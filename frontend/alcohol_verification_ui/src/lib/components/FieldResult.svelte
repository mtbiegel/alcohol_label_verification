<!-- MIT License
Copyright (c) 2026 Mark Biegel
See LICENSE file for full license text. -->

<script lang="ts">
	// Import type definitions
	import type { FieldResult } from '$lib/types';

	// Receive props for this component
	let {
		result,
		onOverride,
		onConfirmReject
	}: {
		result: FieldResult;
		onOverride?: () => void;
		onConfirmReject?: () => void;
	} = $props();

	// Define styling and icons for each status type
	const statusConfig = {
		pass: {
			bg: 'bg-green-50',
			border: 'border-green-200',
			text: 'text-green-700',
			icon: '✓',
			label: 'Pass'
		},
		fail: {
			bg: 'bg-red-50',
			border: 'border-red-200',
			text: 'text-red-700',
			icon: '✗',
			label: 'Fail'
		},
		warning: {
			bg: 'bg-yellow-50',
			border: 'border-yellow-200',
			text: 'text-yellow-700',
			icon: '⚠',
			label: 'Warning'
		}
	};

	// Derive current status config based on result
	const config = $derived(statusConfig[result.status]);
</script>

<!-- Result container -->
<div class="rounded-lg border {config.border} {config.bg} p-4">
	<div class="flex items-start justify-between gap-4">
		<!-- Left side: field info -->
		<div class="flex-1">
			<div class="mb-2 flex items-center gap-2">
				<span class="text-lg {config.text}">{config.icon}</span>
				<h4 class="font-semibold text-gray-800">{result.field}</h4>
				{#if result.overridden}
					<span class="overridden-tag-design">OVERRIDDEN</span>
				{/if}
			</div>

			<!-- Extracted vs Expected values -->
			<div class="grid grid-cols-2 gap-3 text-sm">
				<div>
					<p class="mb-1 text-xs text-gray-500">Extracted</p>
					<p class="font-mono text-gray-800">{result.extracted || '—'}</p>
				</div>
				<div>
					<p class="mb-1 text-xs text-gray-500">Expected</p>
					<p class="font-mono text-gray-800">{result.expected || '—'}</p>
				</div>
			</div>

			<!-- Optional note -->
			{#if result.note}
				<p class="mt-2 text-xs {config.text}">{result.note}</p>
			{/if}
		</div>

		<!-- Right side: action buttons for fail/warning -->
		{#if (result.status === 'fail' || result.status === 'warning') && !result.overridden}
			<div class="flex flex-col gap-2">
				{#if onOverride}
					<button onclick={onOverride} class="override-button-design">
						Override as "Approved"
					</button>
				{/if}
				{#if onConfirmReject && result.status === 'warning'}
					<button onclick={onConfirmReject} class="confirm-reject-button-design">
						Confirm "Rejected"
					</button>
				{/if}
			</div>
		{/if}
	</div>
</div>
