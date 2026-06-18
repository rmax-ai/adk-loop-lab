# Memory Systems In Agent Workflows

Memory systems separate long-lived knowledge from immediate execution state.
Episodic memory captures what happened in a specific run, such as failures,
observations, and successful steps. Semantic memory stores distilled facts or
patterns that may help future runs. These memories should not replace current
authoritative state, because memory can be stale or only partially verified.
Strong designs require evidence before promoting information into reusable
memory, and they keep current loop state distinct from accumulated experience.
