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
      text: "text-green-600"
    },
    rejected: {
      bg: 'bg-red-600',
      label: 'REJECTED',
      description: 'One or more fields failed verification.',
      icon: '✗',
      text: "text-red-600"
    },
    review: {
      bg: 'bg-yellow-500',
      label: 'NEEDS REVIEW',
      description: 'Some fields require manual review.',
      icon: '⚠',
      text: "text-yellow-600"
    }
  };

  const config = $derived(statusConfig[result.overallStatus]);
</script>

<div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
  <!-- Status Banner -->
  <div class="px-6 py-5 {config.bg} text-white">
    <div class="flex items-center justify-between">

      <!-- LEFT SIDE -->
      <div class="flex items-center gap-3">
        <span class="text-3xl font-bold">{config.icon}</span>
        <div>
          <h2 class="text-2xl font-bold tracking-wide">{config.label}</h2>
          <p class="text-sm opacity-90 mt-0.5">{config.description}</p>
        </div>
      </div>
    </div>
  </div>

  <!-- Summary -->
  {#if result.summary}
    <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
      <p class="text-sm text-gray-600">{result.summary}</p>
    </div>
  {/if}

  <!-- Field Results -->
  <div class="p-6 flex flex-col gap-3">
    <h3 class="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-1">
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
