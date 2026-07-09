# Skill pack: perfect prompt manager
_Learned 2026-06-07 22:06_

# EXPERT SKILL PACK: PERFECT PROMPT MANAGER

*Compiled from trained knowledge — no live web access used. All content reflects expertise as of early 2025.*

---

## OVERVIEW

A Prompt Manager is a systematic approach to creating, organizing, versioning, testing, and deploying prompts used with large language models (LLMs). As AI becomes embedded in workflows, treating prompts as managed assets — not throwaway text — is the difference between brittle, inconsistent AI behavior and reliable, scalable AI performance.

A "perfect" prompt manager combines the disciplines of software engineering (version control, testing), UX design (clarity, intent), and knowledge management (taxonomy, retrieval). Whether you are a solo practitioner, a product team, or an enterprise AI ops group, prompt management prevents prompt rot, enables collaboration, and turns prompting from art into engineering.

---

## CORE CONCEPTS

**Prompt as an Asset**
A prompt is not a chat message. It is a structured artifact with a lifecycle: creation, testing, deployment, iteration, and retirement. Treat it accordingly.

**Prompt Anatomy**
Every well-formed prompt has identifiable layers:
- System context (role, persona, constraints, format rules)
- Task instruction (what the model must do)
- Input variables (placeholders filled at runtime)
- Output specification (format, length, tone, schema)
- Examples (few-shot demonstrations)
- Guard rails (what to avoid, how to handle edge cases)

**Prompt Variables and Templates**
A raw prompt hardcoded with specific content is brittle. Template-based prompts use placeholders like {{customer_name}} or {{product_category}} that are populated dynamically. This separation of logic from data is foundational.

**Versioning**
Every change to a prompt creates a new version. Version 1.0 vs 1.1 vs 2.0 distinctions matter because a prompt change can silently break downstream behavior. You need to know what changed, when, and why.

**Prompt Metadata**
Each prompt should carry: unique ID, version number, author, creation date, last modified date, model target (GPT-4, Claude 3, Gemini), use case tag, performance notes, and status (draft, staging, production, deprecated).

**Evaluation (Evals)**
Prompts must be tested against defined success criteria before deployment. Evals are the quality gate. Without them you are guessing.

**Prompt Chaining and Orchestration**
Many real-world tasks require sequences of prompts where the output of one becomes the input of the next. A prompt manager must track these relationships, not just individual prompts in isolation.

**Model Sensitivity**
The same prompt can behave differently across models, temperatures, and even across model versions of the same family. A prompt tuned for GPT-3.5 may need significant adjustment for GPT-4o or Claude 3 Opus.

---

## STEP-BY-STEP WORKFLOW

**Step 1: Capture and Draft**
Begin with intent. Write a one-sentence goal: "This prompt extra