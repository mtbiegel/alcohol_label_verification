<script lang="ts">
	import '../app.css';

	let { children } = $props();
	let logo = '/treasury_logo.svg';
</script>

<svelte:head>
	<link rel="icon" href={logo} />
	<title>ProofCheck™ Verifier - TTB</title>
</svelte:head>
{@render children()}
