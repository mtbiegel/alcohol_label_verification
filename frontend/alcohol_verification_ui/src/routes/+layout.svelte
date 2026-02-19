<script lang="ts">
	import './layout.css';
	import '../app.css';

	let { children } = $props();
	let logo = '/treasury_logo.svg';
</script>

<svelte:head><link rel="icon" href={logo} /></svelte:head>
{@render children()}
