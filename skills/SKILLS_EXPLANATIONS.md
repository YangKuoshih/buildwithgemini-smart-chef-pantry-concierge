# Agent Skills Reference Catalog & Explanations Guide

This document provides a comprehensive guide to all agent skills available in the environment. Each skill is categorized, explained in detail, and accompanied by usage criteria, key commands, and architectural patterns.

---

## Master Skills Index

| # | Category | Skill Name | Folder Path | Summary |
|---|:---|:---|:---|:---|
| 1 | **Workspace / Lab** | `build-agent-frontend` | `01_workspace_lab_skills/build-agent-frontend` | Chat UI + FastAPI A2A proxy + A2UI v0.8 card renderer deployed to Cloud Run. |
| 2 | **Workspace / Lab** | `build-rag` | `01_workspace_lab_skills/build-rag` | Serverless Vertex AI RAG Engine corpus creation & agent retrieval function tool. |
| 3 | **Workspace / Lab** | `enable-a2ui` | `01_workspace_lab_skills/enable-a2ui` | Enables ADK agents to emit rich A2UI cards, tables, and images. |
| 4 | **Workspace / Lab** | `setup-memory-bank` | `01_workspace_lab_skills/setup-memory-bank` | Long-term cross-session memory via Vertex AI Memory Bank. |
| 5 | **Workspace / Lab** | `publish-to-github` | `01_workspace_lab_skills/publish-to-github` | GH CLI device-flow sign-in, secret scan, and public repo publishing. |
| 6 | **Workspace / Lab** | `pick-your-agent-project` | `01_workspace_lab_skills/pick-your-agent-project` | Interactive project selection, domain gut-checks, and project briefs. |
| 7 | **Workspace / Lab** | `record-demo` | `01_workspace_lab_skills/record-demo` | Clean automated demo screen recording into an animated GIF. |
| 8 | **Workspace / Lab** | `troubleshoot-lab-setup` | `01_workspace_lab_skills/troubleshoot-lab-setup` | Diagnostics and fixes for IAM, GCP auth, ADC, and API permissions. |
| 9 | **Agents CLI Suite** | `google-agents-cli-adk-code` | `02_agents_cli_suite/google-agents-cli-adk-code` | ADK code patterns: function tools, callbacks, state, workflows. |
| 10 | **Agents CLI Suite** | `google-agents-cli-deploy` | `02_agents_cli_suite/google-agents-cli-deploy` | Deploying agents to Agent Runtime, Cloud Run, GKE, and secret handling. |
| 11 | **Agents CLI Suite** | `google-agents-cli-eval` | `02_agents_cli_suite/google-agents-cli-eval` | Agent evaluation framework, dataset schemas, LLM-as-judge scoring. |
| 12 | **Agents CLI Suite** | `google-agents-cli-observability` | `02_agents_cli_suite/google-agents-cli-observability` | Cloud Trace, telemetry, BigQuery analytics, and AgentOps monitoring. |
| 13 | **Agents CLI Suite** | `google-agents-cli-publish` | `02_agents_cli_suite/google-agents-cli-publish` | Registering agents with Gemini Enterprise and Agent Registry fleet ops. |
| 14 | **Agents CLI Suite** | `google-agents-cli-scaffold` | `02_agents_cli_suite/google-agents-cli-scaffold` | Scaffolding new ADK projects and upgrading configurations. |
| 15 | **Agents CLI Suite** | `google-agents-cli-workflow` | `02_agents_cli_suite/google-agents-cli-workflow` | Full lifecycle guide for developing, testing, evaluating, and shipping. |
| 16 | **Antigravity Built-in** | `agy-customizations` | `03_antigravity_builtin/agy-customizations` | Guide to Antigravity rules, skills, plugins, MCP servers, and hooks. |
| 17 | **Antigravity Built-in** | `antigravity_guide` | `03_antigravity_builtin/antigravity_guide` | Complete reference for Antigravity IDE, CLI (`agy`), and SDK. |
| 18 | **Antigravity Built-in** | `permissioned-github` | `03_antigravity_builtin/permissioned-github` | Safe GitHub interaction rules and permission escalations. |

---

## Section 1: Workspace & Lab Skills

### 1. `build-agent-frontend`
- **Location**: `01_workspace_lab_skills/build-agent-frontend/`
- **What it does**: Provides a complete, ready-to-deploy frontend architecture for ADK agents deployed on Google Cloud Agent Engine. It includes a FastAPI proxy running on Cloud Run communicating via the A2A (Agent-to-Agent) protocol (`jsonrpc`/`http_json`), coupled with a modern responsive HTML/JS chat interface that natively renders A2UI v0.8 cards.
- **When to use**: When you need a web chat interface for a deployed agent, when deploying to Cloud Run, or when sorting out browser-to-proxy-to-agent authentication.
- **When NOT to use**: Do not use for core agent prompt engineering or backend-only business logic.
- **Included Assets**: Complete working template in `template/` (`main.py`, `Dockerfile`, `static/index.html`, `requirements.txt`).

