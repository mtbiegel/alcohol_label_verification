<script lang="ts">
	import PairUpload from '$lib/components/PairUpload.svelte';
	import ResultsViewer from '$lib/components/ResultsViewer.svelte';
	import Modal from '$lib/components/Modal.svelte';
	import type { FilePair, VerificationResult } from '$lib/types';

	let pairs = $state<FilePair[]>([]);
	let isProcessing = $state(false);
	let processedPairs = $state<FilePair[]>([]);
	let currentIndex = $state(0);
	let error = $state<string | null>(null);
	let showWarning = $state(false);
	let showHelp = $state(false);
	let processingProgress = $state({ current: 0, total: 0 });

	let attribute_blur = 7;
	let background_opacity = 0.8;
	let background_size = 100;
	const BATCH_SIZE = 4;
	let currentBatchSize = BATCH_SIZE;

	let pairUploadRef = $state<any>(null);

	const completePairsCount = $derived(pairs.filter((p) => p.status === 'complete').length);
	const incompletePairsCount = $derived(pairs.filter((p) => p.status !== 'complete').length);

	function handlePairsUpdate(newPairs: FilePair[]) {
		pairs = newPairs;
		error = null;
	}

	async function handleVerifyAll() {
		const completePairs = pairs.filter((p) => p.status === 'complete');

		if (completePairs.length === 0) {
			error =
				'No complete pairs to verify. Please ensure each image has a matching application file.';
			return;
		}

		if (incompletePairsCount > 0) {
			showWarning = true;
			return;
		}

		await processVerification();
	}

	function openHelp() {
		showHelp = true;
	}

	async function processVerification() {
		showWarning = false;
		const completePairs = pairs.filter((p) => p.status === 'complete');

		isProcessing = true;
		error = null;
		processedPairs = [];
		processingProgress = { current: 0, total: completePairs.length };

		for (let i = 0; i < completePairs.length; i += BATCH_SIZE) {
			const batch = completePairs.slice(i, i + BATCH_SIZE);

			currentBatchSize = batch.length;

			try {
				const formData = new FormData();

				for (const pair of batch) {
					formData.append('images', pair.imageFile!);
				}

				const appDataArray = batch.map((pair) => ({
					baseName: pair.baseName,
					...pair.applicationData
				}));
				formData.append('applicationData', JSON.stringify(appDataArray));

				const response = await fetch('/api/verify-batch', {
					method: 'POST',
					body: formData
				});

				if (!response.ok) {
					throw new Error(`Server error: ${response.status}`);
				}

				const batchResults = await response.json();

				for (let j = 0; j < batch.length; j++) {
					const pair = batch[j];
					const result = batchResults[j];

					processedPairs.push({
						...pair,
						result: result
					});

					processingProgress.current++;
				}
			} catch (err) {
				for (const pair of batch) {
					processedPairs.push({
						...pair,
						result: {
							overallStatus: 'rejected',
							summary: err instanceof Error ? err.message : 'Processing failed',
							fields: []
						}
					});
					processingProgress.current++;
				}
			}
		}

		isProcessing = false;
		currentIndex = 0;
	}

	function handleReset() {
		if (pairUploadRef) {
			pairs.forEach((p) => pairUploadRef.removePair(p.baseName));
		}

		pairs = [];
		processedPairs = [];
		currentIndex = 0;
		error = null;
		processingProgress = { current: 0, total: 0 };
	}

	function downloadTemplate() {
		const csv = `brand_name,class_type,alcohol_content_amount,alcohol_content_format,net_contents_amount,net_contents_unit,producer_name
    Midnight Ember,Smoky Bourbon Whiskey,47,%,750,mL,Midnight Ember Distillery`;

		const blob = new Blob([csv], { type: 'text/csv' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = 'application_template.csv';
		a.click();
		URL.revokeObjectURL(url);
	}
</script>

<div class="relative min-h-screen">
	<!-- Background Logo -->
	<div
		class="pointer-events-none fixed inset-0"
		style="
      z-index: -1;
      background-image: url('/background.png');
      background-repeat: no-repeat;
      background-position: center center;
      background-size: {background_size}%;
      opacity: {background_opacity};
    "
	></div>

	<header class="bg-blue-900 text-white shadow-lg">
		<div class="mx-auto max-w-7xl px-6 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<button onclick={handleReset} class="cursor-pointer rounded p-1">
						<img src="/treasury_logo.svg" alt="Treasury Logo" width="80" height="80" />
					</button>
					<div>
						<h1 class="text-xl font-bold tracking-wide">ProofCheck™</h1>
						<p class="text-sm text-blue-200">
							Alcohol Beverage Label Compliance Tool
							<br />
							by the U.S. Alcohol and Tobacco Tax and Trade Bureau
						</p>
					</div>
				</div>
				<div class="flex items-center gap-3">
					<button
						onclick={handleReset}
						class="flex cursor-pointer items-center rounded-lg bg-white px-4 py-2 font-semibold text-blue-900 shadow-sm transition-colors hover:bg-blue-200"
					>
						<svg class="mr-2 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<circle
								cx="12"
								cy="12"
								r="10"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							/>
							<line
								x1="12"
								y1="8"
								x2="12"
								y2="16"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							/>
							<line
								x1="8"
								y1="12"
								x2="16"
								y2="12"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							/>
						</svg>
						Verify New Labels
					</button>

					<button
						onclick={openHelp}
						class="cursor-pointer rounded-lg bg-white px-4 py-2 font-semibold text-blue-900 shadow-sm transition-colors hover:bg-blue-200"
					>
						Using ProofCheck™
					</button>

					<button
						onclick={downloadTemplate}
						class="flex cursor-pointer items-center gap-2 rounded-lg bg-white px-4 py-2 font-semibold text-blue-900 shadow-sm transition-colors hover:bg-blue-200"
					>
						<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
							/>
						</svg>
						Download Template
					</button>
				</div>
			</div>
		</div>
	</header>

	<main class="mx-auto max-w-7xl px-6 py-8">
		{#if processedPairs.length === 0}
			<!-- Upload Section -->
			<div class="space-y-6">
				<section
					class="rounded-xl border border-white/40 p-6"
					style="
          background: rgba(255, 255, 255, 0.45);
          backdrop-filter: blur({attribute_blur}px);
          -webkit-backdrop-filter: blur(16px);
          box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255,255,255,0.8);
          "
				>
					<div class="mb-4">
						<h2 class="text-lg font-semibold text-gray-900">Upload Labels & Applications</h2>
						<p class="mt-1 text-sm text-gray-800">
							NAMING SCHEME: Upload paired files & replace LABEL_NAME with the label's name:
							<code class="rounded bg-gray-200 px-1">LABEL_NAME_image.ext</code>
							and
							<code class="rounded bg-gray-50 px-1">LABEL_NAME_application.csv</code>
						</p>
					</div>

					<PairUpload bind:this={pairUploadRef} onPairsUpdate={handlePairsUpdate} {pairs} />
				</section>
				<div class="flex gap-4">
					<button
						onclick={handleVerifyAll}
						disabled={isProcessing || completePairsCount === 0}
						class="flex-1 cursor-pointer rounded-xl bg-blue-800 px-6 py-4 text-lg font-semibold text-white shadow-sm transition-colors hover:bg-blue-900 disabled:cursor-not-allowed disabled:bg-gray-300"
					>
						{#if isProcessing}
							<span class="flex items-center justify-center gap-3">
								<svg class="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
									<circle
										class="opacity-25"
										cx="12"
										cy="12"
										r="10"
										stroke="currentColor"
										stroke-width="4"
									/>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
								</svg>
								Processing {processingProgress.total} label{processingProgress.total !== 1
									? 's'
									: ''}...
							</span>
						{:else}
							Verify {completePairsCount} Label{completePairsCount !== 1 ? 's' : ''}
						{/if}
					</button>

					{#if pairs.length > 0}
						<button
							onclick={handleReset}
							disabled={isProcessing}
							class="cursor-pointer rounded-xl border-2 border-gray-400 px-6 py-4 font-semibold text-gray-700 transition-colors hover:border-gray-600 disabled:border-gray-300 disabled:text-gray-400"
						>
							Clear All
						</button>
					{/if}
				</div>

				{#if error}
					<div class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
						{error}
					</div>
				{/if}
			</div>
		{:else}
			<!-- Results Section -->
			<ResultsViewer
				pairs={processedPairs}
				bind:currentIndex
				onReset={handleReset}
				processingProgress={isProcessing ? processingProgress : null}
				batchSize={currentBatchSize}
			/>
		{/if}

		<Modal
			show={showHelp}
			title="How to use the ProofCheck™"
			cancelText="Close"
			onCancel={() => (showHelp = false)}
			modalSize="3xl"
		>
			<h1 class="font-bold">About</h1>
			<p>
				This app helps government workers determine if alcohol beverage labels meet regulations set
				by the Alcohol and Tobacco Tax and Trade Bureau (TTB). It allows workers to quickly verify
				labels match corresponding application information and meet requirements.
			</p>
			<br />
			<h1 class="font-bold">How to use</h1>
			<ol class="list-inside list-decimal">
				<li>Download Application Template:</li>
				<p>
					Download the application template from the button in the top right corner. Use this
					template as the starting point for bottlers and producers to input data; this way, data
					can easily be loaded into the ProofCheck™. Once the information is populated into the CSV
					fields, follow the next step for file naming scheme.
				</p>
				<br />
				<li>Proper File Naming Scheme</li>
				<p>
					Rename files such that the image file has LABEL_image.ext, replacing LABEL with a constant
					name, adding the "_image.ext" where .ext is the original image extension. Repeat this
					process for the application file, replacing LABEL with the same constant name used on the
					image, adding the "_application.csv" suffix. As a result, the image and application file
					pair have the same constant name you defined as the prefix with corresponding suffixes.
				</p>
				<br />
				<li>Upload Image & Application Pair</li>
				<p>
					There are 2 methods to upload image and application pairs: You can drag and drop the image
					and application pair into the drop zone, or you can click the upload box and browse for
					image and applicaiton pair through the OS. Once you select a pair, it will show up in the
					"Uploaded Pairs" section and tell you if the pair is ready for valdiating or if it is
					missing an entry (i.e missing the image or the application).
				</p>
				<br />
				<li>Run Validation</li>
				<p>
					Once you have valid pair(s), click the "Verify" button at the bottom of the webpage. The
					processing will start and route you to the Results page once completed. Each pair
					validation takes approximately 5 seconds to complete. The UI will let you know of any
					invalid pairs. Clicking the "Verify" button will prompt you with a warning that a pair(s)
					is incomplete. Incomplete pairs will not be processed.
				</p>
				<br />
				<li>Results & Downloadables</li>
				Once pair(s) have been processed and redirected to the Results page, there will be the following
				attributes: Count for total, approved, needs-review, and rejected categories. Below that is the
				individual hueristcs of the processed pairs with more detail about the results; next to that is
				an image preview of the label you are observing. You are able to toggle through all the pair results
				if you uploaded multiple pairs. You are able to download the hueristics from this validation run
				with the "Download All Results as CSV" button. If you uploaded multiple pairs, you will see a
				progress bar at the top of this page showing how many pairs are still processing.
			</ol>
		</Modal>
	</main>
</div>

<!-- Warning Modal -->
<Modal
	show={showWarning}
	title=""
	onConfirm={processVerification}
	onCancel={() => (showWarning = false)}
	modalSize="sm"
	confirmText="Continue Anyway"
>
	<div class="flex items-start gap-4">
		<div class="flex-shrink-0">
			<svg class="h-12 w-12 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
				/>
			</svg>
		</div>
		<div class="flex-1">
			<h3 class="mb-2 text-lg font-semibold text-gray-900">Incomplete Pairs Detected</h3>
			<p class="mb-4 text-sm text-gray-600">
				{incompletePairsCount} file pair{incompletePairsCount !== 1 ? 's are' : ' is'} missing (either
				an image or application file). Only the {completePairsCount} complete pair{completePairsCount !==
				1
					? 's'
					: ''} will be verified.
			</p>
		</div>
	</div>
</Modal>
