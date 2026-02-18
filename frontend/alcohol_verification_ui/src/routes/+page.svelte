<script lang="ts">
  import DropZone from '$lib/components/DropZone.svelte';
  import LabelForm from '$lib/components/LabelForm.svelte';
  import ResultsPanel from '$lib/components/ResultsPanel.svelte';
  import BatchResults from '$lib/components/BatchResults.svelte';
  import Modal from '$lib/components/Modal.svelte';
  import type { ApplicationData, VerificationResult } from '$lib/types';

  let mode = $state<'single' | 'batch'>('single');

  // Single mode state
  let imageFile = $state<File | null>(null);
  let imagePreviewUrl = $state<string | null>(null);
  let verificationResult = $state<VerificationResult | null>(null);
  let isLoading = $state(false);
  let error = $state<string | null>(null);

  // Batch mode state
  let csvData = $state<Map<string, ApplicationData> | null>(null);
  let batchImages = $state<File[]>([]);
  let batchResults = $state<Array<{filename: string, result: VerificationResult}>>([]);
  let isBatchLoading = $state(false);
  let batchError = $state<string | null>(null);
  let batchProgress = $state({ current: 0, total: 0 });

  let attribute_blur = 7;
  let background_opacity = 0.8;
  let background_size = 100;
  let showHelp = $state(false);

  let applicationData = $state<ApplicationData>({
    brand_name: '',
    class_type: '',
    alcohol_content_amount: '',
    alcohol_content_format: '%',
    net_contents_amount: '',
    net_contents_unit: 'mL',
    producer_name: '',
    country_of_origin: ''
  });

  function handleImageSelect(file: File) {
    imageFile = file;
    imagePreviewUrl = URL.createObjectURL(file);
    verificationResult = null;
    error = null;
  }

  function downloadTemplate() {
    const csv = `filename,brand_name,class_type,alcohol_content_amount,alcohol_content_format,net_contents_amount,net_contents_unit,producer_name,country_of_origin
label1.jpg,Midnight Ember,Smoky Bourbon Whiskey,47,%,750,mL,Midnight Ember Distillery,USA
label2.jpg,ABC,Straight Rye Whisky,45,%,750,mL,ABC Distillery,USA`;

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'batch_template.csv';
    a.click();
    URL.revokeObjectURL(url);
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
      alcohol_content_amount: '',
      alcohol_content_format: '%',
      net_contents_amount: '',
      net_contents_unit: 'mL',
      producer_name: '',
      country_of_origin: ''
    };
  }

  function handleCSVUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      csvData = parseCSV(text);
      batchError = null;
    };
    reader.onerror = () => {
      batchError = 'Failed to read CSV file';
    };
    reader.readAsText(file);
  }

  function parseCSV(text: string): Map<string, ApplicationData> {
    const lines = text.trim().split('\n');
    if (lines.length < 2) {
      batchError = 'CSV file is empty or invalid';
      return new Map();
    }

    const data = new Map();

    for (let i = 1; i < lines.length; i++) {
      if (!lines[i].trim()) continue;
      
      const values = lines[i].split(',').map(v => v.trim());
      const filename = values[0];
      
      if (!filename) continue;

      data.set(filename, {
        brand_name: values[1] || '',
        class_type: values[2] || '',
        alcohol_content_amount: values[3] || '',
        alcohol_content_format: values[4] || '%',
        net_contents_amount: values[5] || '',
        net_contents_unit: values[6] || 'mL',
        producer_name: values[7] || '',
        country_of_origin: values[8] || ''
      });
    }

    return data;
  }

  function handleImagesUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    batchImages = Array.from(input.files || []);
    batchError = null;
  }

  async function handleBatchVerify() {
    if (!csvData || batchImages.length === 0) {
      batchError = 'Please upload both CSV and images';
      return;
    }

    isBatchLoading = true;
    batchError = null;
    batchResults = [];
    batchProgress = { current: 0, total: batchImages.length };

    for (const imageFile of batchImages) {
      const appData = csvData.get(imageFile.name);
      
      if (!appData) {
        batchResults.push({
          filename: imageFile.name,
          result: {
            overallStatus: 'rejected',
            summary: 'No matching application data found in CSV',
            fields: []
          }
        });
        batchProgress.current++;
        continue;
      }

      try {
        const formData = new FormData();
        formData.append('image', imageFile);
        formData.append('applicationData', JSON.stringify(appData));

        const response = await fetch('/api/verify', {
          method: 'POST',
          body: formData
        });

        const result = await response.json();
        batchResults.push({ filename: imageFile.name, result });
      } catch (err) {
        batchResults.push({
          filename: imageFile.name,
          result: {
            overallStatus: 'rejected',
            summary: err instanceof Error ? err.message : 'Processing error',
            fields: []
          }
        });
      }

      batchProgress.current++;
    }

    isBatchLoading = false;
  }

  function downloadBatchResults() {
    let csv = 'filename,overall_status,brand_status,class_status,alcohol_status,volume_status,warning_status,summary\n';
    
    for (const {filename, result} of batchResults) {
      const statuses = result.fields.map(f => f.status);
      csv += `${filename},${result.overallStatus},${statuses.join(',')},${result.summary.replace(/,/g, ';')}\n`;
    }

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `batch_results_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleBatchReset() {
    csvData = null;
    batchImages = [];
    batchResults = [];
    batchError = null;
    batchProgress = { current: 0, total: 0 };
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
          onclick={() => showHelp = true}
          class="flex items-center gap-2 px-4 py-2 bg-white text-blue-900 font-semibold rounded-lg hover:bg-blue-50 transition-colors shadow-sm"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none"/>
            <path d="M12 16h.01M12 8a2 2 0 0 1 2 2c0 1-2 2-2 2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          </svg>
          Help
        </button>
      </div>
    </div>
  </header>

  <Modal bind:open={showHelp} title="Help & Instructions" on:close={() => showHelp = false}>
    <p>Welcome to the TTB Label Verification tool!</p>
    <ul class="list-disc pl-5 space-y-1">
      <li>Upload a label image in Single Verification mode.</li>
      <li>Fill out the Application Data form.</li>
      <li>Click Verify Label to see the results on the right panel.</li>
      <li>For Batch Processing, upload CSV and multiple label images.</li>
    </ul>
  </Modal>

  <main class="max-w-7xl mx-auto px-6 py-8">
    <!-- Tabs -->
    <div class="flex gap-2 mb-8">
      <button
        onclick={() => mode = 'single'}
        class="button-blur flex-1 relative text-center"
      >
        Single Verification
        {#if mode === 'single'}
          <div class="absolute bottom-0 left-0 right-0 h-1 bg-blue-900 rounded-t"></div>
        {/if}
      </button>

      <button
        onclick={() => mode = 'batch'}
        class="button-blur flex-1 relative text-center"
      >
        Batch Processing
        {#if mode === 'batch'}
          <div class="absolute bottom-0 left-0 right-0 h-1 bg-blue-900 rounded-t"></div>
        {/if}
      </button>
    </div>

    {#if mode === 'single'}
      <!-- Single Verification Mode -->
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

          <button
            onclick={handleReset}
            class="text-sm text-gray-600 hover:text-gray-800 underline"
          >
            Reset Form
          </button>
        </div>

        <!-- Right Column: Results -->
        <div class="flex flex-col gap-6">
          {#if verificationResult}
            <ResultsPanel result={verificationResult} />
          {:else}
            <div class="rounded-xl border border-white/40 p-12 flex flex-col items-center justify-center text-center text-gray-400 h-full min-h-64"
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
    {:else}
      <!-- Batch Processing Mode -->
      <div class="space-y-6">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- CSV Upload -->
          <section class="rounded-xl border border-white/40 p-6"
            style="
            background: rgba(255, 255, 255, 0.45);
            backdrop-filter: blur({attribute_blur}px);
            -webkit-backdrop-filter: blur(16px);
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.8);
            "
          >
            <h2 class="text-lg font-semibold text-gray-800 mb-4">Step 1: Upload Application Data (CSV)</h2>
                <button
              onclick={downloadTemplate}
              class="w-full mb-3 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors text-sm"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              Download Batch CSV Template
            </button>
            <input
              type="file"
              accept=".csv"
              onchange={handleCSVUpload}
              class="w-full text-sm border border-gray-300 rounded-lg p-2 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-blue-600 file:text-white hover:file:bg-blue-700"
            />
            {#if csvData}
              <p class="text-sm text-green-600 mt-2">✓ {csvData.size} records loaded</p>
            {/if}
          </section>

          <!-- Images Upload -->
          <section class="rounded-xl border border-white/40 p-6"
            style="
            background: rgba(255, 255, 255, 0.45);
            backdrop-filter: blur({attribute_blur}px);
            -webkit-backdrop-filter: blur(16px);
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.8);
            "
          >
            <h2 class="text-lg font-semibold text-gray-800 mb-4">Step 2: Upload Label Images</h2>
            <input
              type="file"
              accept="image/*"
              multiple
              onchange={handleImagesUpload}
              class="w-full text-sm border border-gray-300 rounded-lg p-2 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-blue-600 file:text-white hover:file:bg-blue-700"
            />
            {#if batchImages.length > 0}
              <p class="text-sm text-green-600 mt-2">✓ {batchImages.length} images selected</p>
            {/if}
          </section>
        </div>

        <!-- Process Button -->
        <div class="flex gap-4">
          <button
            onclick={handleBatchVerify}
            disabled={!csvData || batchImages.length === 0 || isBatchLoading}
            class="flex-1 py-4 px-6 bg-blue-800 hover:bg-blue-900 disabled:bg-gray-300 disabled:cursor-not-allowed text-white text-lg font-semibold rounded-xl transition-colors shadow-sm"
          >
            {#if isBatchLoading}
              <span class="flex items-center justify-center gap-3">
                <svg class="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                Processing {batchProgress.current} of {batchProgress.total}...
              </span>
            {:else}
              Verify {batchImages.length} Labels
            {/if}
          </button>

          {#if batchResults.length > 0}
            <button
              onclick={handleBatchReset}
              class="px-6 py-4 border-2 border-gray-400 hover:border-gray-600 text-gray-700 font-semibold rounded-xl transition-colors"
            >
              Reset Batch
            </button>
          {/if}
        </div>

        {#if batchError}
          <div class="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
            {batchError}
          </div>
        {/if}

        <!-- Batch Results -->
        {#if batchResults.length > 0}
          <BatchResults results={batchResults} onDownload={downloadBatchResults} />
        {/if}
      </div>
    {/if}
  </main>
</div>