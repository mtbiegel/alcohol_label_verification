<script lang="ts">
  import type { FieldResult } from '$lib/types';

  let { 
    result, 
    onOverride,
    onConfirmReject
  }: { 
    result: FieldResult; 
    onOverride?: () => void;
    onConfirmReject?: () => void;
  } = $props();

  const statusConfig = {
    pass: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', icon: '✓', label: 'Pass' },
    fail: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', icon: '✗', label: 'Fail' },
    warning: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', icon: '⚠', label: 'Warning' }
  };

  const config = $derived(statusConfig[result.status]);
</script>

<div class="rounded-lg border {config.border} {config.bg} p-4">
  <div class="flex items-start justify-between gap-4">
    <div class="flex-1">
      <div class="flex items-center gap-2 mb-2">
        <span class="text-lg {config.text}">{config.icon}</span>
        <h4 class="font-semibold text-gray-800">{result.field}</h4>
        {#if result.overridden}
          <span class="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full font-semibold">OVERRIDDEN</span>
        {/if}
      </div>
      <div class="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p class="text-gray-500 text-xs mb-1">Extracted</p>
          <p class="font-mono text-gray-800">{result.extracted || '—'}</p>
        </div>
        <div>
          <p class="text-gray-500 text-xs mb-1">Expected</p>
          <p class="font-mono text-gray-800">{result.expected || '—'}</p>
        </div>
      </div>
      {#if result.note}
        <p class="mt-2 text-xs {config.text}">{result.note}</p>
      {/if}
    </div>
    
    {#if (result.status === 'fail' || result.status === 'warning') && !result.overridden}
    <div class="flex flex-col gap-2">
      {#if onOverride}
        <button
          onclick={onOverride}
          class="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded transition-colors"
        >
          Override as "Approved"
        </button>
      {/if}
      {#if onConfirmReject && result.status === 'warning'}
        <button
          onclick={onConfirmReject}
          class="px-3 py-1.5 text-xs bg-red-600 hover:bg-red-700 text-white font-semibold rounded transition-colors"
        >
          Confirm "Rejected"
        </button>
      {/if}
    </div>
  {/if}
  </div>
</div>