# Skill pack: Perfect AI
_Learned 2026-06-07 22:03_

JARVIS SKILL PACK — PERFECT AI
Compiled from internal training knowledge. No live web access used. All content reflects expertise embedded in my training data through early 2025.

---

OVERVIEW

"Perfect AI" is not a single product or method — it is a practitioner's goal: getting the maximum useful, accurate, and reliable output from AI systems through intelligent prompting, system design, evaluation, and iteration. Whether you are using large language models (LLMs), image generators, code assistants, or agentic systems, "perfecting" AI means closing the gap between what you ask and what you actually need. It spans prompt engineering, model selection, output evaluation, fine-tuning, retrieval-augmented generation, and responsible deployment. Mastery here is a force multiplier across every domain.

---

CORE CONCEPTS

1. The Intent-Output Gap
The core problem in AI use. Your mental model of what you want rarely matches what the model receives as instruction. Closing this gap is the central skill.

2. Context Window
LLMs operate on a fixed window of tokens (words/pieces). Everything the model "knows" during a session lives inside this window. Managing it well is critical for long tasks.

3. Temperature and Sampling Parameters
Temperature controls randomness. Low temperature (0–0.3) gives focused, deterministic output. High temperature (0.7–1.0) gives creative, varied output. Top-p, top-k, and frequency penalties further shape output distribution.

4. System Prompts vs. User Prompts
The system prompt sets the model's persona, rules, and constraints. The user prompt is the live instruction. Understanding this separation lets you architect reliable AI behavior.

5. Tokens and Latency
Longer prompts cost more tokens and increase latency. Efficiency in prompt design has real cost and speed consequences in production.

6. Hallucination
Models generate plausible-sounding text that can be factually wrong. They do not "know" things the way humans do — they predict likely next tokens. This is the single most dangerous property to manage.

7. Grounding
Connecting AI output to verifiable external sources — databases, documents, APIs — to reduce hallucination and increase accuracy. Retrieval-Augmented Generation (RAG) is the dominant grounding technique.

8. Fine-Tuning vs. Prompting
Prompting adjusts behavior at inference time with no model changes. Fine-tuning retrains a model on your data to bake in specialized behavior permanently. Each has trade-offs in cost, flexibility, and effectiveness.

9. Agentic AI
AI systems that take sequences of actions, use tools, call APIs, write and execute code, and operate autonomously toward a goal. Agents introduce compounding error risk and require robust guardrails.

10. Evaluation (Evals)
Systematic measurement of AI output quality. Without evals, you are flying blind. Good evals define what "perfect" actually means in your context.

---

STEP-BY-STEP WORKFLOW

STEP 1 — DEFINE YOUR OBJECTIVE PRECISELY
Before touching a prompt