---

### 2. `build-rag`
- **Location**: `01_workspace_lab_skills/build-rag/`
- **What it does**: Creates and manages a serverless Vertex AI RAG Engine corpus (Agent Platform). Uploads documents to Cloud Storage, imports them into the corpus using custom LLM parsing, verifies retrieval independently, and exposes retrieval as a standard ADK function tool (`search_documents`).
- **When to use**: When an agent needs to cite private documents, books, or product catalogs without hallucinating.
- **When NOT to use**: When knowledge fits easily in the model prompt context or is retrieved from structured databases like Cloud SQL or Firestore.
- **Included Assets**: Helper scripts for creating corpora, uploading files, and verifying retrieval standalone.

---

### 3. `enable-a2ui`
- **Location**: `01_workspace_lab_skills/enable-a2ui/`
- **What it does**: Injects A2UI v0.8 capabilities into an ADK agent using an `after_model_callback` (`a2ui_callback`). Emits UI components (cards, lists, tables, key-value rows, and images) rather than raw markdown.
- **When to use**: When you want rich glanceable displays in the ADK Dev UI (`adk web`) or custom frontends.
- **When NOT to use**: When the frontend only supports plain markdown or plain text streams.
- **Included Assets**: Ready-to-use `a2ui_utils.py` and `a2ui_prompt.txt` schema template.

---

### 4. `setup-memory-bank`
- **Location**: `01_workspace_lab_skills/setup-memory-bank/`
- **What it does**: Configures persistent cross-session memory using Vertex AI Memory Bank. Adds `PreloadMemoryTool` to agent tools (READ) and `generate_memories_callback` in `after_agent_callback` (WRITE).
- **When to use**: When an agent must remember user preferences, dietary restrictions, allergies, or past context across completely different sessions and devices.
- **When NOT to use**: For short-term conversation context within a single active conversation session (handled automatically by ADK sessions).
- **Included Assets**: Setup scripts, memory service wiring templates, and verification test snippets.

---

### 5. `publish-to-github`
- **Location**: `01_workspace_lab_skills/publish-to-github/`
- **What it does**: Automates publishing ephemeral workstation code to a participant's personal GitHub account using the GitHub CLI device-flow authentication (`github.com/login/device`). Runs a local secret scan, starts a clean commit history, creates a public repository, pushes code, and generates a pre-filled Google Form submission link.
- **When to use**: At the conclusion of a workshop or lab when the user wants to keep their code and claim swag/badges.
- **When NOT to use**: For deploying to cloud infrastructure (Cloud Run or Agent Runtime).
- **Included Assets**: `publish.sh` deterministic helper script.

---

### 6. `pick-your-agent-project`
- **Location**: `01_workspace_lab_skills/pick-your-agent-project/`
- **What it does**: An interactive brainstorming and design skill that guides developers through choosing an agent domain, evaluating tool coverage (memory, function calling, RAG, sandboxing, multimodal), and generating a concise `project_brief.md`.
- **When to use**: At the beginning of a build before scaffolding any code.
- **When NOT to use**: Once code has already been written.
- **Included Assets**: Project brief templates, domain checklists, and tool mapping guides.

---

### 7. `record-demo`
- **Location**: `01_workspace_lab_skills/record-demo/`
- **What it does**: Automates screen and terminal capture inside the lab container to record a clean animated GIF or video showcasing the running application for documentation and READMEs.
- **When to use**: When creating visual assets for GitHub READMEs, hackathons, or project galleries.
- **When NOT to use**: For live presentations.

---

### 8. `troubleshoot-lab-setup`
- **Location**: `01_workspace_lab_skills/troubleshoot-lab-setup/`
- **What it does**: System diagnostic runbook that tests Google Cloud account login, active project configuration, Application Default Credentials (`gcloud auth application-default login`), IAM roles (`roles/aiplatform.user`), and Vertex AI API enablement.
- **When to use**: Right after logging into a workstation, or when encountering `403 PERMISSION_DENIED` errors or deploy failures.
- **When NOT to use**: For general Python debugging or application logic errors.

---

## Section 2: Google Agents CLI Suite

### 9. `google-agents-cli-adk-code`
- **Location**: `02_agents_cli_suite/google-agents-cli-adk-code/`
- **What it does**: Developer reference manual for ADK (Agent Development Kit) code patterns. Details agent definitions (`Agent`, `App`), tool creation (`@tool` decorator, function schemas), callbacks (`before_agent_callback`, `after_model_callback`), state management, and workflow graphs.
- **When to use**: Whenever you are writing or refactoring Python agent code.
- **When NOT to use**: For deployment or scaffolding commands.

