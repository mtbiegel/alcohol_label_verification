<script lang="ts">
  import ResultsPanel from './ResultsPanel.svelte';
  import type { FilePair } from '$lib/types';

  let { 
    pairs,
    currentIndex = $bindable(),
    onReset
  }: { 
    pairs: FilePair[],
    currentIndex: number,
    onReset: () => void
  } = $props();

  const currentPair = $derived(pairs[currentIndex]);
  const approvedCount = $derived(pairs.filter(p => p.result?.overallStatus === 'approved').length);
  const rejectedCount = $derived(pairs.filter(p => p.result?.overallStatus === 'rejected').length);
  const reviewCount = $derived(pairs.filter(p => p.result?.overallStatus === 'review').length);

  function goToPrevious() {
    if (currentIndex > 0) currentIndex--;
  }

  function goToNext() {
    if (currentIndex < pairs.length - 1) currentIndex++;
  }

  function downloadAllResults() {
    const now = new Date();
    const timestamp = now.toISOString().replace(/[:.]/g, '-').slice(0, -5); // Format: YYYY-MM-DDTHH-MM-SS
    
    let csv = 'name,overall_status,brand_status,class_status,alcohol_status,volume_status,warning_status,summary\n';
    
    for (const pair of pairs) {
      if (!pair.result) continue;
      const statuses = pair.result.fields.map(f => f.overridden ? 'pass (overridden)' : f.status);
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
      
      // Recalculate overall status
      const hasFailures = currentPair.result.fields.some(f => f.status === 'fail' && !f.overridden);
      const hasWarnings = currentPair.result.fields.some(f => f.status === 'warning' && !f.overridden);
      
      if (!hasFailures && !hasWarnings) {
        currentPair.result.overallStatus = 'approved';
        currentPair.result.summary = 'All fields verified.';
      } else if (hasFailures) {
        currentPair.result.overallStatus = 'rejected';
      } else {
        currentPair.result.overallStatus = 'review';
      }
      
      // Force reactivity
      pairs = [...pairs];
    }
  }
</script>

<div class="space-y-6">
  <!-- Summary Stats -->
  <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
    <div class="rounded-xl border border-white/40 p-4 text-center"
      style="
      background: rgba(255, 255, 255, 0.45);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.8);
      "
    >
      <p class="text-3xl font-bold text-gray-800">{pairs.length}</p>
      <p class="text-sm text-gray-600">Total Verified</p>
    </div>
    <div class="rounded-xl border border-white/40 p-4 text-center"
      style="background: rgba(34, 197, 94, 0.1); backdrop-filter: blur(16px);"
    >
      <p class="text-3xl font-bold text-green-700">{approvedCount}</p>
      <p class="text-sm text-green-600">Approved</p>
    </div>
    <div class="rounded-xl border border-white/40 p-4 text-center"
      style="background: rgba(234, 179, 8, 0.1); backdrop-filter: blur(16px);"
    >
      <p class="text-3xl font-bold text-yellow-700">{reviewCount}</p>
      <p class="text-sm text-yellow-600">Need Review</p>
    </div>
    <div class="rounded-xl border border-white/40 p-4 text-center"
      style="background: rgba(239, 68, 68, 0.1); backdrop-filter: blur(16px);"
    >
      <p class="text-3xl font-bold text-red-700">{rejectedCount}</p>
      <p class="text-sm text-red-600">Rejected</p>
    </div>
  </div>

  <!-- Navigation -->
  <div class="flex items-center justify-between rounded-xl border border-white/40 p-4"
    style="
    background: rgba(255, 255, 255, 0.45);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.8);
    "
  >
    <button
      onclick={goToPrevious}
      disabled={currentIndex === 0}
      class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white font-semibold rounded-lg transition-colors"
    >
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
      class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white font-semibold rounded-lg transition-colors"
    >
      Next →
    </button>
  </div>

  <!-- Current Result -->
  {#if currentPair.result}
    <ResultsPanel result={currentPair.result} onFieldOverride={handleFieldOverride} />
  {/if}

  <!-- Actions -->
  <div class="flex gap-4">
    <button
      onclick={downloadAllResults}
      class="flex-1 px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors"
    >
      Download All Results (CSV)
    </button>
    <button
      onclick={onReset}
      class="px-6 py-3 border-2 border-gray-400 hover:border-gray-600 text-gray-700 font-semibold rounded-lg transition-colors"
    >
      Verify New Labels
    </button>
  </div>
</div>