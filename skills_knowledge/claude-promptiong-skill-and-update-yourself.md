# Skill pack: claude promptiong skill and update yourself
_Learned 2026-06-09 12:50_

SKILL PACK: Claude Prompting Mastery
(Built from my own trained knowledge — no live web access used. All guidance reflects Claude's design principles and behavior as I understand them through my training cutoff.)

---

OVERVIEW

Claude is Anthropic's large language model designed with a strong emphasis on helpfulness, harmlessness, and honesty. Prompting Claude effectively is both a craft and a science. Claude responds distinctively to tone, structure, role framing, and explicit instruction in ways that differ meaningfully from other models. Mastering Claude prompting means understanding its constitutional training, its tendency toward nuanced reasoning, its preference for collaborative dialogue, and how to harness its strengths in long-context tasks, analysis, writing, and code. This skill pack treats you as a practitioner building real workflows.

---

CORE CONCEPTS

Constitutional AI Alignment
Claude is trained via Constitutional AI, meaning it has internalized a set of principles rather than just reward signals. It will push back on requests it finds harmful, but it also genuinely tries to be maximally helpful within those constraints. Understanding this means you work with its values rather than trying to route around them.

Context Window and Attention
Claude has a large context window (up to 200K tokens in Claude 3 models). It attends carefully to material placed at the beginning and end of prompts. Middle sections can receive slightly less weight in very long contexts, a known phenomenon sometimes called lost-in-the-middle. Structure your prompts accordingly.

The Helpful Assistant Prior
Claude defaults to being a cooperative assistant. It will attempt to answer even ambiguous prompts. This means you must be deliberate about what you actually want or it will fill gaps with plausible but possibly wrong assumptions.

Instruction Hierarchy
Claude processes and prioritizes instructions roughly in this order: system prompt, then human turn, then its own trained dispositions. When system prompt and human turn conflict, system prompt usually wins unless the instruction crosses an ethical line.

Verbosity and Hedging Defaults
Left unprompted, Claude tends toward thoroughness and often adds caveats. This is useful in research contexts but can bloat outputs. You can and should instruct it explicitly to suppress unnecessary hedging.

Steerability
Claude is highly steerable. Tone, persona, format, length, reasoning style, and output structure are all things you can specify and Claude will follow reliably. This is one of its greatest strengths.

---

STEP-BY-STEP WORKFLOW

Step 1 — Define Your Objective Precisely
Before writing a single word of prompt, state to yourself in plain language: what is the exact deliverable? A 500-word blog post? A JSON schema? A risk analysis with three scenarios? Vagueness in your mental model produces vagueness in output.

Step 2 — Choose Your Prompt Architecture
Decide between:
- Zero-shot: Just the task, no examples. Works when the task is common and well-defined.
- Few-shot: Provide 2-5 examples of input/output pairs before the actual task. Powerful for format and style calibration.
- Chain-of-thought: Ask Claude to reason step by