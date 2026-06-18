<script lang="ts">
	import { afterNavigate } from "$app/navigation";
	import { onMount, tick } from "svelte";

	import Footer from "$lib/components/Footer.svelte";
	import Nav from "$lib/components/Nav.svelte";

	type TocItem = {
		id: string;
		level: 2 | 3;
		text: string;
	};

	let { title = "", description = "", children } = $props<{
		title?: string;
		description?: string;
		children?: () => unknown;
	}>();

	let articleElement = $state<HTMLElement | null>(null);
	let tocItems = $state<TocItem[]>([]);
	let tocOpen = $state(false);

	function slugify(text: string): string {
		return text
			.toLowerCase()
			.trim()
			.replace(/[^a-z0-9\s-]/g, "")
			.replace(/\s+/g, "-")
			.replace(/-+/g, "-");
	}

	async function updateToc(): Promise<void> {
		await tick();
		if (!articleElement) {
			tocItems = [];
			return;
		}

		const seen = new Map<string, number>();
		const headings = Array.from(articleElement.querySelectorAll("h2, h3"));

		tocItems = headings.map((heading) => {
			const rawText = heading.textContent?.trim() || "section";
			const baseId = slugify(rawText) || "section";
			const count = seen.get(baseId) ?? 0;
			seen.set(baseId, count + 1);
			const id = count === 0 ? baseId : `${baseId}-${count + 1}`;
			heading.id = heading.id || id;

			return {
				id: heading.id,
				level: heading.tagName === "H3" ? 3 : 2,
				text: rawText,
			};
		});
	}

	onMount(() => {
		void updateToc();
	});

	afterNavigate(() => {
		tocOpen = false;
		void updateToc();
	});

	const pageTitle = $derived(title ? `${title} | adk-loop-lab` : "adk-loop-lab");
</script>

<svelte:head>
	<title>{pageTitle}</title>
	{#if description}
		<meta name="description" content={description} />
	{/if}
</svelte:head>

<div class="site-frame">
	<Nav />

	<div class="doc-grid">
		<main class="doc-main">
			<article bind:this={articleElement} class="prose">
				{@render children?.()}
			</article>
		</main>

		{#if tocItems.length > 0}
			<aside class="toc-shell" class:open={tocOpen}>
				<button class="toc-toggle" type="button" onclick={() => (tocOpen = !tocOpen)}>
					On this page
				</button>
				<nav class="toc-nav" aria-label="Table of contents">
					<p>On this page</p>
					{#each tocItems as item}
						<a class:subheading={item.level === 3} href={`#${item.id}`}>{item.text}</a>
					{/each}
				</nav>
			</aside>
		{/if}
	</div>

	<Footer />
</div>

<style>
	.site-frame {
		min-height: 100vh;
	}

	.doc-grid {
		max-width: 1220px;
		margin: 0 auto;
		padding: 1.8rem 1rem 0;
		display: grid;
		grid-template-columns: minmax(0, 1fr) 280px;
		gap: 2rem;
	}

	.doc-main {
		min-width: 0;
	}

	.prose {
		max-width: var(--max-content);
		padding: 2rem;
		background:
			linear-gradient(180deg, rgba(96, 165, 250, 0.06), transparent 20rem),
			var(--bg-elevated);
		border: 1px solid rgba(148, 163, 184, 0.14);
		border-radius: 28px;
		box-shadow: var(--shadow);
	}

	:global(.prose h1) {
		margin: 0 0 1rem;
		font-size: clamp(2.6rem, 5vw, 4.4rem);
		line-height: 0.98;
		letter-spacing: -0.05em;
	}

	:global(.prose h2) {
		margin-top: 2.7rem;
		margin-bottom: 0.9rem;
		font-size: clamp(1.5rem, 3vw, 2rem);
		letter-spacing: -0.03em;
		color: #f6f8ff;
	}

	:global(.prose h3) {
		margin-top: 1.8rem;
		margin-bottom: 0.55rem;
		font-size: 1.12rem;
		color: #edf2ff;
	}

	:global(.prose p) {
		margin: 1rem 0;
		color: var(--text);
	}

	:global(.prose strong) {
		color: #f8fbff;
	}

	:global(.prose .lead) {
		font-size: 1.16rem;
		color: #dce5f7;
	}

	.toc-shell {
		position: sticky;
		top: 6.6rem;
		align-self: start;
	}

	.toc-toggle {
		display: none;
		width: 100%;
		padding: 0.8rem 0.95rem;
		background: rgba(15, 23, 42, 0.82);
		border: 1px solid rgba(148, 163, 184, 0.16);
		border-radius: 16px;
		color: #f8fbff;
		font: inherit;
		text-align: left;
	}

	.toc-nav {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		padding: 1rem;
		background: rgba(12, 16, 28, 0.88);
		border: 1px solid rgba(148, 163, 184, 0.14);
		border-radius: 22px;
	}

	.toc-nav p {
		margin: 0 0 0.4rem;
		color: #f8fbff;
		font-weight: 700;
	}

	.toc-nav a {
		padding: 0.3rem 0;
		color: var(--muted);
		font-size: 0.94rem;
	}

	.toc-nav a.subheading {
		padding-left: 0.9rem;
		font-size: 0.9rem;
	}

	@media (max-width: 1100px) {
		.doc-grid {
			grid-template-columns: 1fr;
		}

		.toc-shell {
			position: static;
			order: -1;
		}

		.toc-toggle {
			display: block;
		}

		.toc-nav {
			display: none;
			margin-top: 0.75rem;
		}

		.toc-shell.open .toc-nav {
			display: flex;
		}
	}

	@media (max-width: 720px) {
		.doc-grid {
			padding-top: 1.1rem;
		}

		.prose {
			padding: 1.35rem;
			border-radius: 22px;
		}
	}
</style>
