<script lang="ts">
  export let show = false;
  export let title: string;
  export let icon: any = null;
  export let onCancel: () => void = () => {};
  export let onConfirm: (() => void) | null = null;
  export let confirmText: string = "OK";
  export let cancelText: string = "Cancel";
  export let modalSize: string = "1xl";

  function handleBackdropClick(e: MouseEvent | KeyboardEvent) {
    if (e.target === e.currentTarget) {
      onCancel();
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      onCancel();
    }
  }
</script>

{#if show}
  <div
    role="dialog"
    aria-modal="true"
    aria-labelledby="modal-title"
    class="fixed inset-0 flex items-center justify-center z-50 bg-white/0 backdrop-blur-sm"
    style="background-color: rgba(255, 255, 255, 0.2);"
    on:click={handleBackdropClick}
    on:keydown={handleKeydown}
    tabindex="-1"
  >
    <div
      class="bg-white rounded-lg p-6 max-w-{modalSize} mx-4" 
      on:click|stopPropagation
      on:keydown|stopPropagation
      role="document"
    >
      <div class="flex items-start gap-4">
        {#if icon}
          <div class="flex-shrink-0">
            {#if typeof icon === "string"}
              {@html icon}
            {:else}
              {#await icon}
                <span>Loading icon...</span>
              {/await}
            {/if}
          </div>
        {/if}
        <div class="flex-1">
          <h3 id="modal-title" class="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
          <div class="text-sm text-gray-600 mb-4">
            <slot />
          </div>
          <div class="flex gap-3 justify-end">
            <button
              on:click={onCancel}
              class="px-4 py-2 text-gray-700 hover:text-gray-900 font-semibold"
            >
              {cancelText}
            </button>
            {#if onConfirm}
              <button
                on:click={onConfirm}
                class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
              >
                {confirmText}
              </button>
            {/if}
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}