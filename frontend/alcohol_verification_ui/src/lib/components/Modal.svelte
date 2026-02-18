<script lang="ts">
  export let show = false; // controls visibility
  export let title: string;
  export let message: string;
  export let icon: any = null; // optional SVG or component
  export let onCancel: () => void = () => {};
  export let onConfirm: (() => void) | null = null;
  export let confirmText: string = "OK";
  export let cancelText: string = "Cancel";
</script>

{#if show}
  <div
    class="fixed inset-0 flex items-center justify-center z-50 bg-white/0 backdrop-blur-sm"
    style="background-color: rgba(255, 255, 255, 0.2);" 
    on:click={onCancel}
  >
    <div class="bg-white rounded-lg p-6 max-w-md mx-4" on:click|stopPropagation>
      <div class="flex items-start gap-4">
        {#if icon}
          <div class="flex-shrink-0">
            {#if typeof icon === "string"}
              {@html icon} <!-- raw SVG string if passed -->
            {:else}
              {#await icon}
                <span>Loading icon...</span>
              {/await}
            {/if}
          </div>
        {/if}

        <div class="flex-1">
          <h3 class="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
          <p class="text-sm text-gray-600 mb-4">{message}</p>
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