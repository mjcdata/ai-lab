# AI Lab

AI Lab is a long-term, hands-on workspace for learning machine learning, generative AI, and AI engineering.

## Initial structure

Keep the initial workspace limited to:

```text
AI-Lab/
├── machine-learning/
├── generative-ai/
├── modules/
├── README.md
└── AGENTS.md
```

- `machine-learning/`: traditional ML, model training, evaluation, prediction, and the ML lifecycle.
- `generative-ai/`: LLMs, RAG, agents, MCP, local models (including models served through LM Studio), and related experiments.
- `modules/`: reusable Python capabilities that emerge from actual projects. Keep project-specific code with its project until there is a clear reason to reuse it.

## Working principles

- Keep the structure minimal. Do not add folders or infrastructure for hypothetical future needs.
- Keep projects isolated and modular, with their own dependencies and environments as needed. Use `uv` for Python project and environment management.
- Prefer simple, replaceable components and avoid tightly coupling projects.
- Let the architecture evolve with learning and actual project needs.
- Extract reusable modules only when projects demonstrate a clear need. Do not build a speculative shared framework.
- Apply AI engineering across projects rather than creating a separate folder. Add APIs, model serving, MCP, testing, environments, Docker, deployment, observability, evaluation, and similar capabilities when needed.

## Initial setup scope

When setting up the lab, create only the structure above and concise README and AGENTS documentation explaining these principles. Do not create example projects or additional infrastructure unless explicitly requested.
