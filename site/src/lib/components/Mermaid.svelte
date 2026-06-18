<script lang="ts">
	import { onMount } from "svelte";

	let { chart } = $props<{ chart: string }>();

	let svg = $state("");
	let error = $state("");
	let mounted = false;

	let nextId = 0;

	async function renderDiagram(): Promise<void> {
		try {
			error = "";
			svg = "";
			const { default: mermaid } = await import("mermaid");
			mermaid.initialize({
				startOnLoad: false,
				securityLevel: "loose",
				theme: "base",
				themeVariables: {
					background: "#121420",
					primaryColor: "#1d2438",
					primaryTextColor: "#e6e8ef",
					primaryBorderColor: "#60a5fa",
					lineColor: "#93c5fd",
					secondaryColor: "#0f172a",
					tertiaryColor: "#111827",
					clusterBkg: "#101726",
					clusterBorder: "#334155",
					fontFamily: "Inter, sans-serif"
				}
			});

			nextId += 1;
			const { svg: rendered } = await mermaid.render(`diagram-${nextId}`, chart);
			svg = rendered;
		} catch (renderError) {
			error = renderError instanceof Error ? renderError.message : "Unable to render Mermaid.";
		}
	}

	onMount(() => {
		mounted = true;
		void renderDiagram();
	});

	$effect(() => {
		chart;
		if (mounted) {
			void renderDiagram();
		}
	});
</script>

<div class="diagram-shell">
	{#if error}
		<div class="diagram-error">
			<strong>Diagram unavailable.</strong>
			<p>{error}</p>
			<pre><code>{chart}</code></pre>
		</div>
	{:else if svg}
		<div class="diagram-markup">{@html svg}</div>
	{:else}
		<div class="diagram-loading">Rendering diagram...</div>
	{/if}
</div>

<style>
	.diagram-shell {
		margin: 1.4rem 0;
		padding: 1rem;
		background: rgba(9, 12, 22, 0.86);
		border: 1px solid rgba(148, 163, 184, 0.14);
		border-radius: 22px;
		overflow-x: auto;
	}

	.diagram-loading,
	.diagram-error p {
		color: var(--muted);
	}

	.diagram-error strong {
		color: #f8fbff;
	}

	.diagram-markup {
		min-width: 680px;
	}

	:global(.diagram-markup svg) {
		display: block;
		height: auto;
		max-width: 100%;
	}

	@media (max-width: 720px) {
		.diagram-markup {
			min-width: 520px;
		}
	}
</style>
