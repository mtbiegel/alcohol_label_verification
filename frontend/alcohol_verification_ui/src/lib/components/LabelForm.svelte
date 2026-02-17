<script lang="ts">
  import type { ApplicationData } from '$lib/types';
  let { data = $bindable() }: { data: ApplicationData } = $props();

  const fields: { key: keyof ApplicationData; label: string; placeholder: string; multiline?: boolean }[] = [
    { key: 'brand_name', label: 'Brand Name', placeholder: 'e.g. OLD TOM DISTILLERY' },
    { key: 'class_type', label: 'Class / Type', placeholder: 'e.g. Kentucky Straight Bourbon Whiskey' },
    { key: 'alcohol_content', label: 'Alcohol Content', placeholder: 'e.g. 45% Alc./Vol. (90 Proof)' },
    { key: 'net_contents', label: 'Net Contents', placeholder: 'e.g. 750 mL' },
    { key: 'producer_name', label: 'Bottler / Producer Name & Address', placeholder: 'e.g. Old Tom Distillery, Louisville, KY' },
    { key: 'country_of_origin', label: 'Country of Origin', placeholder: 'e.g. USA (or leave blank if domestic)' },
    { key: 'gov_warning', label: 'Government Warning Statement', placeholder: 'GOVERNMENT WARNING: ...', multiline: true }
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