<script lang="ts">
  import PairUpload from '$lib/components/PairUpload.svelte';
  import ResultsViewer from '$lib/components/ResultsViewer.svelte';
  import Modal from '$lib/components/Modal.svelte'
  import type { FilePair, VerificationResult, VerificationBatch } from '$lib/types';

  let pairs = $state<FilePair[]>([]);
  let isProcessing = $state(false);
  let processedPairs = $state<FilePair[]>([]);
  let currentIndex = $state(0);
  let error = $state<string | null>(null);
  let showWarning = $state(false);
  let showHelp = $state(false);
  let processingProgress = $state({ current: 0, total: 0 });

  let attribute_blur = 7;
  let background_opacity = 0.8;
  let background_size = 100;

  let pairUploadRef = $state<any>(null);

  const completePairsCount = $derived(pairs.filter(p => p.status === 'complete').length);
  const incompletePairsCount = $derived(pairs.filter(p => p.status !== 'complete').length);

  function handlePairsUpdate(newPairs: FilePair[]) {
    pairs = newPairs;
    error = null;
  }

  async function handleVerifyAll() {
    const completePairs = pairs.filter(p => p.status === 'complete');
    
    if (completePairs.length === 0) {
      error = 'No complete pairs to verify. Please ensure each image has a matching application file.';
      return;
    }

    // Show warning if there are incomplete pairs
    if (incompletePairsCount > 0) {
      showWarning = true;
      return;
    }

    await processVerification();
  }

  function openHelp() {
    showHelp = true;
  }

  async function processVerification() {
    showWarning = false;
    const completePairs = pairs.filter(p => p.status === 'complete');
    
    isProcessing = true;
    error = null;
    processedPairs = [];
    processingProgress = { current: 0, total: completePairs.length };

    for (const pair of completePairs) {
      try {
        const formData = new FormData();
        formData.append('image', pair.imageFile!);
        formData.append('applicationData', JSON.stringify(pair.applicationData));

        const response = await fetch('/api/verify', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          throw new Error(`Server error: ${response.status}`);
        }

        const result: VerificationResult = await response.json();
        
        processedPairs.push({
          ...pair,
          result
        });
      } catch (err) {
        processedPairs.push({
          ...pair,
          result: {
            overallStatus: 'rejected',
            summary: err instanceof Error ? err.message : 'Processing failed',
            fields: []
          }
        });
      }

      processingProgress.current++;
    }
    isProcessing = false;
    currentIndex = 0;
  }

  function handleReset() {
    if (pairUploadRef) {
      pairs.forEach(p => pairUploadRef.removePair(p.baseName));
    }

    pairs = [];
    processedPairs = [];
    currentIndex = 0;
    error = null;
    processingProgress = { current: 0, total: 0 };
  }

  function downloadTemplate() {
    const template = {
      brand_name: "Midnight Ember",
      class_type: "Smoky Bourbon Whiskey",
      alcohol_content_amount: "47",
      alcohol_content_format: "%",
      net_contents_amount: "750",
      net_contents_unit: "mL",
      producer_name: "Midnight Ember Distillery",
      country_of_origin: "USA"
    };

    const blob = new Blob([JSON.stringify(template, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'example_application.json';
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

<div class="min-h-screen relative">
  <!-- Background Logo -->
  <div
    class="fixed inset-0 pointer-events-none"
    style="
      z-index: -1;
      background-image: url('/usa_seal.png');
      background-repeat: no-repeat;
      background-position: center center;
      background-size: {background_size}%;
      opacity: {background_opacity};
    "
  ></div>

  <header class="bg-blue-900 text-white shadow-lg">
    <div class="max-w-7xl mx-auto px-6 py-4">
      <div class="flex items-center justify-between">

        <!-- LEFT SIDE -->
        <div class="flex items-center gap-4">
          <div class="bg-white rounded p-1">
            <svg class="w-8 h-8 text-blue-900" fill="currentColor" viewBox="0 0 24 24">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <div>
            <h1 class="text-xl font-bold tracking-wide">
              TTB Label Verification
            </h1>
            <p class="text-blue-200 text-sm">
              Alcohol Beverage Label Compliance Tool
            </p>
          </div>
        </div>

        <!-- RIGHT SIDE -->
        <div class="flex items-center gap-3">
          <button 
            onclick={handleReset}
            class="px-4 py-2 bg-white text-blue-900 font-semibold cursor-pointer rounded-lg hover:bg-blue-50 transition-colors shadow-sm">
            New Verification
          </button>

          <button 
            onclick={openHelp}
            class="px-4 py-2 bg-white text-blue-900 font-semibold cursor-pointer rounded-lg hover:bg-blue-50 transition-colors shadow-sm">
            How it works
          </button>

          <button
            onclick={downloadTemplate}
            class="flex items-center gap-2 px-4 py-2 bg-white cursor-pointer text-blue-900 font-semibold rounded-lg hover:bg-blue-50 transition-colors shadow-sm"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            Download Template
          </button>
        </div>

      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-6 py-8">
    {#if processedPairs.length === 0}
      <!-- Upload Section -->
      <div class="space-y-6">
        <section class="rounded-xl border border-white/40 p-6"
          style="
          background: rgba(255, 255, 255, 0.45);
          backdrop-filter: blur({attribute_blur}px);
          -webkit-backdrop-filter: blur(16px);
          box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.8);
          "
        >
          <div class="mb-4">
            <h2 class="text-lg font-semibold text-gray-900">Upload Labels & Applications</h2>
            <p class="text-sm text-gray-800 mt-1">
              NAMING SCHEME: Upload paired files & replace LABEL_NAME with the label's name:
              <code class="bg-gray-200 px-1 rounded">LABEL_NAME_image.jpg</code> 
              and
              <code class="bg-gray-50 px-1 rounded">LABEL_NAME_application.json</code>
            </p>
          </div>

          <PairUpload
            bind:this={pairUploadRef}
            onPairsUpdate={handlePairsUpdate}
            pairs={pairs}
          />
        </section>

        <!-- Always visible verify button -->
        <div class="flex gap-4">
          <button
            onclick={handleVerifyAll}
            disabled={isProcessing || completePairsCount === 0}
            class="flex-1 py-4 px-6 bg-blue-800 hover:bg-blue-900 disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-lg font-semibold rounded-xl transition-colors shadow-sm"
          >
            {#if isProcessing}
              <span class="flex items-center justify-center gap-3">
                <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                Processing {processingProgress.total} label{processingProgress.total !== 1 ? 's' : ''}...
              </span>
            {:else}
              Verify {completePairsCount} Label{completePairsCount !== 1 ? 's' : ''}
            {/if}
          </button>

          {#if pairs.length > 0}
            <button
              onclick={handleReset}
              disabled={isProcessing}
              class="px-6 py-4 border-2 border-gray-400 hover:border-gray-600 disabled:border-gray-300 text-gray-700 disabled:text-gray-400 font-semibold rounded-xl transition-colors"
            >
              Clear All
            </button>
          {/if}
        </div>

        {#if error}
          <div class="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
            {error}
          </div>
        {/if}
      </div>
    {:else}
      <!-- Results Section -->
      <ResultsViewer 
        pairs={processedPairs} 
        bind:currentIndex={currentIndex}
        onReset={handleReset}
        processingProgress={isProcessing ? processingProgress : null}
      />
    {/if}

    <Modal
      show={showHelp}
      title="Need Help?"
      message="Here is some helpful information about how to use this feature."
      onCancel={() => showHelp = false}
    />
  </main>
</div>

<!-- Warning Modal -->
{#if showWarning}
  <div
    class="fixed inset-0 flex items-center justify-center z-50 bg-white/0 backdrop-blur-sm"
    style="background-color: rgba(255, 255, 255, 0.2);" 
    onclick={() => showWarning = false}
  >
    <div class="bg-white rounded-lg p-6 max-w-md mx-4" onclick={(e) => e.stopPropagation()}>
      <div class="flex items-start gap-4">
        <div class="flex-shrink-0">
          <svg class="w-12 h-12 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
        </div>
        <div class="flex-1">
          <h3 class="text-lg font-semibold text-gray-900 mb-2">Incomplete Pairs Detected</h3>
          <p class="text-sm text-gray-600 mb-4">
            {incompletePairsCount} file pair{incompletePairsCount !== 1 ? 's are' : ' is'} missing (either an image or application file). 
            Only the {completePairsCount} complete pair{completePairsCount !== 1 ? 's' : ''} will be verified.
          </p>
          <div class="flex gap-3 justify-end">
            <button
              onclick={() => showWarning = false}
              class="px-4 py-2 text-gray-700 hover:text-gray-900 font-semibold"
            >
              Cancel
            </button>
            <button
              onclick={processVerification}
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
            >
              Continue Anyway
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}
