<script lang="ts">
	import ResultsPanel from './ResultsPanel.svelte';
	import type { FilePair } from '$lib/types';
	import { onMount } from 'svelte';

	onMount(() => {
		window.scrollTo({ top: 0, behavior: 'auto' });
	});

	let {
		pairs,
		currentIndex = $bindable(),
		onReset,
		processingProgress = null,
		batchSize
	}: {
		pairs: FilePair[];
		currentIndex: number;
		onReset: () => void;
		processingProgress?: { current: number; total: number } | null;
		batchSize: number;
	} = $props();

	const currentPair = $derived(pairs[currentIndex]);
	const approvedCount = $derived(
		pairs.filter((p) => p.result?.overallStatus === 'approved').length
	);
	const rejectedCount = $derived(
		pairs.filter((p) => p.result?.overallStatus === 'rejected').length
	);
	const reviewCount = $derived(pairs.filter((p) => p.result?.overallStatus === 'review').length);

	function goToPrevious() {
		if (currentIndex > 0) currentIndex--;
	}

	function goToNext() {
		if (currentIndex < pairs.length - 1) currentIndex++;
	}

	function downloadAllResults() {
		const now = new Date();
		const timestamp = now.toISOString().replace(/[:.]/g, '-').slice(0, -5); // Formats time in YYYY-MM-DDTHH-MM-SS

		let csv =
			'name,overall_status,brand_status,class_status,alcohol_status,volume_status,warning_status,summary\n';

		for (const pair of pairs) {
			if (!pair.result) continue;
			const statuses = pair.result.fields.map((f) =>
				f.overridden ? `${f.status} (overridden)` : f.status
			);
			csv += `${pair.baseName},${pair.result.overallStatus},${statuses.join(',')},${pair.result.summary.replace(/,/g, ';')}\n`;
		}

		const blob = new Blob([csv], { type: 'text/csv' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `verification_results_${timestamp}.csv`;
		a.click();
		URL.revokeObjectURL(url);
	}

	function handleFieldOverride(fieldIndex: number) {
		if (currentPair.result) {
			const field = currentPair.result.fields[fieldIndex];
			field.status = 'pass';
			field.overridden = true;

			const hasFailures = currentPair.result.fields.some(
				(f) => f.status === 'fail' && !f.overridden
			);
			const hasWarnings = currentPair.result.fields.some(
				(f) => f.status === 'warning' && !f.overridden
			);

			if (!hasFailures && !hasWarnings) {
				currentPair.result.overallStatus = 'approved';
				currentPair.result.summary = 'All fields verified.';
			} else if (hasFailures) {
				currentPair.result.overallStatus = 'rejected';
			} else {
				currentPair.result.overallStatus = 'review';
			}

			pairs = [...pairs];
		}
	}

	function handleFieldConfirmReject(fieldIndex: number) {
		if (currentPair.result) {
			const field = currentPair.result.fields[fieldIndex];
			field.status = 'fail';
			field.overridden = true;

			const hasFailures = currentPair.result.fields.some((f) => f.status === 'fail');

			if (hasFailures) {
				currentPair.result.overallStatus = 'rejected';
				currentPair.result.summary = 'One or more fields failed verification.';
			}

			pairs = [...pairs];
		}
	}
</script>

<div class="space-y-6">
	{#if processingProgress && processingProgress.current < processingProgress.total}
		<div
			class="rounded-xl border border-white/40 bg-blue-50 p-4"
			style="backdrop-filter: blur(16px);"
		>
			<div class="flex items-center gap-3">
				<svg class="h-5 w-5 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
					<circle
						class="opacity-25"
						cx="12"
						cy="12"
						r="10"
						stroke="currentColor"
						stroke-width="4"
					/>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
				</svg>
				<div class="flex-1">
					<p class="text-sm font-semibold text-blue-900">Processing Labels...</p>
					<p class="text-xs text-blue-700">
						{processingProgress.current} of {processingProgress.total} complete | Batch Processing Size:
						{batchSize}
					</p>
				</div>
				<div class="text-right">
					<p class="text-2xl font-bold text-blue-900">
						{Math.round((processingProgress.current / processingProgress.total) * 100)}%
					</p>
				</div>
			</div>
			<div class="mt-2 h-2 w-full rounded-full bg-blue-200">
				<div
					class="h-2 rounded-full bg-blue-600 transition-all duration-300"
					style="width: {(processingProgress.current / processingProgress.total) * 100}%"
				></div>
			</div>
		</div>
	{/if}
	<!-- Summary Stats -->
	<div class="grid grid-cols-1 gap-4 md:grid-cols-5">
		<button onclick={downloadAllResults} class="download-all-results-button-design">
			<svg class="h-14 w-14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
				/>
			</svg>
			Download All Results as CSV
		</button>

		<div class="liquid-glass-effect">
			<p class="text-3xl font-bold text-gray-800">{pairs.length}</p>
			<p class="text-md text-gray-700">Total Verified</p>
		</div>
		<div
			class="rounded-xl border border-white/40 p-4 text-center"
			style="background: rgba(34, 197, 94, 0.1); backdrop-filter: blur(16px);"
		>
			<p class="text-3xl font-bold text-green-700">{approvedCount}</p>
			<p class="text-md text-green-800">Approved</p>
		</div>
		<div
			class="rounded-xl border border-white/40 p-4 text-center"
			style="background: rgba(234, 179, 8, 0.1); backdrop-filter: blur(16px);"
		>
			<p class="text-3xl font-bold text-yellow-600">{reviewCount}</p>
			<p class="text-md text-yellow-700">Need Review</p>
		</div>
		<div
			class="rounded-xl border border-white/40 p-4 text-center"
			style="background: rgba(239, 68, 68, 0.1); backdrop-filter: blur(16px);"
		>
			<p class="text-3xl font-bold text-red-600">{rejectedCount}</p>
			<p class="text-md text-red-700">Rejected</p>
		</div>
	</div>

	<!-- Navigation -->
	<div class="liquid-glass-effect flex items-center justify-between">
		<button onclick={goToPrevious} disabled={currentIndex === 0} class="previous-button-design">
			← Previous
		</button>

		<div class="text-center">
			<p class="text-sm text-gray-600">Viewing</p>
			<p class="text-lg font-bold text-gray-800">{currentPair.baseName}</p>
			<p class="text-xs text-gray-500">{currentIndex + 1} of {pairs.length}</p>
		</div>

		<button
			onclick={goToNext}
			disabled={currentIndex === pairs.length - 1}
			class="next-button-design"
		>
			Next →
		</button>
	</div>

	<!-- Current Result -->
	<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
		<div>
			{#if currentPair.result}
				<ResultsPanel
					result={currentPair.result}
					onFieldOverride={handleFieldOverride}
					onFieldConfirmReject={handleFieldConfirmReject}
				/>
			{/if}
		</div>
		<div class="liquid-glass-effect">
			<h3 class="mb-4 text-lg font-semibold text-gray-800">Label Image</h3>
			{#if currentPair.imageFile}
				<img
					src={URL.createObjectURL(currentPair.imageFile)}
					alt="{currentPair.baseName} label"
					class="h-auto w-full rounded-lg border border-gray-200 shadow-sm"
				/>
			{:else}
				<div class="flex h-64 items-center justify-center rounded-lg bg-gray-100">
					<p class="text-gray-400">No image available</p>
				</div>
			{/if}
		</div>
	</div>
</div>
