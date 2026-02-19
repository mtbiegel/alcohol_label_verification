<script lang="ts">
	import FieldResult from './FieldResult.svelte';
	import type { VerificationResult } from '$lib/types';

	let {
		result,
		onFieldOverride,
		onFieldConfirmReject
	}: {
		result: VerificationResult;
		onFieldOverride?: (index: number) => void;
		onFieldConfirmReject?: (index: number) => void;
	} = $props();

	const statusConfig = {
		approved: {
			bg: 'bg-green-600',
			label: 'APPROVED',
			description: 'All fields match the application data.',
			icon: '✓',
			text: 'text-green-600'
		},
		rejected: {
			bg: 'bg-red-600',
			label: 'REJECTED',
			description: 'One or more fields failed verification.',
			icon: '✗',
			text: 'text-red-600'
		},
		review: {
			bg: 'bg-yellow-500',
			label: 'NEEDS REVIEW',
			description: 'Some fields require manual review.',
			icon: '⚠',
			text: 'text-yellow-600'
		}
	};

	const config = $derived(statusConfig[result.overallStatus]);
</script>

<div class="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
	<!-- Status Banner -->
	<div class="px-6 py-5 {config.bg} text-white">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-3">
				<span class="text-3xl font-bold">{config.icon}</span>
				<div>
					<h2 class="text-2xl font-bold tracking-wide">{config.label}</h2>
					<p class="mt-0.5 text-sm opacity-90">{config.description}</p>
				</div>
			</div>
		</div>
	</div>

	<!-- Summary -->
	{#if result.summary}
		<div class="border-b border-gray-200 bg-gray-50 px-6 py-4">
			<p class="text-sm text-gray-600">{result.summary}</p>
		</div>
	{/if}

	<!-- Field Results -->
	<div class="flex flex-col gap-3 p-6">
		<h3 class="mb-1 text-sm font-semibold tracking-wider text-gray-500 uppercase">
			Field-by-Field Results
		</h3>

		{#each result.fields as field, index}
			<FieldResult
				result={field}
				onOverride={onFieldOverride ? () => onFieldOverride(index) : undefined}
				onConfirmReject={onFieldConfirmReject ? () => onFieldConfirmReject(index) : undefined}
			/>
		{/each}
	</div>
</div>
