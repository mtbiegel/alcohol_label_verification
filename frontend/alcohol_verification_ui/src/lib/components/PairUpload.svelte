<script lang="ts">
  import Modal from '$lib/components/Modal.svelte'
  import type { FilePair, ApplicationData } from '$lib/types';

  let { onPairsUpdate }: { onPairsUpdate: (pairs: FilePair[]) => void } = $props();

  let pairs = $state<Map<string, FilePair>>(new Map());
  let isDragging = $state(false);
  let fileInputElement: HTMLInputElement;

  // Add these for the modal
  let showRejectedFilesModal = $state(false);
  let rejectedFilesList = $state<string[]>([]);

  const ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp'];
  const ALLOWED_APPLICATION_EXTENSION = '.csv';

  function isValidFileType(filename: string, type: 'image' | 'application'): boolean {
    const ext = filename.substring(filename.lastIndexOf('.')).toLowerCase();
    
    if (type === 'image') {
      return ALLOWED_IMAGE_EXTENSIONS.includes(ext);
    } else if (type === 'application') {
      return ext === ALLOWED_APPLICATION_EXTENSION;
    }
    
    return false;
  }

  function extractBaseName(filename: string): { baseName: string; type: 'image' | 'application' | null } {
    const nameWithoutExt = filename.substring(0, filename.lastIndexOf('.'));
    
    if (nameWithoutExt.endsWith('_image')) {
      return { baseName: nameWithoutExt.replace('_image', ''), type: 'image' };
    } else if (nameWithoutExt.endsWith('_application')) {
      return { baseName: nameWithoutExt.replace('_application', ''), type: 'application' };
    }
    
    return { baseName: nameWithoutExt, type: null };
  }

  async function processFiles(files: FileList | File[]) {
    const fileArray = Array.from(files);
    const newPairs = new Map(pairs);
    const rejectedFiles: string[] = [];

    for (const file of fileArray) {
      const { baseName, type } = extractBaseName(file.name);

      if (!type) {
        console.warn(`File ${file.name} doesn't follow naming convention`);
        rejectedFiles.push(file.name);
        continue;
      }

      // Validate file type
      if (!isValidFileType(file.name, type)) {
        console.warn(`File ${file.name} has invalid file type`);
        rejectedFiles.push(`${file.name} (invalid type)`);
        continue;
      }

      // Get existing pair or create new one
      let existingPair = newPairs.get(baseName);
      
      // IMPORTANT: Always create a NEW object to trigger reactivity
      let pair: FilePair;
      if (existingPair) {
        // Create a new object by spreading the existing one
        pair = { ...existingPair };
      } else {
        // Create a brand new pair
        pair = {
          baseName,
          imageFile: null,
          applicationFile: null,
          applicationData: null,
          status: 'missing-application'
        };
      }

      if (type === 'image') {
        pair.imageFile = file;
      } else if (type === 'application') {
        pair.applicationFile = file;
        try {
          const text = await file.text();
          pair.applicationData = parseCSVFile(text);
        } catch (err) {
          console.error(`Failed to parse ${file.name}:`, err);
          rejectedFiles.push(`${file.name} (parse error)`);
          continue;
        }
      }

      // Recalculate status
      if (pair.imageFile && pair.applicationFile && pair.applicationData) {
        pair.status = 'complete';
      } else if (pair.imageFile && !pair.applicationFile) {
        pair.status = 'missing-application';
      } else if (!pair.imageFile && pair.applicationFile) {
        pair.status = 'missing-image';
      }

      // Set the NEW pair object in the map
      newPairs.set(baseName, pair);
    }

    // Force reactivity by creating new Map
    pairs = new Map(newPairs);
    onPairsUpdate(Array.from(pairs.values()));

    // Show rejected files modal if any
    if (rejectedFiles.length > 0) {
      rejectedFilesList = rejectedFiles;
      showRejectedFilesModal = true;
    }
  }

  function parseCSVFile(csvText: string): ApplicationData {
    const lines = csvText.trim().split('\n');
    if (lines.length < 2) {
      throw new Error('CSV file must have headers and at least one data row');
    }

    const headers = lines[0].split(',').map(h => h.trim());
    const values = lines[1].split(',').map(v => v.trim());

    const data: any = {};
    headers.forEach((header, index) => {
      data[header] = values[index] || '';
    });

    return {
      brand_name: data.brand_name || '',
      class_type: data.class_type || '',
      alcohol_content_amount: data.alcohol_content_amount || '',
      alcohol_content_format: data.alcohol_content_format || '%',
      net_contents_amount: data.net_contents_amount || '',
      net_contents_unit: data.net_contents_unit || 'mL',
      producer_name: data.producer_name || '',
      country_of_origin: data.country_of_origin || ''
    };
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    isDragging = false;
    
    const files = e.dataTransfer?.files;
    if (files) {
      processFiles(files);
    }
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    isDragging = true;
  }

  function handleDragLeave() {
    isDragging = false;
  }

  function handleFileInput(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files) {
      processFiles(input.files);
    }
  }

  export function removePair(baseName: string) {
    const newPairs = new Map(pairs);
    newPairs.delete(baseName);
    pairs = newPairs;
    onPairsUpdate(Array.from(pairs.values()));
  }

  export function resetPairs() {
    pairs = new Map();
    onPairsUpdate([]);
  }

  function openFileBrowser() {
    fileInputElement?.click();
  }

  const statusConfig = {
    'complete': { color: 'text-green-600', icon: '✓', label: 'Ready' },
    'missing-image': { color: 'text-red-600', icon: '✗', label: 'Missing Image' },
    'missing-application': { color: 'text-red-600', icon: '✗', label: 'Missing Application' }
  };
