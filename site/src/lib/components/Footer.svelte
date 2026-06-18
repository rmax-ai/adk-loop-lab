<footer class="footer">
	<div class="footer-inner">
		<p>MIT licensed. Built as a static SvelteKit site for GitHub Pages.</p>
		<a href="https://github.com/rmax-ai/adk-loop-lab" rel="noreferrer" target="_blank">
			View the repository
		</a>
	</div>
</footer>

<style>
	.footer {
		padding: 2.5rem 1rem 3rem;
	}

	.footer-inner {
		max-width: 1220px;
		margin: 0 auto;
		padding-top: 1.5rem;
		border-top: 1px solid rgba(148, 163, 184, 0.16);
		display: flex;
		justify-content: space-between;
		gap: 1rem;
		color: var(--muted);
		font-size: 0.94rem;
	}

	.footer-inner p {
		margin: 0;
	}

	@media (max-width: 720px) {
		.footer-inner {
			flex-direction: column;
		}
	}
</style>
