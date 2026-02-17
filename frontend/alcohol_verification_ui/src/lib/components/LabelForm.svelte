<script lang="ts">
  import type { ApplicationData } from '$lib/types';
  let { data = $bindable() }: { data: ApplicationData } = $props();

  const fields: { key: keyof ApplicationData; label: string; placeholder: string; multiline?: boolean }[] = [
    { key: 'brand_name', label: 'Brand Name', placeholder: 'e.g. OLD TOM DISTILLERY' },
    { key: 'class_type', label: 'Class / Type', placeholder: 'e.g. Kentucky Straight Bourbon Whiskey' },
    { key: 'producer_name', label: 'Bottler / Producer Name & Address', placeholder: 'e.g. Old Tom Distillery, Louisville, KY' },
    { key: 'country_of_origin', label: 'Country of Origin', placeholder: 'e.g. USA (or leave blank if domestic)' },
  ];

  const volumeUnits = ['mL', 'L', 'fl oz', 'pt', 'pint', 'gal'];
  const alcoholFormats = ['%', 'Alc/Vol', 'Alc./Vol.', 'Alc', 'Alc.', 'ABV'];
</script>

<div class="flex flex-col gap-4">
  <!-- Brand Name -->
  <div>
    <label class="block text-sm font-medium text-gray-700 mb-1" for="brand_name">Brand Name*</label>
    <input
      id="brand_name"
      type="text"
      bind:value={data.brand_name}
      placeholder="e.g. OLD TOM DISTILLERY"
      class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
    />
  </div>

  <!-- Class Type -->
  <div>
    <label class="block text-sm font-medium text-gray-700 mb-1" for="class_type">Class / Type*</label>
    <input
      id="class_type"
      type="text"
      bind:value={data.class_type}
      placeholder="e.g. Kentucky Straight Bourbon Whiskey"
      class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
    />
  </div>

  <!-- Alcohol Content | Net Contents (side by side) -->
  <div class="flex gap-4">

    <!-- Alcohol Content -->
    <div class="flex-1">
      <label class="block text-sm font-medium text-gray-700 mb-1">Alcohol Content*</label>
      <div class="flex gap-2">
        <input
          type="number"
          bind:value={data.alcohol_content_amount}
          placeholder="45"
          class="w-20 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <select
          bind:value={data.alcohol_content_format}
          class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          {#each alcoholFormats as format}
            <option value={format}>{format}</option>
          {/each}
        </select>
      </div>
    </div>

    <!-- Net Contents -->
    <div class="flex-1">
      <label class="block text-sm font-medium text-gray-700 mb-1">Net Contents*</label>
      <div class="flex gap-2">
        <input
          type="number"
          bind:value={data.net_contents_amount}
          placeholder="750"
          class="w-20 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <select
          bind:value={data.net_contents_unit}
          class="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          {#each volumeUnits as unit}
            <option value={unit}>{unit}</option>
          {/each}
        </select>
      </div>
    </div>

  </div>

  <!-- Bottler / Producer -->
  <div>
    <label class="block text-sm font-medium text-gray-700 mb-1" for="producer_name">Bottler / Producer Name & Address</label>
    <input
      id="producer_name"
      type="text"
      bind:value={data.producer_name}
      placeholder="e.g. Old Tom Distillery, Louisville, KY"
      class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
    />
  </div>

  <!-- Country of Origin -->
  <div>
    <label class="block text-sm font-medium text-gray-700 mb-1" for="country_of_origin">Country of Origin</label>
    <input
      id="country_of_origin"
      type="text"
      bind:value={data.country_of_origin}
      placeholder="e.g. USA"
      class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
    />
  </div>
</div>