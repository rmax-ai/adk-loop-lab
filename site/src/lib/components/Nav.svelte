<script lang="ts">
	import { afterNavigate } from "$app/navigation";
	import { base } from "$app/paths";
	import { page } from "$app/state";

	type NavLink = {
		href: string;
		label: string;
		match: "exact" | "prefix";
	};

	const homeHref = `${base}/`;
	const links: NavLink[] = [
		{ href: homeHref, label: "Home", match: "exact" },
		{ href: `${base}/architecture/`, label: "Architecture", match: "exact" },
		{ href: `${base}/examples/`, label: "Examples", match: "prefix" },
		{ href: `${base}/concepts/`, label: "Concepts", match: "prefix" },
	];

	let open = $state(false);

	afterNavigate(() => {
		open = false;
	});

	function isActive(link: NavLink): boolean {
		const pathname = page.url.pathname;
		if (link.match === "exact") {
			return pathname === link.href;
		}
		return pathname === link.href || pathname.startsWith(link.href);
	}
</script>

<nav class="nav-shell">
	<div class="nav-inner">
		<a class="brand" href={homeHref}>
			<span class="brand-mark">AL</span>
			<span>adk-loop-lab</span>
		</a>

		<button
			class="menu-toggle"
			type="button"
			aria-label="Toggle navigation"
			aria-expanded={open}
			onclick={() => (open = !open)}
		>
			<span></span>
			<span></span>
			<span></span>
		</button>

		<div class:open class="nav-links">
			{#each links as link}
				<a
					class:active={isActive(link)}
					href={link.href}
					onclick={() => (open = false)}
				>
					{link.label}
				</a>
			{/each}
			<a
				class="external"
				href="https://github.com/rmax-ai/adk-loop-lab"
				rel="noreferrer"
				target="_blank"
			>
				GitHub
			</a>
		</div>
	</div>
</nav>

<style>
	.nav-shell {
		position: sticky;
		top: 0;
		z-index: 40;
		padding: 1.1rem 1rem 0;
		backdrop-filter: blur(18px);
	}

	.nav-inner {
		max-width: 1220px;
		margin: 0 auto;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 0.9rem 1rem;
		background: rgba(10, 10, 15, 0.72);
		border: 1px solid rgba(148, 163, 184, 0.16);
		border-radius: 999px;
		box-shadow: 0 18px 45px rgba(2, 6, 23, 0.3);
	}

	.brand {
		display: inline-flex;
		align-items: center;
		gap: 0.75rem;
		color: #f8fbff;
		font-weight: 800;
		letter-spacing: -0.02em;
	}

	.brand-mark {
		display: inline-grid;
		place-items: center;
		width: 2rem;
		height: 2rem;
		border-radius: 999px;
		background: linear-gradient(135deg, rgba(96, 165, 250, 0.96), rgba(52, 211, 153, 0.72));
		color: #03111f;
		font-size: 0.78rem;
	}

	.nav-links {
		display: flex;
		align-items: center;
		gap: 0.35rem;
	}

	.nav-links a {
		padding: 0.52rem 0.85rem;
		border-radius: 999px;
		color: var(--muted);
		font-weight: 600;
	}

	.nav-links a:hover,
	.nav-links a.active {
		background: var(--accent-glow);
		color: #f8fbff;
	}

	.external {
		border: 1px solid rgba(148, 163, 184, 0.16);
	}

	.menu-toggle {
		display: none;
		width: 2.75rem;
		height: 2.75rem;
		padding: 0;
		background: transparent;
		border: 1px solid rgba(148, 163, 184, 0.18);
		border-radius: 999px;
		cursor: pointer;
	}

	.menu-toggle span {
		display: block;
		width: 1.15rem;
		height: 2px;
		margin: 0.22rem auto;
		background: #dbeafe;
		border-radius: 999px;
	}

	@media (max-width: 780px) {
		.nav-inner {
			border-radius: 28px;
			align-items: flex-start;
			flex-wrap: wrap;
		}

		.menu-toggle {
			display: inline-block;
		}

		.nav-links {
			display: none;
			width: 100%;
			flex-direction: column;
			align-items: stretch;
			padding-top: 0.35rem;
		}

		.nav-links.open {
			display: flex;
		}

		.nav-links a {
			padding: 0.75rem 0.2rem;
		}
	}
</style>
