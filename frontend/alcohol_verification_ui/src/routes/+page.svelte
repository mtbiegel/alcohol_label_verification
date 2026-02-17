<script lang="ts">
  import DropZone from '$lib/components/DropZone.svelte';
  import LabelForm from '$lib/components/LabelForm.svelte';
  import ResultsPanel from '$lib/components/ResultsPanel.svelte';
  import type { ApplicationData, VerificationResult } from '$lib/types';

  let imageFile = $state<File | null>(null);
  let imagePreviewUrl = $state<string | null>(null);
  let verificationResult = $state<VerificationResult | null>(null);
  let isLoading = $state(false);
  let error = $state<string | null>(null);

  let attribute_blur = 7
  let background_opacity = 0.8
  let background_size = 100

  let applicationData = $state<ApplicationData>({
    brand_name: '',
    class_type: '',
    alcohol_content: '',
    net_contents: '',
    producer_name: '',
    country_of_origin: '',
    gov_warning: 'GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.'
  });

  function handleImageSelect(file: File) {
    imageFile = file;
    imagePreviewUrl = URL.createObjectURL(file);
    verificationResult = null;
    error = null;
  }

  async function handleVerify() {
    if (!imageFile) {
      error = 'Please upload a label image before verifying.';
      return;
    }

    isLoading = true;
    error = null;
    verificationResult = null;

    try {
      const formData = new FormData();
      formData.append('image', imageFile);
      formData.append('applicationData', JSON.stringify(applicationData));

      const response = await fetch('/api/verify', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.message || `Server error: ${response.status}`);
      }

      verificationResult = await response.json();
    } catch (err) {
      error = err instanceof Error ? err.message : 'An unexpected error occurred.';
    } finally {
      isLoading = false;
    }
  }

  function handleReset() {
    imageFile = null;
    imagePreviewUrl = null;
    verificationResult = null;
    error = null;
    applicationData = {
      brand_name: '',
      class_type: '',
      alcohol_content: '',
      net_contents: '',
      producer_name: '',
      country_of_origin: '',
      gov_warning: 'GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic beverages impairs your ability to drive a car or operate machinery, and may cause health problems.'
    };
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
    <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
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
        onclick={handleReset}
        class="text-sm text-blue-200 hover:text-white border border-blue-400 hover:border-white px-4 py-2 rounded transition-colors"
      >
        New Verification
      </button>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-6 py-8">
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-20">

      <!-- Left Column: Upload + Preview -->
      <div class="flex flex-col gap-6">
        <section class="rounded-xl border border-white/40 p-6"
            style="
            background: rgba(255, 255, 255, 0.45);
            backdrop-filter: blur({attribute_blur}px);
            -webkit-backdrop-filter: blur(16px);
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.8);
            "
        >
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Label Image</h2>
          <DropZone onFileSelect={handleImageSelect} />

          {#if imagePreviewUrl}
            <div class="mt-4">
              <p class="text-sm text-gray-500 mb-2">Preview</p>
              <img
                src={imagePreviewUrl}
                alt="Uploaded label"
                class="w-full max-h-80 object-contain rounded-lg border border-gray-200 bg-gray-50"
              />
            </div>
          {/if}
        </section>

        <!-- Application Data Form -->
        <section class="rounded-xl border border-white/40 p-6"
            style="
            background: rgba(255, 255, 255, 0.45);
            backdrop-filter: blur({attribute_blur}px);
            -webkit-backdrop-filter: blur(16px);
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.8);
            "
        >
          <h2 class="text-lg font-semibold text-gray-800 mb-4">Application Data</h2>
          <LabelForm bind:data={applicationData} />
        </section>

        <!-- Verify Button -->
        <button
          onclick={handleVerify}
          disabled={isLoading || !imageFile}
          class="w-full py-4 px-6 bg-blue-800 hover:bg-blue-900 disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-lg font-semibold rounded-xl transition-colors shadow-sm"
        >
          {#if isLoading}
            <span class="flex items-center justify-center gap-3">
              <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              Verifying Label...
            </span>
          {:else}
            Verify Label
          {/if}
        </button>

        {#if error}
          <div class="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
            {error}
          </div>
        {/if}
      </div>

      <!-- Right Column: Results -->
      <div class="flex flex-col gap-6">
        {#if verificationResult}
          <ResultsPanel result={verificationResult} />
        {:else}
          <div class="rounded-xl border border-white/40 p-6 p-12 flex flex-col items-center justify-center text-center text-gray-400 h-full min-h-64"
            style="
            background: rgba(255, 255, 255, 0.45);
            backdrop-filter: blur({attribute_blur}px);
            -webkit-backdrop-filter: blur(16px);
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.8);
            "
        >
            <svg class="w-16 h-16 mb-4 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
            </svg>
            <p class="text-lg font-medium text-gray-500">Verification Results</p>
            <p class="text-sm mt-1">Upload a label and fill in the application data, then click Verify.</p>
          </div>
        {/if}
      </div>
    </div>
  </main>
</div>
