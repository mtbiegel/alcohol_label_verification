<!-- MIT License
Copyright (c) 2026 Mark Biegel
See LICENSE file for full license text. -->

<script lang="ts">
	// Props passed into the modal
	export let show = false;
	export let title: string;
	export let icon: any = null;
	export let onCancel: () => void = () => {};
	export let onConfirm: (() => void) | null = null;
	export let confirmText: string = 'OK';
	export let cancelText: string = 'Cancel';
	export let modalSize: string = 'xl';
	export let showTestData = false;

	// Close modal when clicking on backdrop
	function handleBackdropClick(e: MouseEvent | KeyboardEvent) {
		if (e.target === e.currentTarget) {
			onCancel();
		}
	}

	// Close modal when pressing Escape
	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			onCancel();
		}
	}

	// Prevent event bubbling for inner elements
	function stopPropagation(e: Event) {
		e.stopPropagation();
	}
</script>

<!-- Modal wrapper -->
{#if show}
	<div
		role="dialog"
		aria-modal="true"
		aria-labelledby="modal-title"
		class="fixed inset-0 z-50 flex items-center justify-center bg-white/0 backdrop-blur-sm"
		style="background-color: rgba(255, 255, 255, 0.2);"
		on:click={handleBackdropClick}
		on:keydown={handleKeydown}
		tabindex="-1"
	>
		<!-- Modal content container -->
		<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
		<!-- svelte-ignore a11y-click-events-have-key-events -->
		<div
			class={`mx-4 rounded-lg bg-white p-6 max-w-${modalSize}`}
			on:click|stopPropagation
			role="document"
		>
			<div class="flex items-start gap-4">
				<!-- Optional icon display -->
				{#if icon}
					<div class="shrink-0">
						{#if typeof icon === 'string'}
							{@html icon}
						{:else}
							{#await icon}
								<span>Loading icon...</span>
							{/await}
						{/if}
					</div>
				{/if}

				<!-- Modal body -->
				<div class="flex-1">
					<h3 id="modal-title" class="mb-2 text-lg font-semibold text-gray-900">{title}</h3>
					<div class="mb-4 text-sm text-gray-600">
						<slot />
					</div>

					<!-- Modal action buttons -->
					<div class="flex justify-end gap-3">
						<button
							type="button"
							on:click={onCancel}
							class="cursor-pointer px-4 py-2 font-semibold text-gray-700 transition-colors hover:text-gray-900"
						>
							{cancelText}
						</button>
						{#if showTestData}
							<!-- Download Example Files only in help menu -->
							<a href="/example_pairings.zip" download>
								<button class="download-test-data-button-design">
									<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
										/>
									</svg>
									Example Data (ZIP)
								</button>
							</a>
						{/if}
						{#if onConfirm}
							<button
								type="button"
								on:click={onConfirm}
								class="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-blue-700"
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
