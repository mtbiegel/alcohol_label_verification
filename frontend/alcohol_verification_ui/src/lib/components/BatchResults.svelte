<script lang="ts">
  import type { VerificationResult } from '$lib/types';
  
  let { 
    results,
    onDownload
  }: { 
    results: Array<{filename: string, result: VerificationResult}>,
    onDownload: () => void
  } = $props();

  const statusColors = {
    approved: 'bg-green-100 text-green-800',
    review: 'bg-yellow-100 text-yellow-800',
    rejected: 'bg-red-100 text-red-800'
  };

  const fieldStatusIcons = {
    pass: '✓',
    warning: '⚠️',
    fail: '✗'
  };
</script>

<section class="rounded-xl border border-white/40 p-6"
  style="
  background: rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.8);
  "
>
  <div class="flex items-center justify-between mb-4">
    <h2 class="text-lg font-semibold text-gray-800">Batch Results ({results.length} labels)</h2>
    <button
      onclick={onDownload}
      class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-semibold"
    >
      Download CSV Report
    </button>
  </div>

  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b-2 border-gray-300">
          <th class="text-left p-3 font-semibold">Filename</th>
          <th class="text-left p-3 font-semibold">Overall Status</th>
          <th class="text-center p-3 font-semibold">Brand</th>
          <th class="text-center p-3 font-semibold">Class/Type</th>
          <th class="text-center p-3 font-semibold">ABV</th>
          <th class="text-center p-3 font-semibold">Volume</th>
          <th class="text-center p-3 font-semibold">Warning</th>
        </tr>
      </thead>
      <tbody>
        {#each results as { filename, result }}
          <tr class="border-b border-gray-200 hover:bg-white/50 transition-colors">
            <td class="p-3 font-medium text-gray-700">{filename}</td>
            <td class="p-3">
              <span class="px-3 py-1 rounded-full text-xs font-semibold {statusColors[result.overallStatus]}">
                {result.overallStatus.toUpperCase()}
              </span>
            </td>
            {#each result.fields as field}
              <td class="p-3 text-center text-lg">
                <span class="{field.status === 'pass' ? 'text-green-600' : field.status === 'warning' ? 'text-yellow-600' : 'text-red-600'}">
                  {fieldStatusIcons[field.status]}
                </span>
              </td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>

  <div class="mt-4 text-sm text-gray-600">
    <p>
      <span class="font-semibold">Summary:</span>
      {results.filter(r => r.result.overallStatus === 'approved').length} approved,
      {results.filter(r => r.result.overallStatus === 'review').length} need review,
      {results.filter(r => r.result.overallStatus === 'rejected').length} rejected
    </p>
  </div>
</section>