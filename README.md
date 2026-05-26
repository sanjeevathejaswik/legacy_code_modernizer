# Legacy Code Conversion Pipeline

> A multi-agent application that converts monolithic Java legacy code into modern
> Spring Boot 3 microservices — orchestrated by **LangGraph** and powered by
> **Azure OpenAI**.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Pipeline Flow](#pipeline-flow)
4. [Project Structure](#project-structure)
5. [Package Reference](#package-reference)
6. [Agent Reference](#agent-reference)
7. [Prompt Design](#prompt-design)
8. [Observability](#observability)
9. [Reassembly](#reassembly)
10. [Evaluation](#evaluation)
11. [REST API](#rest-api)
12. [Dashboard](#dashboard)
13. [Setup & Usage](#setup--usage)
14. [Output Artefacts](#output-artefacts)
15. [Dependencies](#dependencies)
16. [Configuration Reference](#configuration-reference)

---

## Overview

The pipeline accepts a single legacy Java `.java` file (monolithic, any size) and
automatically:

| Step | What happens |
|------|-------------|
| **Split** | Decompose the monolith into distinct classes / interfaces / enums |
| **Document** | Extract business rules, data models, and service contracts |
| **Audit** | Score documentation quality (0–100); auto-retry with feedback if below threshold |
| **Review Gate** | Pause for human approval (HITL) before spending tokens on conversion |
| **Convert** | Rewrite each module as a Spring Boot 3 / Java 17 component |
| **Test** | Generate JUnit 5 + Mockito test suites per module |
| **Assemble** | Stitch all artefacts into a compilable Maven project tree |
| **Build Verify** | Run `mvn compile` / `javac`; auto-retry Converter with compiler feedback if it fails |

Everything is observable: per-agent timing, token usage, and execution spans are
saved as JSON and visualised in a Streamlit dashboard.

The pipeline is also exposed as a **REST API** (FastAPI + uvicorn), enabling
programmatic job submission, status polling, HITL approve/reject, and ZIP download.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       LangGraph StateGraph                          │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐           │
│  │ Code Splitter│──▶│  Documenter  │──▶│   Auditor    │           │
│  └──────────────┘   └──────────────┘   └──────┬───────┘           │
│                           ▲                    │                   │
│                           │  retry             │ passed/exhausted  │
│                           └────────────────────┤                   │
│                                                ▼                   │
│                                       ┌──────────────┐            │
│                                       │ Review Gate  │ ◀── PAUSE  │
│                                       │    (HITL)    │            │
│                                       └──────┬───────┘            │
│                           ▲                  │                    │
│                           │  reject          │ approve            │
│                           └──────────────────┤                    │
│                                              ▼                    │
│                                     ┌──────────────┐             │
│                                     │  Converter   │◀──┐ retry   │
│                                     └──────┬───────┘   │         │
│                                            ▼           │         │
│                                     ┌──────────────┐   │         │
│                                     │    Tester    │   │         │
│                                     └──────┬───────┘   │         │
│                                            ▼           │         │
│                                     ┌──────────────┐   │         │
│                                     │    Joiner    │   │         │
│                                     └──────┬───────┘   │         │
│                                            ▼           │         │
│                                     ┌──────────────┐   │         │
│                                     │Build Verifier│───┘         │
│                                     └──────┬───────┘             │
│                                            │                     │
│                                           END                    │
└─────────────────────────────────────────────────────────────────────┘

Every node is wrapped by instrument_node() — tracing + metrics are recorded
automatically with zero changes to agent files.
```

### Key Design Decisions

| Concern | Decision | Reason |
|---------|----------|--------|
| **Prompt separation** | All prompt strings live in `prompts/<agent>_prompts.py` | Behavioural logic is not configuration; keeps agent code clean |
| **PromptHelper** | Central class loads, formats, and invokes prompts | Single place to change LLM call behaviour across all agents |
| **State reducers** | `errors` field uses `Annotated[List, operator.add]` | Nodes append errors without overwriting previous ones |
| **Audit retry loop** | Conditional edge: fail → Documenter (with feedback injected) | Guarantees documentation quality before human review |
| **HITL Review Gate** | `langgraph.interrupt()` + `MemorySaver` checkpointer | Pipeline pauses; human approves or rejects via REST API before conversion begins |
| **Build self-healing** | Conditional edge: build fail → Converter (with compiler errors injected) | Automatically repairs classes that fail compilation |
| **Observability** | `instrument_node()` wrapper applied at graph-build time | Zero intrusion into agent files; consistent span/metric coverage |
| **Reassembly** | Separate `DependencyGraph` + `CodeStitcher` + `joiner_node` | Splitting and stitching are symmetric; neither is meaningful alone |
| **Evaluation** | Two-layer scoring: deterministic (45 %) + DeepEval LLM (55 %) | Structural checks catch format gaps; LLM metrics catch semantic gaps |
| **Fully deterministic splitting** | tree-sitter extracts structure; naming conventions assign layer; method signatures generate descriptions — zero LLM cost | Eliminates stubs, removes one LLM call per run, layer correct for 100% of classes |
| **Structured Documenter payload** | Method signatures + field types replace truncated raw code | Documenter sees the full API surface of every class regardless of implementation size |
| **LLM output validation** | Every LLM response is validated and repaired before it drives any decision | Prevents out-of-range scores, missing fields, or non-bool flags from silently corrupting the pipeline |

---

## Pipeline Flow

```
Input: legacy Java file
         │
         ▼
┌──────────────────────┐
│    Code Splitter     │  Fully deterministic — zero LLM cost.
│                      │  tree-sitter extracts: declarations, imports,
│                      │  annotations, superclass, implements, field types,
│                      │  method signatures, dependencies.
│                      │  Layer: annotation map → naming conventions
│                      │  (ChequeProcessor→service, UserRepository→repository)
│                      │  → structural signals → "utility" fallback.
│                      │  Description: built from method signatures + fields.
└──────────┬───────────┘
           │  state["modules"]
           ▼
┌──────────────────────┐
│      Documenter      │  Generates: overview, business_rules,
│                      │  data_models, service_interfaces,
│                      │  module_docs, technical_specs.
│                      │  On retry: re-runs with audit_feedback
└──────────┬───────────┘  injected, fixing only the failing gaps.
           │  state["documentation"]
           ▼
┌──────────────────────┐
│       Auditor        │  Scores documentation 0–100:
│                      │  completeness · accuracy · clarity · coverage
│                      │  Writes: audit_report, audit_feedback
└──────────┬───────────┘
           │
     ┌─────┴──────────────────────────────┐
     │                                    │
     ▼                                    ▼
score < threshold                  score >= threshold
+ retries left                     OR retries exhausted
     │                                    │
     │  audit_retries++                   │
     │  injects audit_feedback            │
     ▼                                    ▼
 Documenter ◄───── (retry loop) ─────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │     Review Gate       │  langgraph.interrupt()
                               │       (HITL)          │  Workflow paused +
                               │                       │  checkpointed via
                               │                       │  MemorySaver.
                               │                       │  Human reviews
                               │                       │  audit_report via
                               │                       │  REST API or dashboard.
                               └──────────┬────────────┘
                                          │  state["hitl_decision"]
                          ┌───────────────┴──────────────┐
                          │                              │
                          ▼                              ▼
                       reject                         approve
                          │                              │
                          │  loops back for              │
                          │  full re-document            │
                          ▼                              ▼
                      Documenter               ┌──────────────────────┐
                                               │      Converter        │  Rewrites each module as
                                               │                       │  Spring Boot 3 / Java 17.
                                               │                       │  Order: model → exception
                                               │                       │  → repo → service
                                               │                       │  → controller → config.
                                               │                       │  On build retry: re-converts
                                               │                       │  only failing classes using
                                               └──────────┬────────────┘  build_feedback.
                                                          │  state["converted_modules"]
                                                          ▼
                                               ┌──────────────────────┐
                                               │        Tester         │  JUnit 5 + Mockito + AssertJ.
                                               │                       │  Given-When-Then per module.
                                               └──────────┬────────────┘  Priority: service → controller
                                                          │  state["test_suites"]     → repository.
                                                          ▼
                                               ┌──────────────────────┐
                                               │    Joiner             │  1. DependencyGraph:
                                               │   (Reassembly)        │     topo sort, cycle detect,
                                               │                       │     microservice grouping.
                                               │                       │  2. LLM: pom.xml, Dockerfile,
                                               │                       │     application.yml.
                                               └──────────┬────────────┘  3. CodeStitcher: Maven tree.
                                                          │  state["assembly_result"]
                                                          ▼
                                               ┌──────────────────────┐
                                               │    Build Verifier     │  mvn compile → javac
                                               │                       │  → LLM static analysis.
                                               │                       │  Writes: build_report,
                                               └──────────┬────────────┘          build_feedback.
                                                          │
                                          ┌───────────────┴──────────────┐
                                          │                              │
                                          ▼                              ▼
                                   build failed                    success / skipped
                                   + retries left                        │
                                          │                              ▼
                                          │  build_retries++       Output: compilable
                                          │  injects               Spring Boot project
                                          │  build_feedback        + Maven structure
                                          ▼  per failing class     + JUnit 5 tests
                                      Converter                    + Observability
                                     (retry loop)                    artefacts
```

---

## Project Structure

```
usecase_02/
│
├── main.py                        Entry point (CLI)
├── config.py                      Reads .env into constants
├── requirements.txt
├── .env.example                   Template — copy to .env
│
├── app/                           FastAPI REST API layer
│   ├── main.py                    uvicorn application entry point
│   ├── api/v1/
│   │   ├── routes_conversion.py   POST /api/v1/convert, GET /api/v1/jobs
│   │   ├── routes_health.py       GET /health
│   │   └── routes_review.py       Job detail, artefacts, download, approve, reject
│   ├── schemas/
│   │   └── job_models.py          Pydantic request/response models
│   └── services/
│       └── pipeline.py            PipelineService + JobRecord (in-memory job store)
│
├── graph/                         LangGraph wiring
│   ├── state.py                   WorkflowState TypedDict (shared state contract)
│   └── workflow.py                StateGraph: nodes, edges, conditional routing
│
├── agents/                        One LangGraph node function per agent
│   ├── code_splitter.py
│   ├── documenter.py
│   ├── auditor.py
│   ├── review_gate.py             HITL interrupt node (MemorySaver checkpoint)
│   ├── converter.py
│   ├── tester.py
│   ├── build_verifier.py          Compilation check + build self-healing trigger
│   └── (joiner lives in reassembly/joiner_agent.py)
│
├── prompts/                       All LLM prompt strings — never inlined in agents
│   ├── code_splitter_prompts.py   SYSTEM + USER_TEMPLATE
│   ├── documenter_prompts.py      SYSTEM, SYSTEM_RETRY + USER_TEMPLATE
│   ├── auditor_prompts.py         SYSTEM (with {threshold}) + USER_TEMPLATE
│   ├── converter_prompts.py       SYSTEM + USER_TEMPLATE
│   ├── tester_prompts.py          SYSTEM + USER_TEMPLATE
│   ├── joiner_prompts.py          SYSTEM + USER_TEMPLATE
│   └── build_verifier_prompts.py  SYSTEM + USER_TEMPLATE
│
├── utils/                         Shared helpers
│   ├── llm_client.py              AzureChatOpenAI wrapper + JSON parser
│   │                              call_llm(... agent_name=) records metrics
│   ├── prompt_helper.py           PromptHelper class — loads prompts, calls LLM
│   ├── file_handler.py            save_json / save_text / load_source_code
│   └── output_formatter.py        Rich console tables, panels, step markers
│
├── observability/                 Pipeline telemetry (zero agent-file changes)
│   ├── logging_config.py          Structured JSONL file logger + Rich console
│   ├── metrics.py                 MetricsCollector — timing, tokens, LLM calls
│   └── tracing.py                 PipelineTracer + instrument_node() wrapper
│
├── reassembly/                    Module reassembly into deployable project
│   ├── dependency_graph.py        DependencyGraph — topo sort, cycle detect, grouping
│   ├── code_stitcher.py           CodeStitcher — writes full Maven project tree
│   └── joiner_agent.py            LangGraph node — orchestrates graph + LLM + stitch
│
├── evaluation/                    Documentation quality scoring (two-layer)
│   ├── deterministic.py           Layer 1: schema, coverage, depth checks (45 %)
│   ├── deepeval_metrics.py        Layer 2: DeepEval summarization/faithfulness/clarity (55 %)
│   └── scorer.py                  Combines layers into a single 0–100 final score
│
├── dashboard/
│   └── app.py                     Streamlit 8-page dashboard
│
└── output/                        Auto-created; all pipeline artefacts land here
    ├── modules/                   modules.json + one .java per module
    ├── docs/                      documentation.json
    ├── audit/                     audit_report.json
    ├── converted/                 one .java per converted module
    │                              conversion_summary.json
    ├── tests/                     one *Test.java per suite
    │                              test_suites_summary.json
    ├── assembled/                 Full Maven project
    │   ├── pom.xml
    │   ├── Dockerfile
    │   ├── src/main/java/...      converted source files
    │   ├── src/test/java/...      test files
    │   ├── src/main/resources/
    │   │   └── application.yml
    │   ├── assembly_manifest.json
    │   └── dependency_graph.json
    ├── build/
    │   └── build_report.json      Compilation result + per-class errors
    ├── observability/
    │   ├── metrics.json           per-agent timing, token counts, LLM calls
    │   └── traces.json            span-level execution trace (Gantt-ready)
    └── logs/
        └── pipeline_<timestamp>.jsonl  Structured JSONL log
```

---

## Package Reference

### `app/`

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI application with CORS middleware; registers all routers |
| `app/api/v1/routes_conversion.py` | `POST /api/v1/convert` (upload file, receive `job_id`); `GET /api/v1/jobs` (list all jobs) |
| `app/api/v1/routes_health.py` | `GET /health` liveness check |
| `app/api/v1/routes_review.py` | `GET /api/v1/jobs/{id}`, `GET /api/v1/jobs/{id}/results/{artifact}`, `GET /api/v1/jobs/{id}/download`, `POST /api/v1/jobs/{id}/approve`, `POST /api/v1/jobs/{id}/reject` |
| `app/schemas/job_models.py` | `JobResponse`, `JobDetail`, `JobList` Pydantic models |
| `app/services/pipeline.py` | `PipelineService` singleton — creates and tracks `JobRecord` objects; starts background pipeline threads; resumes HITL-paused jobs |

### `graph/`

| File | Purpose |
|------|---------|
| `state.py` | Defines `WorkflowState` — the single shared TypedDict that every node reads from and writes to. Uses `Annotated[List[str], operator.add]` on the `errors` field so nodes append without overwriting. |
| `workflow.py` | Constructs the `StateGraph`, wraps every node with `instrument_node()`, defines routing after Auditor (`_route_after_audit`), after Review Gate (`_route_after_review`), and after Build Verifier (`_route_after_build`). Compiled with a `MemorySaver` checkpointer for HITL pause/resume. |

### `agents/`

Each agent is a plain Python function `(state: WorkflowState) -> dict`.
It reads from state, calls the LLM via `PromptHelper`, saves artefacts, and returns
a **partial dict** with only the fields it updated.

### `prompts/`

Each file exports:
- `SYSTEM` — system prompt template (may contain `{placeholder}` syntax)
- `USER_TEMPLATE` — user message template (always contains `{placeholder}` syntax)
- `SYSTEM_<VARIANT>` *(optional)* — alternate system prompt (e.g. `SYSTEM_RETRY`)

`PromptHelper` selects the right template, calls `.format(**kwargs)`, and invokes the LLM.

### `utils/`

| File | Key exports |
|------|-------------|
| `llm_client.py` | `call_llm(system, user, temperature, max_tokens, agent_name)` — `agent_name` triggers automatic metrics recording |
| `prompt_helper.py` | `PromptHelper(agent_name)` — `.system()`, `.user()`, `.invoke()`, `.invoke_and_parse()` |
| `file_handler.py` | `save_json()`, `save_text()`, `load_source_code()`, `ensure_output_dirs()` |
| `output_formatter.py` | `print_step()`, `print_modules_table()`, `print_audit_report()`, `print_conversion_summary()`, `print_test_summary()` |

### `observability/`

| File | Key exports |
|------|-------------|
| `metrics.py` | `MetricsCollector` class; `get_metrics()` / `reset_metrics()` singletons |
| `tracing.py` | `PipelineTracer` class; `instrument_node(name, fn)` wrapper; `get_tracer()` / `reset_tracer()` singletons |
| `logging_config.py` | `setup_pipeline_logging()` — JSONL file + Rich console handlers; `get_logger()` |

### `reassembly/`

| File | Key exports |
|------|-------------|
| `dependency_graph.py` | `DependencyGraph` — `.topological_sort()`, `.detect_cycles()`, `.microservice_groups()`, `.most_depended_on()`, `.to_dict()` |
| `code_stitcher.py` | `CodeStitcher` — `.stitch(project_config, modules, tests, dep_graph)` → `AssemblyManifest` |
| `joiner_agent.py` | `joiner_node(state)` — the LangGraph node |

### `evaluation/`

| File | Purpose |
|------|---------|
| `deterministic.py` | Layer 1 checks: schema completeness (all 6 doc keys present), module coverage (% with a `module_doc`), depth (avg word count of business logic sections) |
| `deepeval_metrics.py` | Layer 2: runs DeepEval `SummarizationMetric`, `FaithfulnessMetric`, `GEval` (clarity) against the generated documentation |
| `scorer.py` | `compute(det, llm) → dict` — combines both layers into a final 0–100 score with per-dimension breakdown |

**Weight breakdown** (defined as constants in `scorer.py`, easy to tune):

| Dimension | Layer | Weight |
|-----------|-------|--------|
| Summarization | DeepEval | 35 % |
| Faithfulness | DeepEval | 30 % |
| Clarity | DeepEval | 15 % |
| Coverage | Deterministic | 10 % |
| Schema | Deterministic | 5 % |
| Depth | Deterministic | 5 % |

---

## Agent Reference

### WorkflowState fields

| Field | Type | Written by |
|-------|------|-----------|
| `source_code` | `str` | Input |
| `source_file_path` | `str` | Input |
| `modules` | `List[Module]` | Code Splitter |
| `documentation` | `Dict` | Documenter |
| `audit_report` | `AuditReport` | Auditor |
| `audit_feedback` | `str` | Auditor |
| `audit_retries` | `int` | Auditor |
| `hitl_decision` | `str` (`"approve"` / `"reject"` / `""`) | Review Gate |
| `awaiting_review` | `bool` | Review Gate |
| `converted_modules` | `List[ConvertedModule]` | Converter |
| `test_suites` | `List[TestSuite]` | Tester |
| `assembly_result` | `Dict` | Joiner |
| `build_report` | `Dict` | Build Verifier |
| `build_feedback` | `str` | Build Verifier |
| `build_retries` | `int` | Build Verifier |
| `metrics_summary` | `Dict` | instrument_node wrapper |
| `trace_data` | `Dict` | instrument_node wrapper |
| `errors` | `Annotated[List[str], operator.add]` | Any node |
| `current_step` | `str` | Any node |
| `processing_complete` | `bool` | Final node |

---

### 1. Code Splitter

Two-phase design — deterministic systems first, LLM only for semantic reasoning.

**Phase 1 — tree-sitter (zero LLM cost, full file — no truncation)**

tree-sitter parses the complete source file regardless of size. Token budget is managed independently in Phase 2 via per-class 400-char snippets — there is no file-size limit on extraction.

| Extracted deterministically | How |
|-----------------------------|-----|
| Full source for every `class` / `interface` / `enum` / `@interface` | CST byte-range slice — no stubs possible |
| File-level import statements | `import_declaration` nodes |
| Annotations per class (`@Service`, `@Entity`, etc.) | `modifiers → annotation` nodes |
| Superclass (`extends`) | `superclass` node |
| Implemented interfaces | `super_interfaces` node |
| Field types | `field_declaration` nodes in class body |
| Method signatures (name, return type, parameters) | `method_declaration` nodes |
| Internal dependencies | Field types ∩ names of other declarations in the same file |
| **Layer label** | Annotation-to-layer map (`@Service`→service, `@Entity`→model, etc.); `extends Exception`→exception; enum→model |

**Layer assignment — fully deterministic, four-step priority:**

| Priority | Method | Example |
|----------|--------|---------|
| 1 | Spring/JPA annotation map | `@Service` → `service`, `@Entity` → `model` |
| 2 | Structural signals | `extends Exception` → `exception`, `enum` → `model` |
| 3 | Naming convention patterns (25 regexes) | `ChequeProcessor` → `service`, `UserRepository` → `repository`, `FraudException` → `exception` |
| 4 | Final fallback | → `utility` |

**Description generation — from structural metadata, no LLM:**

`_generate_description()` builds a concise description from method signatures and field types:
- `"Service providing: processChequeBatch, validateCheque, notifyFailure"`
- `"Repository providing: findByStatus, save, deleteById"`
- `"Data model with fields: accountNumber, chequeNumber, amount"`

This gives the Documenter enough signal to produce proper documentation without any LLM call in the Code Splitter.

**Output** — `modules[]`: each entry has `name`, `description`, `code`, `layer`, `dependencies`, `superclass`, `implements`, `annotations`, `methods`, `field_types`, `imports`

- **Deduplication** — first occurrence of each name is kept (source order preserved)
- **Zero LLM calls** — the entire agent is deterministic
- **Saves** — `output/modules/modules.json`, `output/modules/<ClassName>.java`

### 2. Documenter

- **Input** — `modules[]` — structured metadata per module, not truncated raw code
- **Payload per module** — `name`, `layer`, `description`, `annotations`, `superclass`, `implements`, `field_types`, `dependencies`, `methods` (formatted as `"ReturnType name(ParamType, ...)"` strings), `code_opening` (first 500 chars for class-level context)
- **Why structured payload** — method signatures convey the full API surface regardless of class size; a 3K char truncated snippet cuts off mid-method and misses logic in long classes
- **Output** — `documentation{}`: `overview`, `business_rules`, `data_models`, `service_interfaces`, `module_docs`, `technical_specs`
- **Retry mode** — when `audit_feedback` is set and `audit_retries > 0`, uses `SYSTEM_RETRY` with feedback injected
- **Saves** — `output/docs/documentation.json`

### 3. Auditor

- **Input** — `modules[]` + `documentation{}`
- **Output** — `audit_report{}` with `score` (0–100), `passed`, `issues[]`, `metrics{}`, `recommendations[]`, `evaluation_breakdown{}`
- **Scoring layers** — LLM content score (primary, drives retry) + deterministic structural checks + DeepEval semantic signals (both supplementary)
- **Pass threshold** — configurable via `AUDIT_PASS_THRESHOLD` (default 70)
- **Retry trigger** — if `score < threshold` and `audit_retries < MAX_AUDIT_RETRIES`, returns to Documenter with structured feedback including: missing sections, undocumented modules, shallow depth, hallucination warnings, clarity issues
- **LLM output validation (`_validate_llm_result`)** runs before the score drives any decision:

| Check | Repair applied |
|-------|---------------|
| Score out of 0–100 range | Clamped (`150` → `100`) |
| Score not a number | Derived from deterministic average as safe fallback |
| `metrics` not a dict | Reset; missing keys filled from deterministic scores |
| Metric values not numeric or out of range | Set to `50` |
| `issues` not a list | Reset to `[]` |
| Issue items not dicts or missing required fields | Filled with placeholder values |
| Invalid severity value | Clamped to `"minor"` |

- **Saves** — `output/audit/audit_report.json`

### 4. Review Gate (HITL)

- **Input** — `audit_report{}`
- **Mechanism** — calls `langgraph.interrupt()`, which checkpoints the graph state via `MemorySaver` and pauses execution
- **Resume** — `PipelineService.resume_job(job_id, decision)` injects `hitl_decision` and calls `graph.invoke()` to continue
- **Routing** — `"approve"` → Converter; `"reject"` → Documenter; neither → END
- **Sets** — `hitl_decision`, `awaiting_review`

### 5. Converter

- **Input** — `modules[]` + `documentation{}` + `build_feedback` (optional, on build retry)
- **Output** — `converted_modules[]`: each has `name`, `package`, `java_code`, `microservice_type`, `dependencies`, `file_path`
- **Conversion order** — model → exception → repository → service → controller → dto → config → utility
- **Limit** — first 15 modules per run (configurable via `_MAX_MODULES`)
- **Saves** — `output/converted/<ClassName>.java`, `output/converted/conversion_summary.json`

### 6. Tester

- **Input** — `converted_modules[]`
- **Output** — `test_suites[]`: each has `module_name`, `test_class_name`, `test_code`, `test_count`, `file_path`
- **Priority** — service / controller / repository modules tested first
- **Framework** — JUnit 5 + Mockito + AssertJ; Given-When-Then structure
- **Limit** — first 10 modules per run
- **Saves** — `output/tests/<ClassNameTest>.java`, `output/tests/test_suites_summary.json`

### 7. Joiner (Reassembly)

- **Input** — `converted_modules[]` + `test_suites[]`
- **Phase 1** — builds `DependencyGraph`, detects cycles, groups by microservice layer
- **Phase 2** — LLM generates `project_config` (pom.xml content, Dockerfile, application.yml, main class)
- **Phase 3** — `CodeStitcher` writes the full Maven project tree with correct package paths
- **Saves** — `output/assembled/` (full project tree), `output/assembled/assembly_manifest.json`, `output/assembled/dependency_graph.json`

### 8. Build Verifier

- **Input** — `assembly_result{}`
- **Verification order** — `mvn compile` (if Maven available) → `javac` (if JDK available) → LLM static analysis fallback
- **Output** — `build_report{}` with `status` (`success` / `failed` / `skipped`), `errors[]`, per-class diagnostics
- **Retry trigger** — if `status == "failed"` and `build_retries <= MAX_BUILD_RETRIES`, injects per-class errors into `build_feedback` and routes back to Converter
- **LLM output validation (`_validate_llm_static_result`)** runs when LLM fallback is used:

| Check | Repair applied |
|-------|---------------|
| `has_critical_issues` not a bool | Defaults to `True` — safe: assumes failure rather than silently passing bad code |
| `issues` not a list | Reset to `[]` |
| Issue items missing required fields (`class`, `severity`, `message`) | Filled with placeholders |
| `summary` missing or empty | Default message inserted |

- **Saves** — `output/build/build_report.json`

---

## Prompt Design

All LLM prompts are stored in `prompts/<agent>_prompts.py` and **never inlined** in agent code.

```
prompts/
├── code_splitter_prompts.py    →  REMOVED — Code Splitter is fully deterministic, no LLM
├── documenter_prompts.py       →  SYSTEM + SYSTEM_RETRY + USER_TEMPLATE
├── auditor_prompts.py          →  SYSTEM (uses {threshold} placeholder) + USER_TEMPLATE
├── converter_prompts.py        →  SYSTEM + USER_TEMPLATE
├── tester_prompts.py           →  SYSTEM + USER_TEMPLATE
├── joiner_prompts.py           →  SYSTEM + USER_TEMPLATE
└── build_verifier_prompts.py   →  SYSTEM + USER_TEMPLATE
```

`PromptHelper` is the only class that touches prompt modules:

```python
ph = PromptHelper("documenter")

# Fresh pass
result = ph.invoke_and_parse(modules_json=json.dumps(summaries))

# Retry pass — selects SYSTEM_RETRY, injects feedback
result = ph.invoke_and_parse(
    system_variant="retry",
    system_kwargs={"feedback": audit_feedback},
    modules_json=json.dumps(summaries),
)
```

To add a new agent, create `prompts/<name>_prompts.py` with `SYSTEM` and
`USER_TEMPLATE`, then `PromptHelper("<name>")` handles everything else.

---

## Observability

### Metrics (`observability/metrics.py`)

`MetricsCollector` records — per agent:

| Metric | How captured |
|--------|-------------|
| Duration (ms) | `start_agent()` / `end_agent()` called by `instrument_node` |
| LLM call count | `record_llm_call()` called inside `call_llm()` when `agent_name` is set |
| Tokens in / out | Estimated as `chars ÷ 4`; summed per agent and pipeline-total |
| Items processed | Count of modules / test-suites produced; set by `instrument_node` |
| Status | `success` / `partial` (produced output but had errors) / `failed` |

Saved to `output/observability/metrics.json`.

### Tracing (`observability/tracing.py`)

`PipelineTracer` records one **span** per agent execution:
- ISO-8601 start/end timestamps
- Duration in milliseconds
- Input and output summaries (first 300 chars)
- Status and metadata

Saved to `output/observability/traces.json` — Gantt-chart-ready (used by dashboard).

### Node instrumentation

The wrapper is applied **once** in `workflow.py`:

```python
wf.add_node("build_verifier", instrument_node("build_verifier", build_verifier_node))
```

Agent files contain no observability code.

### Logging

`setup_pipeline_logging()` registers two handlers on the `pipeline` logger:
- **File** — newline-delimited JSON (`output/logs/pipeline_<timestamp>.jsonl`)
- **Console** — plain text, WARNING level only (Rich handles INFO output)

---

## Reassembly

### DependencyGraph

Builds a directed graph from the `converted_modules` list:

```
model (User)
  └── repository (UserRepository)
        └── service (UserService)
              └── controller (UserController)
```

Key operations:

| Method | Algorithm | Output |
|--------|-----------|--------|
| `topological_sort()` | DFS post-order | Build order with deepest deps first |
| `detect_cycles()` | DFS with path tracking | List of cyclic paths |
| `microservice_groups()` | Layer → group map | `domain / data / service / api / shared` |
| `most_depended_on()` | Sort by reverse-edge count | Top-N shared modules |

### CodeStitcher

Writes a complete Maven project tree to `output/assembled/`:

```
output/assembled/
├── pom.xml                           Spring Boot 3.x parent, all starters
├── Dockerfile                        Multi-stage: jdk-alpine builder → jre-alpine runtime
├── src/
│   ├── main/
│   │   ├── java/<group_path>/        One .java per converted module
│   │   └── resources/
│   │       └── application.yml      H2 datasource, server port, springdoc
│   └── test/
│       └── java/<group_path>/        One *Test.java per test suite
├── assembly_manifest.json
└── dependency_graph.json
```

File placement is derived from the module's `package` field:
`com.bank.cheque.service` → `src/main/java/com/bank/cheque/service/<Name>.java`

---

## Evaluation

Every LLM call in the pipeline has evaluation coverage. There are three distinct
layers of evaluation, applied at different points.

---

### Layer 1 — LLM Output Validation (structural repair, runs immediately after every LLM call)

Before any LLM response is trusted, a validator repairs malformed output so
it can never corrupt a downstream decision.

| Agent | Validator | What is checked and repaired |
|-------|-----------|------------------------------|
| **Code Splitter** | `_validate_enrichments` | Dropped modules → defaults inserted; invalid layer values → clamped to `utility`; description is just the class name → replaced; hallucinated extras → ignored |
| **Auditor** | `_validate_llm_result` | Score out of 0–100 → clamped; score not numeric → derived from deterministic avg; `metrics` not a dict → repaired; missing metric keys → filled from deterministic scores; `issues` not a list → reset; issue items missing required fields → placeholder-filled; invalid severity → clamped to `"minor"` |
| **Build Verifier** *(LLM fallback)* | `_validate_llm_static_result` | `has_critical_issues` not bool → defaults `True` (safe: assumes failure); `issues` not a list → reset; issue items missing fields → filled; empty summary → default message |

---

### Layer 2 — Agent Output Quality Evaluation (runs after generation, scores the output)

Each agent's LLM output is evaluated for quality. Results are stored in state,
saved to disk, and displayed in the dashboard. Self-healing is triggered where
critical failures are detected.

| Agent | Evaluator | Dimensions | Self-healing |
|-------|-----------|-----------|-------------|
| **Code Splitter** | `_validate_enrichments` | Coverage of all modules, layer validity, description quality | Repairs inline before merge |
| **Documenter** | **Auditor agent** — 3-layer evaluation: | | |
| | ↳ LLM scoring (primary) | Completeness · accuracy · clarity · coverage | Retry loop with targeted feedback |
| | ↳ `evaluation/deterministic.py` | Schema completeness · module coverage · business logic depth | Feeds into retry feedback |
| | ↳ `evaluation/deepeval_metrics.py` | Summarization · faithfulness · clarity | Feeds into retry feedback |
| **Converter** | `evaluation/converter_checks.py` | Spring annotations match layer · package declarations · Spring imports · no stubs | No retry — results in state + dashboard |
| **Tester** | `evaluation/tester_checks.py` | `@Test` present · assertions present · module coverage ratio · Mockito usage | Yes — within-node retry for suites with no `@Test` or no assertions |
| **Joiner** | `evaluation/joiner_checks.py` | `pom.xml` validity · Dockerfile multi-stage · `application.yml` config · manifest completeness | No retry — results in state + dashboard |

---

### Layer 3 — Self-healing Feedback Loops

When quality evaluation fails, structured feedback is injected back into the
next LLM call rather than just surfacing an error.

**Audit retry loop (Documenter ↔ Auditor)**

`_build_feedback()` composes a targeted message combining all three evaluation layers:

```
• LLM issues    — critical + major issues with module + suggestion
• Schema        — exact missing documentation section names
• Coverage      — names of every undocumented module
• Depth         — names of modules with < 20 words of business logic
• Faithfulness  — hallucination rate + DeepEval reason string
• Clarity       — clarity score + DeepEval reason string
```

Injected into `SYSTEM_RETRY` prompt so the Documenter fixes only the identified gaps.

**Build self-healing loop (Converter ↔ Build Verifier)**

Per-class compiler errors from `mvn compile` / `javac` are injected into
`build_feedback`. Converter re-converts only the failing classes.

**Tester within-node retry**

If `tester_checks.needs_retry()` flags a suite (no `@Test` or no assertions),
the suite is regenerated immediately with an explicit instruction requiring
assertions. Evaluation re-runs after the retry.

---

### Offline Evaluation (`evaluation/scorer.py`)

The `evaluation/` package can also be run offline against any saved
`documentation.json` artefact, independent of the pipeline:

```python
from evaluation.deterministic import run_all as det_run
from evaluation.deepeval_metrics import run_all as llm_run
from evaluation.scorer import compute

det_result = det_run(documentation, modules)
llm_result = llm_run(documentation, source_code)
score = compute(det_result, llm_result)
# score["final_score"]  → 0–100
```

| Layer | Weight | Dimensions |
|-------|--------|-----------|
| Deterministic | 20 % | schema (5 %), coverage (10 %), depth (5 %) |
| DeepEval | 80 % | summarization (35 %), faithfulness (30 %), clarity (15 %) |

DeepEval dimensions are weighted higher because structural checks (key presence,
word count) are weak proxies for actual documentation quality.

---

## REST API

Run the FastAPI server:

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive docs: `http://localhost:8000/docs`

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check |
| `POST` | `/api/v1/convert` | Upload `.java` file; returns `job_id` immediately |
| `GET` | `/api/v1/jobs` | List all jobs with status |
| `GET` | `/api/v1/jobs/{id}` | Full job detail, including `awaiting_review` flag and HITL URLs |
| `GET` | `/api/v1/jobs/{id}/results/{artifact}` | Fetch a pipeline artefact as JSON |
| `GET` | `/api/v1/jobs/{id}/download` | Download assembled Maven project as ZIP |
| `POST` | `/api/v1/jobs/{id}/approve` | HITL: approve audit report → pipeline proceeds to conversion |
| `POST` | `/api/v1/jobs/{id}/reject` | HITL: reject audit report → pipeline loops back to Documenter |

### Available artifact names

| Name | Content |
|------|---------|
| `modules` | Identified legacy modules |
| `documentation` | Business rules & technical specs |
| `audit` | Documentation quality report |
| `conversion` | Converted Spring Boot modules summary |
| `tests` | Generated JUnit 5 test suites summary |
| `assembly` | Full Maven project manifest |
| `build` | Compilation verification report |
| `metrics` | Per-agent timing & token usage |
| `traces` | Execution spans (Gantt-ready) |

### Typical workflow

```bash
# 1. Submit a job
curl -X POST http://localhost:8000/api/v1/convert \
  -F "file=@DemoApplication.java"
# → { "job_id": "abc12345-...", "status": "queued" }

# 2. Poll until awaiting_review
curl http://localhost:8000/api/v1/jobs/abc12345-...
# → { "status": "awaiting_review", "approve_url": "/api/v1/jobs/abc12345-.../approve", ... }

# 3. Review the audit report
curl http://localhost:8000/api/v1/jobs/abc12345-.../results/audit

# 4. Approve (or reject)
curl -X POST http://localhost:8000/api/v1/jobs/abc12345-.../approve

# 5. Poll until complete
curl http://localhost:8000/api/v1/jobs/abc12345-...
# → { "status": "complete", "build_status": "success", ... }

# 6. Download the Maven project
curl -O http://localhost:8000/api/v1/jobs/abc12345-.../download
```

---

## Dashboard

Run independently or launched via `--dashboard` flag.

```bash
streamlit run dashboard/app.py
```

| Page | Content |
|------|---------|
| **Overview** | Pipeline stage status, KPI metrics, modules-by-layer pie, audit metrics bar |
| **Code Modules** | Filterable module list with code viewer, dependencies, layer badge |
| **Documentation** | Tabbed view: overview, business rules, data models, service interfaces, module docs |
| **Audit Report** | Score gauge, pass/fail status, issue severity bar chart, metrics, recommendations |
| **Converted Code** | Type-distribution bar chart, per-module Spring Boot code viewer |
| **Test Suites** | Test suite list with JUnit 5 code viewer |
| **Dependency Graph** | Microservice group cards, topological build order, cycle warnings, most-depended-on chart, assembly manifest |
| **Observability** | Pipeline KPIs, per-agent metrics table, token usage chart, time-spent pie, Gantt execution timeline, span detail table |

---

## Setup & Usage

### 1. Prerequisites

- Python 3.11+
- Azure OpenAI resource with a GPT-4o deployment
- (Optional) JDK 17+ and Maven 3.x for real compilation in Build Verifier

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-4o

MAX_AUDIT_RETRIES=2
AUDIT_PASS_THRESHOLD=70.0
MAX_BUILD_RETRIES=1
BUILD_TIMEOUT_SECS=120
OUTPUT_DIR=output
```

The API key is read from the **terminal environment variable** `AZURE_OPENAI_KEY_GPT4o`
and is never stored in `.env` or source code:

```powershell
# PowerShell
$env:AZURE_OPENAI_KEY_GPT4o = "<your-key>"
```

```bash
# Bash / zsh
export AZURE_OPENAI_KEY_GPT4o="<your-key>"
```

### 4a. Run via CLI

```bash
# Basic run
python main.py DemoApplication.java

# Run and launch Streamlit dashboard automatically
python main.py DemoApplication.java --dashboard

# Custom output directory, 3 audit retries
python main.py DemoApplication.java --output-dir results --max-retries 3
```

> The CLI pipeline pauses at the Review Gate and waits for terminal input to
> approve or reject.

### 4b. Run via REST API

```bash
uvicorn app.main:app --reload --port 8000
```

Then follow the [REST API workflow](#typical-workflow) above.

### 5. Launch the dashboard manually

```bash
streamlit run dashboard/app.py
# Open http://localhost:8501
```

---

## Output Artefacts

After a successful run, `output/` contains:

```
output/
├── modules/
│   ├── modules.json               All identified modules with metadata
│   └── <ClassName>.java           Raw extracted source per module
│
├── docs/
│   └── documentation.json         Business rules, data models, service interfaces
│
├── audit/
│   └── audit_report.json          Score, issues, metrics, recommendations
│
├── converted/
│   ├── conversion_summary.json    Summary of all converted modules
│   └── <ClassName>.java           Modern Spring Boot source per module
│
├── tests/
│   ├── test_suites_summary.json   Summary of all test suites
│   └── <ClassNameTest>.java       JUnit 5 test class per module
│
├── assembled/                     Compilable Maven project
│   ├── pom.xml
│   ├── Dockerfile
│   ├── src/main/java/...
│   ├── src/main/resources/application.yml
│   ├── src/test/java/...
│   ├── assembly_manifest.json     File inventory
│   └── dependency_graph.json      Full dep graph with build order
│
├── build/
│   └── build_report.json          Compilation status + per-class error details
│
├── observability/
│   ├── metrics.json               Per-agent and pipeline-level metrics
│   └── traces.json                Span-level execution trace
│
└── logs/
    └── pipeline_<timestamp>.jsonl  Structured JSONL log
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `langgraph` | ≥ 0.2.0 | Multi-agent orchestration (StateGraph, interrupt, MemorySaver) |
| `langchain` | ≥ 0.3.0 | LangChain core framework |
| `langchain-openai` | ≥ 0.2.0 | `AzureChatOpenAI` integration |
| `langchain-core` | ≥ 0.3.0 | Message types, runnable interface |
| `openai` | ≥ 1.50.0 | Azure OpenAI REST client |
| `fastapi` | ≥ 0.115.0 | REST API framework |
| `uvicorn` | ≥ 0.30.0 | ASGI server for FastAPI |
| `streamlit` | ≥ 1.39.0 | Interactive dashboard |
| `plotly` | ≥ 5.24.0 | Gauge, bar, pie, Gantt charts in dashboard |
| `pandas` | ≥ 2.2.0 | DataFrame support for dashboard tables |
| `python-dotenv` | ≥ 1.0.0 | `.env` file loading |
| `pydantic` | ≥ 2.9.0 | Data validation (also used by FastAPI) |
| `rich` | ≥ 13.8.0 | Coloured console output and tables |
| `tiktoken` | ≥ 0.8.0 | Token estimation utilities |
| `tree-sitter` | ≥ 0.23.0 | Concrete syntax tree parser — deterministic extraction of declarations, imports, annotations, relationships, signatures, and dependencies in Code Splitter |
| `tree-sitter-java` | ≥ 0.23.0 | Java grammar for tree-sitter |
| `deepeval` | ≥ 1.0.0 | LLM-based evaluation metrics (summarization, faithfulness, clarity) |

---

## Configuration Reference

All values are read from `.env` (or environment variables) in `config.py`.

| Variable | Default | Description |
|----------|---------|-------------|
| `AZURE_OPENAI_ENDPOINT` | *(required)* | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_KEY_GPT4o` | *(required, terminal env only)* | Azure OpenAI API key — never stored in `.env` |
| `AZURE_OPENAI_API_VERSION` | `2025-01-01-preview` | API version |
| `AZURE_OPENAI_DEPLOYMENT` | *(required)* | Deployment / model name (e.g. `gpt-4o`) |
| `MAX_AUDIT_RETRIES` | `2` | Maximum Documenter retry attempts before proceeding to Review Gate |
| `AUDIT_PASS_THRESHOLD` | `70.0` | Minimum audit score (0–100) to proceed without auto-retry |
| `MAX_BUILD_RETRIES` | `1` | Maximum Converter retry attempts triggered by Build Verifier failures |
| `BUILD_TIMEOUT_SECS` | `120` | Timeout in seconds for `mvn compile` / `javac` subprocess calls |
| `OUTPUT_DIR` | `output` | Root directory for all generated artefacts |

CLI flags (`--output-dir`, `--max-retries`) override the corresponding env vars at runtime.