---

### 10. `google-agents-cli-deploy`
- **Location**: `02_agents_cli_suite/google-agents-cli-deploy/`
- **What it does**: Guide for deploying agents using `agents-cli deploy` to Google Cloud Agent Runtime (Reasoning Engine), Cloud Run, or GKE. Covers service accounts, secrets injection (`--secret`), wheel packaging, and rollback procedures.
- **When to use**: When shipping an agent to Google Cloud or diagnosing deployment failures.
- **When NOT to use**: For writing agent logic or running evaluations.

---

### 11. `google-agents-cli-eval`
- **Location**: `02_agents_cli_suite/google-agents-cli-eval/`
- **What it does**: Implements the Agent Quality Flywheel evaluation methodology. Guides the creation of test datasets (`eval_dataset.jsonl`), LLM-as-a-judge scoring, metric evaluation (tool trajectory accuracy, response quality, safety), and regression testing.
- **When to use**: When measuring or improving the accuracy, safety, and reliability of an agent.
- **When NOT to use**: For writing agent tools or managing infrastructure.

---

### 12. `google-agents-cli-observability`
- **Location**: `02_agents_cli_suite/google-agents-cli-observability/`
- **What it does**: Covers production monitoring, tracing, and logging for ADK agents. Explains Google Cloud Trace integration, prompt-response logging, BigQuery Agent Analytics, and integrations with third-party observability platforms (AgentOps, Phoenix, Arize).
- **When to use**: When setting up monitoring, debugging production latency, or auditing agent tool calls.
- **When NOT to use**: For initial local prototyping.

---

### 13. `google-agents-cli-publish`
- **Location**: `02_agents_cli_suite/google-agents-cli-publish/`
- **What it does**: Covers registering deployed agents with Gemini Enterprise and Agent Registry via `agents-cli publish gemini-enterprise`. Supports both ADK and A2A protocols and manages enterprise agent fleets.
- **When to use**: When making an agent discoverable in enterprise catalogs or Gemini Enterprise.
- **When NOT to use**: When deploying raw containers to Cloud Run.

---

### 14. `google-agents-cli-scaffold`
- **Location**: `02_agents_cli_suite/google-agents-cli-scaffold/`
- **What it does**: Details commands for creating and enhancing agent projects: `agents-cli scaffold create`, `scaffold enhance`, and `scaffold upgrade`. Sets up directory structure, dependency locks, and Dockerfiles.
- **When to use**: When bootstrapping a new project or updating project scaffolding.
- **When NOT to use**: For writing specific tool logic inside an existing agent.

---

### 15. `google-agents-cli-workflow`
- **Location**: `02_agents_cli_suite/google-agents-cli-workflow/`
- **What it does**: The central umbrella development lifecycle guide for ADK agents. Details the end-to-end flow: Prototype -> Scaffold -> Build Tools -> Evaluate -> Deploy -> Publish -> Observe.
- **When to use**: General entrypoint whenever building an ADK agent.
- **When NOT to use**: When you need deep code-level tool examples (use `adk-code`).

---

## Section 3: Antigravity Built-in Skills

### 16. `agy-customizations`
- **Location**: `03_antigravity_builtin/agy-customizations/`
- **What it does**: Complete architecture reference for extending the Antigravity assistant system. Covers the discovery mechanism, loading priorities, and design patterns for custom skills (`SKILL.md`), workspace rules (`.gemini/rules/`), plugins, lifecycle hooks, and MCP (Model Context Protocol) servers.
- **When to use**: When building custom skills, writing system rules, or integrating MCP servers into Antigravity.
- **When NOT to use**: For standard Python coding tasks unrelated to assistant customization.

---

### 17. `antigravity_guide`
- **Location**: `03_antigravity_builtin/antigravity_guide/`
- **What it does**: Complete user manual and sitemap for Google Antigravity (AGY). Documents the Antigravity IDE, CLI commands (`agy`), Python SDK, slash commands (`/goal`, `/schedule`, `/browser`, `/grill-me`, `/learn`), and configuration settings.
- **When to use**: When asking questions about how to use, configure, or automate Antigravity.
- **When NOT to use**: For agent domain logic.

---

### 18. `permissioned-github`
- **Location**: `03_antigravity_builtin/permissioned-github/`
- **What it does**: Platform security policy and guidelines for executing GitHub operations safely within the agent runtime. Enforces the use of `gh` CLI with explicit `-R ORG/REPO` qualifiers and restricts dangerous unprompted operations.
- **When to use**: When formulating automated GitHub interaction routines or diagnosing restricted command failures.
- **When NOT to use**: When running simple local Git commands.
