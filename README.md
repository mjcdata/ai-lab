# AI Lab

A long-term, hands-on workspace for learning machine learning, generative AI, and AI engineering through practical projects.

## Structure

```text
AI Lab/
├── machine-learning/
├── generative-ai/
├── modules/
├── README.md
└── AGENTS.md
```

- **machine-learning/** — Traditional ML, model training, evaluation, prediction, and the ML lifecycle.
- **generative-ai/** — LLMs, RAG, agents, MCP, local models served through tools such as LM Studio, and related experiments.
- **modules/** — Reusable Python capabilities extracted from actual projects when there is a clear reason to share them.
- **AGENTS.md** — Guidance for coding agents working in the lab.

## How to work

Keep projects isolated and modular. Each project can manage its own dependencies and environment using `uv`. Keep project-specific code inside its project until reuse is justified.

Build AI engineering experience across projects: introduce testing, APIs, model serving, MCP, Docker, deployment, observability, evaluation, and other practices as they become necessary. AI engineering does not have a separate folder.

Prefer simple, replaceable components. Avoid tightly coupling projects, creating speculative infrastructure, or designing a large shared framework. Let the architecture evolve with experience and actual needs.

## Getting started

Choose one small project with a concrete outcome and place it in the appropriate area. Let its requirements drive the first environment, dependencies, and engineering practices. The initial lab contains no example projects or additional infrastructure.
