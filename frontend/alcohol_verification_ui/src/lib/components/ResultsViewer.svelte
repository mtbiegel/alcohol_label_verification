<script lang="ts">
  import ResultsPanel from './ResultsPanel.svelte';
  import type { FilePair } from '$lib/types';

  let { 
    pairs,
    currentIndex = $bindable(),
    onReset,
    processingProgress = null  // Add this
  }: { 
    pairs: FilePair[],
    currentIndex: number,
    onReset: () => void,
    processingProgress?: { current: number; total: number } | null  // Add this
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
  {#if processingProgress && processingProgress.current < processingProgress.total}
    <div class="rounded-xl border border-white/40 p-4 bg-blue-50"
      style="backdrop-filter: blur(16px);"
    >
      <div class="flex items-center gap-3">
        <svg class="animate-spin h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
        </svg>
        <div class="flex-1">
          <p class="text-sm font-semibold text-blue-900">Processing Labels...</p>
          <p class="text-xs text-blue-700">{processingProgress.current} of {processingProgress.total} complete</p>
        </div>
        <div class="text-right">
          <p class="text-2xl font-bold text-blue-900">{Math.round((processingProgress.current / processingProgress.total) * 100)}%</p>
        </div>
      </div>
      <div class="mt-2 w-full bg-blue-200 rounded-full h-2">
        <div 
          class="bg-blue-600 h-2 rounded-full transition-all duration-300"
          style="width: {(processingProgress.current / processingProgress.total) * 100}%"
        ></div>
      </div>
    </div>
  {/if}
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
      class="px-4 py-2 bg-blue-600 hover:bg-blue-700 cursor-pointer disabled:bg-gray-300 text-white font-semibold rounded-lg transition-colors"
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
      class="px-4 py-2 bg-blue-600 hover:bg-blue-700 cursor-pointer disabled:bg-gray-300 text-white font-semibold rounded-lg transition-colors"
    >
      Next →
    </button>
  </div>
  <div class="flex gap-3 rounded-xl border border-white/40 p-4"
    style="
    background: rgba(255, 255, 255, 0.45);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.8);
    "
  >
    <button
      onclick={downloadAllResults}
      class="flex-1 flex items-center justify-center gap-2 px-6 py-3 cursor-pointer bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
      </svg>
      Download Results CSV
    </button>
    <button
      onclick={onReset}
      class="px-6 py-3 border-2 border-gray-400 hover:border-gray-600 text-gray-700 font-semibold rounded-lg transition-colors"
    >
      Verify New Labels
    </button>
  </div>

  <!-- Current Result -->
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <!-- Left: Results -->
    <div>
      {#if currentPair.result}
        <ResultsPanel result={currentPair.result} onFieldOverride={handleFieldOverride} />
      {/if}
    </div>

    <!-- Right: Image Preview -->
    <div class="rounded-xl border border-white/40 p-6"
      style="
      background: rgba(255, 255, 255, 0.45);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.8);
      "
    >
      <h3 class="text-lg font-semibold text-gray-800 mb-4">Label Image</h3>
      {#if currentPair.imageFile}
        <img
          src={URL.createObjectURL(currentPair.imageFile)}
          alt="{currentPair.baseName} label"
          class="w-full h-auto rounded-lg border border-gray-200 shadow-sm"
        />
      {:else}
        <div class="flex items-center justify-center h-64 bg-gray-100 rounded-lg">
          <p class="text-gray-400">No image available</p>
        </div>
      {/if}
    </div>
  </div>
</div>