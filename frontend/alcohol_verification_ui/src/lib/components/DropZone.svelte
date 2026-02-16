<script lang="ts">
  let { onFileSelect }: { onFileSelect: (file: File) => void } = $props();

  let isDragging = $state(false);
  let inputEl: HTMLInputElement;

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    isDragging = false;
    const file = e.dataTransfer?.files[0];
    if (file && file.type.startsWith('image/')) {
      onFileSelect(file);
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
    const file = input.files?.[0];
    if (file) onFileSelect(file);
  }
</script>

<div
  role="button"
  tabindex="0"
  ondrop={handleDrop}
  ondragover={handleDragOver}
  ondragleave={handleDragLeave}
  onclick={() => inputEl.click()}
  onkeydown={(e) => e.key === 'Enter' && inputEl.click()}
  class="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
    {isDragging
      ? 'border-blue-500 bg-blue-50'
      : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'}"
>
  <svg class="w-10 h-10 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/>
  </svg>
  <p class="text-gray-600 font-medium">Drop label image here</p>
  <p class="text-sm text-gray-400 mt-1">or click to browse</p>
  <p class="text-xs text-gray-300 mt-2">PNG, JPG, WEBP supported</p>

  <input
    bind:this={inputEl}
    type="file"
    accept="image/*"
    class="hidden"
    onchange={handleFileInput}
  />
</div>