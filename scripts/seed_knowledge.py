#!/usr/bin/env python3
"""Seed sample knowledge documents and index them (OpenAI embeddings).

Requires OPENAI_API_KEY and DATABASE_URL (see .env.example). Run from repo root:

  python3 scripts/seed_knowledge.py

Idempotent: skips documents that already exist with the same title.
"""

from __future__ import annotations

import asyncio
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
API_ROOT = os.path.join(REPO_ROOT, "apps", "api")
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)


async def _main() -> None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.core.config import get_settings
    from app.db.models.knowledge import KnowledgeDocument
    from app.services.rag.embeddings import EmbeddingService
    from app.services.rag.ingestion import IngestionService

    settings = get_settings()
    if not settings.OPENAI_API_KEY.strip():
        raise SystemExit("OPENAI_API_KEY must be set to seed embeddings.")

    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    specs: list[dict[str, object]] = [
        {
            "title": "[Seed] Tattoo Pricing Guide",
            "service_type": "tattoo",
            "content": """
Small tattoos (under 5 cm) typically start around ₹2000–₹4000 depending on line complexity.
Medium pieces (half sleeve areas, detailed linework) are usually quoted in the ₹8000–₹25000 range.
Large work (full sleeve, back pieces) requires a consultation; artists price by session and detail.
Touch-ups within 90 days may be included—ask at booking. Deposits secure appointments.
""".strip(),
        },
        {
            "title": "[Seed] Tattoo Aftercare",
            "service_type": "tattoo",
            "content": """
Day 1–3: Wash gently with fragrance-free soap, pat dry, apply thin layer of recommended ointment.
Days 4–14: Moisturize after washing; avoid scratching, sun, swimming, and heavy sweating on the area.
Do not submerge in pools or hot tubs until fully healed (about 2–3 weeks).
If you see spreading redness, fever, or pus, contact a medical professional and inform the studio.
""".strip(),
        },
        {
            "title": "[Seed] Piercing Services Overview",
            "service_type": "piercing",
            "content": """
We offer ear (lobe, helix, conch), nostril, septum, lip, eyebrow, and navel piercings using sterile
single-use needles and implant-grade jewelry options. Basic lobe pairs often start around ₹1500;
cartilage and facial piercings vary by jewelry. We do not offer dermal anchors or genital piercings.
Walk-ins welcome when available; booking reduces wait time.
""".strip(),
        },
        {
            "title": "[Seed] Piercing Aftercare",
            "service_type": "piercing",
            "content": """
Clean twice daily with sterile saline solution or saline wound wash—no alcohol or hydrogen peroxide.
Dry with clean gauze or a lint-free towel. Avoid rotating or moving the jewelry excessively.
Sleep on the opposite side for ear and facial piercings when possible. Downsize jewelry only when
your piercer says it is safe. Signs of trouble: embedded jewelry, rapid swelling, or dark lines
under the skin—contact the studio or a doctor promptly.
""".strip(),
        },
        {
            "title": "[Seed] Dreadlock Services & Maintenance",
            "service_type": "dreadlock",
            "content": """
We create and maintain dreadlocks with sectioning, palm rolling, interlocking, or crochet methods
depending on hair texture and client preference. New sets require patience—maturation can take months.
Maintenance visits tidy roots and loose hair; we recommend scheduling every 4–8 weeks for active growth.
Use residue-free shampoos; avoid heavy waxes. Ask about starter pricing and time estimates at consult.
""".strip(),
        },
        {
            "title": "[Seed] Studio Policies",
            "service_type": "general",
            "content": """
Valid government ID is required for tattoo and piercing services. Minors require guardian presence
and consent per local law. Bookings may need a deposit; deposits apply to the final service total.
Cancellations within 24 hours may forfeit the deposit. We maintain a respectful, safe environment;
harassment results in refusal of service.
""".strip(),
        },
        {
            "title": "[Seed] Opening Hours",
            "service_type": "general",
            "content": """
Tuesday–Friday: 12:00–20:00. Saturday: 11:00–19:00. Sunday–Monday: closed unless special events.
Hours may change on holidays—message us on Instagram to confirm before travelling.
""".strip(),
        },
        {
            "title": "[Seed] Quick FAQ",
            "service_type": "general",
            "source_type": "faq",
            "faq_items": [
                {
                    "q": "Do you take walk-ins?",
                    "a": "Yes when artists are free, but appointments get priority and shorter waits.",
                },
                {
                    "q": "How do I book?",
                    "a": "DM us on Instagram or call the studio line with your idea, placement, and timing.",
                },
                {
                    "q": "Is piercing jewelry included?",
                    "a": "Basic sterile starter jewelry is included; upgrades are quoted separately.",
                },
            ],
            "content": "FAQ entries stored in metadata_json.faq_items.",
        },
    ]

    embed = EmbeddingService(api_key=settings.OPENAI_API_KEY, model=settings.EMBEDDING_MODEL)

    async with factory() as session:
        ingestion = IngestionService(session, embed)
        created = 0
        indexed = 0
        for spec in specs:
            title = str(spec["title"])
            existing = (
                await session.execute(
                    select(KnowledgeDocument).where(KnowledgeDocument.title == title),
                )
            ).scalar_one_or_none()
            if existing is not None:
                print(f"skip existing: {title}")
                continue

            source_type = str(spec.get("source_type", "manual"))
            meta: dict | None = None
            st = str(spec["service_type"])
            if source_type == "faq" and "faq_items" in spec:
                meta = {"service_type": st, "faq_items": spec["faq_items"]}
            else:
                meta = {"service_type": st}

            doc = KnowledgeDocument(
                title=title,
                source_type=source_type,
                language="en",
                content=str(spec["content"]),
                status="active",
                metadata_json=meta,
            )
            session.add(doc)
            await session.flush()
            chunks = await ingestion.ingest_document(doc)
            created += 1
            indexed += len(chunks)
            print(f"created: {title} ({len(chunks)} chunks)")

        await session.commit()

    await engine.dispose()
    print(f"done: {created} new documents, {indexed} new chunks indexed")


if __name__ == "__main__":
    asyncio.run(_main())
