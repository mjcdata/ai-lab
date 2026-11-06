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

## Development workflow

- Use ChatGPT Voice for collaborative planning and requirements decisions; record approved decisions in repository documentation.
- Treat GitHub as the shared source of truth for plans, code, and progress. Read the latest relevant commits and project work plan before implementing changes.
- Prefer cloud Codex for routine implementation, small-scale tests, and committing completed code to GitHub. Use local Codex when direct access to the MacBook, local datasets, or runtime troubleshooting is needed.
- Keep large dataset downloads, substantial data processing, and model training on the MacBook unless the user explicitly approves another environment. The user initiates these large local runs.
- Implement clearly approved tasks autonomously, but request user approval for material changes to scope, data sources, methodology, architecture, costs, deployment, or other consequential decisions.
- For manually initiated Codex sessions, commit approved, tested changes directly to `main` rather than creating pull requests. GitHub Actions is test-only and must not run Codex or use an OpenAI API key. Do not create feature branches or PRs for routine implementation. Before pushing, sync with the current `origin/main`; if it has moved, stop rather than force-push or overwrite concurrent work.
- Run relevant available tests before committing; if tests fail, do not push. Never force-push. Preserve approval gates and the restriction on large data acquisition, costs, and deployment. Direct-to-main permission is not permission to bypass those gates.
- GitHub Actions CI runs offline tests on pushes to `main` and manual dispatch. It does not implement tasks, run Codex, or push changes. Start Codex manually for explicitly approved `[CODEX-READY]` tasks.
- Follow project-specific work plans for deliverables; keep lab-wide operating rules here.
