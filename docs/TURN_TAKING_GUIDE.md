# Turn-Taking Guidelines

This guide summarizes key insights from Harvey Sacks' 1974 paper *"A Simplest Systematics for the Organization of Turn-Taking for Conversation"* and explains how they inform the three-way AI collaboration platform.

## Core Turn-Taking Rules

Sacks, Schegloff, and Jefferson describe a set of rules for how conversational turns are allocated. At each **transition-relevance place** (TRP) – a potential break where one speaker may yield the floor – one of three options occurs:

1. **Current speaker selects next**: if the current speaker addresses or otherwise selects a participant, that participant has the right and obligation to take the next turn.
2. **Self-selection**: if no selection is made, any other participant may start speaking; the first to do so gains the turn.
3. **Current speaker continues**: if no one self-selects, the current speaker may continue with another turn-constructional unit.

These rules are intended to minimize gaps and overlaps while allowing flexible participation【F:/tmp/sacks.txt†L1988-L2022】.

## Multi-Party Considerations

With more than two participants, turn distribution becomes important. Sacks notes that once a third party is involved, "next turn" is no longer guaranteed for any waiting participant. To avoid leaving someone out, turn sizes tend to shrink and participants often rely on explicit selection or self‑selection to claim the floor【F:/tmp/sacks.txt†L4160-L4188】.

## Application in Collaborate

The **ResponseCoordinator** now reflects these principles:

- **Explicit Mentions First** – When the user addresses `@openai` or `@xai` (or uses cues like "your turn, xai"), that provider is placed at the front of the speaking queue regardless of relevance score. This implements the "current speaker selects next" rule.
- **Relevance‑Based Self‑Selection** – If no explicit mention is made, providers with scores above the relevance threshold may self‑select. The highest‑scoring provider speaks next.
- **Fallback Continuation** – If neither condition produces a candidate, the system picks the best available provider so the conversation continues smoothly.

See `ResponseCoordinator._build_speaking_queue()` for the updated logic implementing these rules【F:src/core/response_coordinator.py†L340-L404】.

## Tips for Users

- **Direct your question** to a specific AI if you want it to respond next (e.g., `@openai` or "xAI, what do you think?").
- **Keep turns concise** when both AIs are active so neither model is left out.
- **Allow self‑selection** by occasionally asking open questions to invite responses from either AI.

Following these guidelines helps maintain a smooth three‑way conversation where all participants get a fair chance to contribute.

## Encouraging Cross-Talk

Each AI's system prompt now includes a **COLLABORATION CONTEXT** hint generated from the most recent responses. This hint nudges the models to address each other by name, build on or challenge earlier points, and ask clarifying questions when appropriate. The result is an exchange that feels more like real dialogue among three people instead of isolated replies.
