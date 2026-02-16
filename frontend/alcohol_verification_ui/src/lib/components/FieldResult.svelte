<script lang="ts">
  import type { FieldResult } from '$lib/types';
  let { result }: { result: FieldResult } = $props();

  const statusConfig = {
    pass: { bg: 'bg-green-50', border: 'border-green-200', icon: '✓', iconColor: 'text-green-600', label: 'Pass' },
    fail: { bg: 'bg-red-50', border: 'border-red-200', icon: '✗', iconColor: 'text-red-600', label: 'Fail' },
    warning: { bg: 'bg-yellow-50', border: 'border-yellow-200', icon: '⚠', iconColor: 'text-yellow-600', label: 'Review' }
  };

  const config = $derived(statusConfig[result.status]);
</script>

<div class="rounded-lg border {config.border} {config.bg} p-4">
  <div class="flex items-start justify-between gap-4">
    <div class="flex-1 min-w-0">
      <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">{result.field}</p>
      <div class="grid grid-cols-2 gap-3 mt-2">
        <div>
          <p class="text-xs text-gray-400 mb-0.5">Expected</p>
          <p class="text-sm text-gray-700 font-medium break-words">{result.expected || '—'}</p>
        </div>
        <div>
          <p class="text-xs text-gray-400 mb-0.5">Extracted from Label</p>
          <p class="text-sm text-gray-700 font-medium break-words">{result.extracted || '—'}</p>
        </div>
      </div>
      {#if result.note}
        <p class="text-xs text-gray-500 mt-2 italic">{result.note}</p>
      {/if}
    </div>
    <div class="flex flex-col items-center gap-1 shrink-0">
      <span class="text-xl {config.iconColor} font-bold">{config.icon}</span>
      <span class="text-xs font-medium {config.iconColor}">{config.label}</span>
    </div>
  </div>
</div>