</script>

<div>
  <!-- Drop Zone -->
  <div
    role="button"
    tabindex="0"
    ondrop={handleDrop}
    ondragover={handleDragOver}
    ondragleave={handleDragLeave}
    onclick={openFileBrowser}
    onkeydown={(e) => e.key === 'Enter' && openFileBrowser()}
    class="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors mb-4
      {isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'}"
  >
    <svg class="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
    </svg>
    <p class="text-gray-900 font-medium mb-2">Drop files here or click to browse</p>
    <p class="text-sm text-gray-700">Upload image and CSV application files</p>
    <p class="text-xs text-gray-600 mt-2">Files must follow scheme: <strong>LABEL_NAME_image.ext</strong> and <strong>LABEL_NAME_application.csv</strong></p>
  </div>

  <input
    bind:this={fileInputElement}
    type="file"
    multiple
    accept=".jpg, .jpeg, .png, .webp, .csv"
    onchange={handleFileInput}
    class="hidden"
  />

  <!-- Pairs List -->
  {#if pairs.size > 0}
    <div class="space-y-2">
      <h3 class="text-sm font-semibold text-gray-700 mb-2">Uploaded Pairs ({pairs.size})</h3>
      {#each Array.from(pairs.values()) as pair}
        <div class="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200">
          <div class="flex items-center gap-3 flex-1">
            <span class="text-lg {statusConfig[pair.status].color}">
              {statusConfig[pair.status].icon}
            </span>
            <div class="flex-1">
              <p class="font-medium text-gray-800">{pair.baseName}</p>
              <p class="text-xs text-gray-500">{statusConfig[pair.status].label}</p>
            </div>
            <div class="flex gap-2 text-xs">
              {#if pair.imageFile}
                <span class="px-2 py-1 bg-blue-100 text-blue-700 rounded">Image ✓</span>
              {:else}
                <span class="px-2 py-1 bg-red-100 text-red-700 rounded">Image ✗</span>
              {/if}
              {#if pair.applicationFile}
                <span class="px-2 py-1 bg-green-100 text-green-700 rounded">App ✓</span>
              {:else}
                <span class="px-2 py-1 bg-red-100 text-red-700 rounded">App ✗</span>
              {/if}
            </div>
          </div>
          <button
            onclick={() => removePair(pair.baseName)}
            class="ml-4 text-red-600 hover:text-red-800 text-sm font-semibold"
          >
            Remove
          </button>
        </div>
      {/each}
    </div>
  {/if}
</div>

<Modal
  bind:show={showRejectedFilesModal}
  title="Invalid Files Detected"
  icon={`<svg class="w-12 h-12 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
  </svg>`}
  confirmText="OK"
  cancelText=""
  modalSize="lg"
  onCancel={() => showRejectedFilesModal = false}
  onConfirm={() => showRejectedFilesModal = false}
>
  <p class="mb-3">The following files were rejected due to a mismatch:</p>
  <ul class="list-disc pl-5 space-y-1 mb-3 max-h-48 overflow-y-auto">
    {#each rejectedFilesList as file}
      <li class="text-sm text-gray-700">{file}</li>
    {/each}
  </ul>
  <p class="text-xs text-gray-500 bg-gray-50 p-2 rounded">
    <strong>Naming Convention:</strong>The naming convention could be incorrect:
    <span class="inline-block indent-8 w-full">Images = "_image.ext"</span>
    <span class="inline-block indent-8 w-full">Applications = "_application.csv"</span>
  </p>
  <p class="text-xs text-gray-500 bg-gray-50 p-2 rounded">
    <strong>Allowed file types:</strong> .jpg, .jpeg, .png, .webp (images) and .csv (applications)
  </p>
</Modal>
