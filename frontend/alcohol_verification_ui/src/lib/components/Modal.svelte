<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  export let open = false;
  export let title = "Modal Title";
</script>

{#if open}
  <div
    class="fixed inset-0 flex items-center justify-center z-50"
    style="background: rgba(0,0,0,0.4); backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);"
  >
    <!-- Modal panel -->
    <div
      class="bg-white rounded-xl shadow-2xl w-11/12 max-w-lg p-6 relative"
      style="backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);"
    >
      <!-- Close button -->
      <button
        class="absolute top-3 right-3 text-gray-400 hover:text-gray-700"
        on:click={() => dispatch('close')}
      >
        &times;
      </button>

      <!-- Title -->
      <h2 class="text-xl font-semibold mb-4 text-gray-800">{title}</h2>

      <!-- Slot for content -->
      <div class="text-gray-700 text-sm space-y-2">
        <slot></slot>
      </div>
    </div>
  </div>
{/if}
