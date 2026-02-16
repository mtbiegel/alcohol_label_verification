<script lang="ts">
  import FieldResult from './FieldResult.svelte';
  import type { VerificationResult } from '$lib/types';
  let { result }: { result: VerificationResult } = $props();

  const statusConfig = {
    approved: {
      bg: 'bg-green-600',
      label: 'APPROVED',
      description: 'All fields match the application data.',
      icon: '✓'
    },
    rejected: {
      bg: 'bg-red-600',
      label: 'REJECTED',
      description: 'One or more fields failed verification.',
      icon: '✗'
    },
    review: {
      bg: 'bg-yellow-500',
      label: 'NEEDS REVIEW',
      description: 'Some fields require manual review.',
      icon: '⚠'
    }
  };

  const config = $derived(statusConfig[result.overallStatus]);
  const passCount = $derived(result.fields.filter(f => f.status === 'pass').length);
  const failCount = $derived(result.fields.filter(f => f.status === 'fail').length);
  const warnCount = $derived(result.fields.filter(f => f.status === 'warning').length);
</script>

<div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
  <!-- Status Banner -->
  <div class="px-6 py-5 {config.bg} text-white">
    <div class="flex items-center gap-3">
      <span class="text-3xl font-bold">{config.icon}</span>
      <div>
        <h2 class="text-2xl font-bold tracking-wide">{config.label}</h2>
        <p class="text-sm opacity-90 mt-0.5">{config.description}</p>
      </div>
    </div>

    <!-- Quick stats -->
    <div class="flex gap-4 mt-4">
      <div class="bg-white bg-opacity-20 rounded-lg px-3 py-2 text-center">
        <p class="text-xl font-bold">{passCount}</p>
        <p class="text-xs opacity-90">Passed</p>
      </div>
      <div class="bg-white bg-opacity-20 rounded-lg px-3 py-2 text-center">
        <p class="text-xl font-bold">{failCount}</p>
        <p class="text-xs opacity-90">Failed</p>
      </div>
      <div class="bg-white bg-opacity-20 rounded-lg px-3 py-2 text-center">
        <p class="text-xl font-bold">{warnCount}</p>
        <p class="text-xs opacity-90">Warnings</p>
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
    <h3 class="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-1">Field-by-Field Results</h3>
    {#each result.fields as field}
      <FieldResult result={field} />
    {/each}
  </div>
</div>