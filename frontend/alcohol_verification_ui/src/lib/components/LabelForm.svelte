<script lang="ts">
  import type { ApplicationData } from '$lib/types';
  let { data = $bindable() }: { data: ApplicationData } = $props();

  const fields: { key: keyof ApplicationData; label: string; placeholder: string; multiline?: boolean }[] = [
    { key: 'brandName', label: 'Brand Name', placeholder: 'e.g. OLD TOM DISTILLERY' },
    { key: 'classType', label: 'Class / Type', placeholder: 'e.g. Kentucky Straight Bourbon Whiskey' },
    { key: 'alcoholContent', label: 'Alcohol Content', placeholder: 'e.g. 45% Alc./Vol. (90 Proof)' },
    { key: 'netContents', label: 'Net Contents', placeholder: 'e.g. 750 mL' },
    { key: 'producerName', label: 'Bottler / Producer Name & Address', placeholder: 'e.g. Old Tom Distillery, Louisville, KY' },
    { key: 'countryOfOrigin', label: 'Country of Origin', placeholder: 'e.g. USA (or leave blank if domestic)' },
    { key: 'governmentWarning', label: 'Government Warning Statement', placeholder: 'GOVERNMENT WARNING: ...', multiline: true }
  ];
</script>

<div class="flex flex-col gap-4">
  {#each fields as field}
    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1" for={field.key}>
        {field.label}
      </label>
      {#if field.multiline}
        <textarea
          id={field.key}
          bind:value={data[field.key]}
          placeholder={field.placeholder}
          rows="3"
          class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
        ></textarea>
      {:else}
        <input
          id={field.key}
          type="text"
          bind:value={data[field.key]}
          placeholder={field.placeholder}
          class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      {/if}
    </div>
  {/each}
</div>