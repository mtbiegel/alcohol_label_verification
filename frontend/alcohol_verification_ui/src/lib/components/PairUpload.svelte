<!-- MIT License
Copyright (c) 2026 Mark Biegel
See LICENSE file for full license text. -->

<script lang="ts">
	// Imports
	import Modal from '$lib/components/Modal.svelte';
	import type { FilePair, ApplicationData } from '$lib/types';

	// Props
	let { onPairsUpdate }: { onPairsUpdate: (pairs: FilePair[]) => void } = $props();

	// State variables
	let pairs = $state<Map<string, FilePair>>(new Map());
	let isDragging = $state(false);
	let fileInputElement: HTMLInputElement;

	// Modal state for rejected files
	let showRejectedFilesModal = $state(false);
	let rejectedFilesList = $state<string[]>([]);

	// Allowed file extensions
	const ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp'];
	const ALLOWED_APPLICATION_EXTENSION = '.csv';

	// Check if file type is valid
	function isValidFileType(filename: string, type: 'image' | 'application'): boolean {
		const ext = filename.substring(filename.lastIndexOf('.')).toLowerCase();

		if (type === 'image') {
			return ALLOWED_IMAGE_EXTENSIONS.includes(ext);
		} else if (type === 'application') {
			return ext === ALLOWED_APPLICATION_EXTENSION;
		}

		return false;
	}

	// Extract base name and type from file name
	function extractBaseName(filename: string): {
		baseName: string;
		type: 'image' | 'application' | null;
	} {
		const nameWithoutExt = filename.substring(0, filename.lastIndexOf('.'));

		if (nameWithoutExt.endsWith('_image')) {
			return { baseName: nameWithoutExt.replace('_image', ''), type: 'image' };
		} else if (nameWithoutExt.endsWith('_application')) {
			return { baseName: nameWithoutExt.replace('_application', ''), type: 'application' };
		}

		return { baseName: nameWithoutExt, type: null };
	}

	// Process uploaded files and update pairs
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

			if (!isValidFileType(file.name, type)) {
				console.warn(`File ${file.name} has invalid file type`);
				rejectedFiles.push(`${file.name} (invalid type)`);
				continue;
			}

			let existingPair = newPairs.get(baseName);

			let pair: FilePair;
			if (existingPair) {
				pair = { ...existingPair };
			} else {
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

			// Recalculate pair status
			if (pair.imageFile && pair.applicationFile && pair.applicationData) {
				pair.status = 'complete';
			} else if (pair.imageFile && !pair.applicationFile) {
				pair.status = 'missing-application';
			} else if (!pair.imageFile && pair.applicationFile) {
				pair.status = 'missing-image';
			}

			newPairs.set(baseName, pair);
		}

		pairs = new Map(newPairs);
		onPairsUpdate(Array.from(pairs.values()));

		if (rejectedFiles.length > 0) {
			rejectedFilesList = rejectedFiles;
			showRejectedFilesModal = true;
		}
	}

	// Parse CSV text into ApplicationData object
	function parseCSVFile(csvText: string): ApplicationData {
		const lines = csvText.trim().split('\n');
		if (lines.length < 2) {
			throw new Error('CSV file must have headers and at least one data row');
		}

		const headers = lines[0].split(',').map((h) => h.trim());
		const values = lines[1].split(',').map((v) => v.trim());

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

	// Drag-and-drop event handlers
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

	// File input change handler
	function handleFileInput(e: Event) {
		const input = e.target as HTMLInputElement;
		if (input.files) {
			processFiles(input.files);
		}
	}

	// Remove a pair from the list
	export function removePair(baseName: string) {
		const newPairs = new Map(pairs);
		newPairs.delete(baseName);
		pairs = newPairs;
		onPairsUpdate(Array.from(pairs.values()));
	}

	// Reset all pairs
	export function resetPairs() {
		pairs = new Map();
		onPairsUpdate([]);
	}

	// Open file browser
	function openFileBrowser() {
		fileInputElement?.click();
	}

	// Status configuration for display
	const statusConfig = {
		complete: { color: 'text-green-600', icon: '✓', label: 'Ready' },
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
		class="dropzone {isDragging ? 'dropzone-dragging' : 'dropzone-idle'}"
	>
		<svg
			class="mx-auto mb-3 h-12 w-12 text-blue-700"
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="1.5"
				d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
			/>
		</svg>
		<p class="mb-2 font-medium text-gray-900">Drop files here or click to browse</p>
		<p class="text-sm text-gray-700">Upload image and CSV application files</p>
		<p class="mt-2 text-xs text-gray-600">
			Files must follow scheme: <strong>LABEL_NAME_image.ext</strong> and
			<strong>LABEL_NAME_application.csv</strong>
			<br>
			Accepted image file types are <strong>.jpg, .png, & .webp</strong> and <strong>application types is .csv</strong>
		</p>
	</div>

	<!-- Hidden file input -->
	<input
		bind:this={fileInputElement}
		type="file"
		multiple
		accept=".jpg, .jpeg, .png, .webp, .csv"
		onchange={handleFileInput}
		class="hidden"
	/>

	<!-- Uploaded Pairs List -->
	{#if pairs.size > 0}
		<div class="space-y-2">
			<h3 class="mb-2 text-sm font-semibold text-gray-700">Uploaded Pairs ({pairs.size})</h3>
			{#each Array.from(pairs.values()) as pair}
				<div
					class="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-3"
				>
					<div class="flex flex-1 items-center gap-3">
						<span class="text-lg {statusConfig[pair.status].color}">
							{statusConfig[pair.status].icon}
						</span>
						<div class="flex-1">
							<p class="font-medium text-gray-800">{pair.baseName}</p>
							<p class="text-xs text-gray-500">{statusConfig[pair.status].label}</p>
						</div>
						<div class="flex gap-2 text-xs">
							{#if pair.imageFile}
								<span class="status-valid-image">Image ✓</span>
							{:else}
								<span class="status-missing">Image ✗</span>
							{/if}
							{#if pair.applicationFile}
								<span class="status-valid-app">App ✓</span>
							{:else}
								<span class="status-missing">App ✗</span>
							{/if}
						</div>
					</div>
					<button
						onclick={() => removePair(pair.baseName)}
						class="ml-4 cursor-pointer text-sm font-semibold text-red-600 transition-colors hover:text-slate-800"
					>
						Remove
					</button>
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- Rejected Files Modal -->
<Modal
	bind:show={showRejectedFilesModal}
	title="Invalid Files Detected"
	icon={`<svg class="w-12 h-12 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
  </svg>`}
	confirmText="OK"
	cancelText=""
	modalSize="lg"
	onCancel={() => (showRejectedFilesModal = false)}
	onConfirm={() => (showRejectedFilesModal = false)}
>
	<!-- Rejected files list -->
	<p class="mb-3">The following files were rejected due to a mismatch:</p>
	<ul class="mb-3 max-h-48 list-disc space-y-1 overflow-y-auto pl-5">
		{#each rejectedFilesList as file}
			<li class="text-sm text-gray-700">{file}</li>
		{/each}
	</ul>
	<p class="rounded bg-gray-50 p-2 text-xs text-gray-500">
		<strong>Naming Convention: </strong>The naming convention could be incorrect:
		<span class="inline-block w-full indent-8">Images = "_image.ext"</span>
		<span class="inline-block w-full indent-8">Applications = "_application.csv"</span>
	</p>
	<p class="rounded bg-gray-50 p-2 text-xs text-gray-500">
		<strong>Allowed file types:</strong> .jpg, .jpeg, .png, .webp (images) and .csv (applications)
	</p>
</Modal>
