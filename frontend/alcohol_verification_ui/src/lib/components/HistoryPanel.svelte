<script lang="ts">
  import type { VerificationBatch } from '$lib/types';

  let { 
    history, 
    onLoadBatch,
    onClose
  }: { 
    history: VerificationBatch[];
    onLoadBatch: (batch: VerificationBatch) => void;
    onClose: () => void;
  } = $props();

  function formatDate(date: Date): string {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    }).format(date);
  }
</script>

<div class="rounded-xl border border-white/40 p-6"
  style="
  background: rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.8);
  "
>
  <div class="flex items-center justify-between mb-4">
    <h2 class="text-lg font-semibold text-gray-800">Verification History</h2>
    <button
      onclick={onClose}
      class="text-gray-500 hover:text-gray-700"
    >
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
      </svg>
    </button>
  </div>

  <div class="space-y-3">
    {#each history.reverse() as batch}
      <button
        onclick={() => onLoadBatch(batch)}
        class="w-full text-left p-4 bg-white hover:bg-gray-50 rounded-lg border border-gray-200 transition-colors"
      >
        <div class="flex items-center justify-between">
          <div>
            <p class="font-semibold text-gray-800">{batch.pairs.length} label{batch.pairs.length !== 1 ? 's' : ''} verified</p>
            <p class="text-sm text-gray-500">{formatDate(batch.timestamp)}</p>
          </div>
          <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
          </svg>
        </div>
      </button>
    {/each}
  </div>
</div>