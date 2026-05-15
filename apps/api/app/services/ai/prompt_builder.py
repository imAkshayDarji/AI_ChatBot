"""Build multi-turn chat messages for AI providers."""

from __future__ import annotations

from app.services.ai.prompts.recommendation_prompts import RECOMMENDATION_SYSTEM_PROMPT
from app.services.ai.prompts.safety_prompts import SAFETY_SYSTEM_PROMPT
from app.services.ai.prompts.system_prompts import (
    AGE_REMINDER,
    BRAND_VOICE_BLOCK,
    HANDOFF_HINTS,
    SUGGESTED_REPLIES_INSTRUCTION,
)
from app.services.rag.retriever import RetrievalResult


class PromptBuilder:
    def build_chat_prompt(
        self,
        user_message: str,
        retrieved_context: list[RetrievalResult],
        conversation_history: list[dict[str, str]],
        language: str = "en",
        lead_info: dict | None = None,
        conversation_summary: str | None = None,
        language_name: str = "English",
    ) -> list[dict[str, str]]:
        """Build message list matching OpenAI-style role/content."""

        rag_block = ""
        if retrieved_context:
            parts = []
            for chunk in retrieved_context:
                parts.append(
                    f"[{chunk.source_title}] (score={chunk.score:.2f})\n{chunk.chunk_text}",
                )
            rag_block = "Retrieved knowledge:\n" + "\n---\n".join(parts)

        lead_block = ""
        if lead_info:
            pairs = [f"{k}: {v}" for k, v in lead_info.items() if v is not None]
            if pairs:
                lead_block = "Known lead hints from earlier in the conversation:\n" + "\n".join(
                    pairs
                )

        summary_block = ""
        if conversation_summary:
            summary_block = f"Earlier conversation summary:\n{conversation_summary}\n"

        system_sections = [
            BRAND_VOICE_BLOCK.strip(),
            SAFETY_SYSTEM_PROMPT,
            RECOMMENDATION_SYSTEM_PROMPT,
            (
                f"Respond in {language_name} (language code: {language})."
                if language == "en"
                else (
                    f"CRITICAL: You MUST respond entirely in {language_name} using its native script. "
                    f"Do NOT use English words or Latin script — every word must be written in the {language_name} script. "
                    f"Translate English terms into {language_name}: "
                    f"e.g. 'tattoo' → use the {language_name} word, 'piercing' → use the {language_name} word, "
                    f"'booking' → use the {language_name} word. "
                    f"The SUGGESTED_REPLIES_JSON must also contain {language_name} text in native script, not English. "
                    f"User may write in Latin script but you must reply in {language_name} script only."
                )
            ),
            HANDOFF_HINTS,
            AGE_REMINDER,
            SUGGESTED_REPLIES_INSTRUCTION,
        ]
        if rag_block:
            system_sections.append(rag_block)
        if summary_block:
            system_sections.append(summary_block)
        if lead_block:
            system_sections.append(lead_block)

        system_content = "\n\n".join(s for s in system_sections if s)

        messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
        messages.extend(dict(m) for m in conversation_history)
        messages.append({"role": "user", "content": user_message})
        return messages
