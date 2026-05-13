"""Map tasks → chat models (Phase 1: heuristic routing)."""


class ModelRouter:
    """
    Routes to appropriate model based on task complexity.
    - Simple FAQ / greetings -> gpt-4o-mini (cheap)
    - Complex recommendations -> gpt-4o (expensive)
    - Static info -> no model (deterministic)
    """

    def select_model(self, intent: str, complexity: str) -> str | None:
        if intent == "static":
            return None
        if complexity == "complex" or intent == "recommendation":
            return "gpt-4o"
        return "gpt-4o-mini"
