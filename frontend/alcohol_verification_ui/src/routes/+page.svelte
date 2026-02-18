<script lang="ts">
  import PairUpload from '$lib/components/PairUpload.svelte';
  import ResultsViewer from '$lib/components/ResultsViewer.svelte';
  import type { FilePair, VerificationResult } from '$lib/types';

  let pairs = $state<FilePair[]>([]);
  let isProcessing = $state(false);
  let processedPairs = $state<FilePair[]>([]);
  let currentIndex = $state(0);
  let error = $state<string | null>(null);

  let attribute_blur = 7;
  let background_opacity = 0.8;
  let background_size = 100;

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

    isProcessing = true;
    error = null;
    processedPairs = [];

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
    }

    isProcessing = false;
    currentIndex = 0;
  }

  function handleReset() {
    pairs = [];
    processedPairs = [];
    currentIndex = 0;
    error = null;
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

  <!-- Header -->
  <header class="bg-blue-900 text-white shadow-lg">
    <div class="max-w-7xl mx-auto px-6 py-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-4">
          <div class="bg-white rounded p-1">
            <svg class="w-8 h-8 text-blue-900" fill="currentColor" viewBox="0 0 24 24">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          </div>
          <div>
            <h1 class="text-xl font-bold tracking-wide">TTB Label Verification</h1>
            <p class="text-blue-200 text-sm">Alcohol Beverage Label Compliance Tool</p>
          </div>
        </div>
        <button
          onclick={downloadTemplate}
          class="flex items-center gap-2 px-4 py-2 bg-white text-blue-900 font-semibold rounded-lg hover:bg-blue-50 transition-colors shadow-sm"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          Download Template
        </button>
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
            <h2 class="text-lg font-semibold text-gray-800">Upload Labels & Applications</h2>
            <p class="text-sm text-gray-600 mt-1">
              Upload paired files: <code class="bg-gray-200 px-1 rounded">name_image.jpg</code> and <code class="bg-gray-200 px-1 rounded">name_application.json</code>
            </p>
          </div>

          <PairUpload onPairsUpdate={handlePairsUpdate} />
        </section>

        {#if pairs.length > 0}
          <div class="flex gap-4">
            <button
              onclick={handleVerifyAll}
              disabled={isProcessing || pairs.filter(p => p.status === 'complete').length === 0}
              class="flex-1 py-4 px-6 bg-blue-800 hover:bg-blue-900 disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-lg font-semibold rounded-xl transition-colors shadow-sm"
            >
              {#if isProcessing}
                <span class="flex items-center justify-center gap-3">
                  <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                  Processing...
                </span>
              {:else}
                Verify {pairs.filter(p => p.status === 'complete').length} Label(s)
              {/if}
            </button>

            <button
              onclick={handleReset}
              class="px-6 py-4 border-2 border-gray-400 hover:border-gray-600 text-gray-700 font-semibold rounded-xl transition-colors"
            >
              Clear All
            </button>
          </div>
        {/if}

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
      />
    {/if}
  </main>
</div>