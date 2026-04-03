# Architecture Guide

## Purpose

This project has three major responsibilities:

1. Fetch and catalog chapter PDFs from Canvas
2. Generate and backfill derived tutoring artifacts from saved model output
3. Build a deployable tutoring site and challenge-exam application from saved artifacts

For operator-facing command sequences and recovery workflows, see [OPERATIONS.md](/home/nshah/projects/math-tutor/math_tutor/docs/OPERATIONS.md).

The long-term goal is to keep these responsibilities separate so each one can
be tested, operated, and evolved independently.

## Current Module Boundaries

### `cli.py`

Primary operator entry point for:

- top-level operator argument parsing
- orchestration across Canvas, prompt generation, state, and site-building modules
- selective prompt execution

Key contract:

- Inputs: Canvas credentials, prompt selection, output directory
- Outputs: downloaded PDFs, response `.md/.html/.pdf`, metadata JSON, state JSON
- Side effects: delegates network access, filesystem writes, and API calls to dedicated modules

### `canvas_course.py`

Canvas-facing integration module for:

- Canvas and OneLogin browser authentication
- authenticated `httpx` client creation from Playwright session cookies
- class-note and assignment PDF discovery
- fetched-PDF download and fetch-state persistence

Key contract:

- Inputs: authenticated browser context, course URL, file-match rules, fetch-state objects
- Outputs: discovered `CanvasFile` records and downloaded PDFs
- Side effects: Canvas network access and filesystem writes

### `canvas_files.py`

Pure Canvas file metadata, matching, and fetch-summary helpers.

Key contract:

- Inputs: Canvas filenames, URLs, content types, and fetched-state data
- Outputs: normalized `CanvasFile` values plus pure matching/parsing decisions and operator fetch summaries
- Side effects: operator-facing summary prints only

### `canvas_login.py`

Canvas and OneLogin browser authentication helpers.

Key contract:

- Inputs: Playwright page instances, login URLs, Canvas course URLs, and operator credentials
- Outputs: authenticated browser sessions positioned on the target course page
- Side effects: browser interaction only

### `cli.py` also coordinates:

- selective prompt execution
- response generation and artifact writing

Supporting state/path/prompt logic now lives in smaller modules so `cli.py`
can increasingly act as the operator wiring layer instead of the source of
truth for every behavior.

### `cli_auth.py`

Authentication input helpers for the operator CLI.

Key contract:

- Inputs: CLI username/password flags, `skip-fetch`, and the operator environment
- Outputs: resolved Canvas credentials or `None` when fetch is intentionally skipped
- Side effects: none

### `cli_commands.py`

High-level command orchestration for the operator CLI.

Key contract:

- Inputs: normalized command context, selected workflow mode, and optional Canvas credentials
- Outputs: processed file-id sets and optional guided-learning site build paths
- Side effects: delegates fetch, generation, printing, and site-building to dedicated modules

### `cli_context.py`

Command-context assembly for the operator CLI.

Key contract:

- Inputs: parsed CLI arguments, output root, and logging callback
- Outputs: fully assembled `CliCommandContext` with normalized state, selected prompts, output layout, and provider clients
- Side effects: output-directory creation plus state-file reads

### `env_config.py`

Shared environment-loading helpers.

Key contract:

- Inputs: optional `.env` file path
- Outputs: current process environment populated with missing values from that file
- Side effects: environment-variable mutation only

### `site_data.py`

Record and prompt-output loading for site generation.

Key contract:

- Inputs: saved fetch state, generated-output state, and response artifact paths under an output root
- Outputs: normalized `DocumentRecord` and `PromptOutputRecord` values used by the site builders
- Side effects: filesystem reads only

### `cli_runtime.py`

Pure runtime helpers for the operator CLI.

Key contract:

- Inputs: output roots, saved fetch-state data, selected prompt specs, and chapter filters
- Outputs: normalized output-layout paths, filtered saved `CanvasFile` lists, and generation/browser requirement decisions
- Side effects: optional directory creation only

### `cli_generation.py`

Generation-client bootstrap helpers for the operator CLI.

Key contract:

- Inputs: selected prompt specs, generation mode flags, and provider API keys from the environment
- Outputs: provider client instances and validated API-key requirements for the selected prompt set
- Side effects: optional provider SDK imports and operator-facing warning logs only

### `cli_workflows.py`

Reusable workflow helpers for repeated CLI processing loops.

Key contract:

- Inputs: discovered or saved `CanvasFile` lists plus a shared file-processing context
- Outputs: processed file-id sets for the current workflow slice
- Side effects: delegates generation/fetch work to `prompt_pipeline.process_file`

### `challenge_builder.py`

Builds challenge exam banks from saved response artifacts.

Key contract:

- Inputs: saved response files under `output/responses/`
- Outputs: challenge exam JSON catalogs, deploy challenge assets, generated `config.php`
- Side effects: filesystem writes only

### `site_builder.py`

Builds the tutoring site and chapter pages from saved artifacts.

Key contract:

- Inputs: saved downloads, response files, metadata, state JSON
- Outputs: HTML site under `output/site/` or deploy tree
- Side effects: filesystem writes only

### `mcq_generator.py`

Creates MCQ option files from already-generated mental math and olympiad source markdown.

Key contract:

- Inputs: saved source `.md` question files
- Outputs: `*-mcq.md/.html/.pdf`
- Side effects: API calls and filesystem writes

### `backfill_response_html.py`

Recreates missing HTML response artifacts from saved markdown without new model calls.

Key contract:

- Inputs: saved `.md` outputs and saved state
- Outputs: missing `.html` artifacts and normalized state
- Side effects: filesystem writes only

### `chaptering.py`

Pure utility module that defines the canonical chapter parsing and chapter slug rules.

Key contract:

- Inputs: filenames, stems, display names, chapter labels
- Outputs: normalized chapter labels, slugs, sort keys
- Side effects: none

### `prompt_catalog.py`

Pure prompt-definition and prompt-selection module.

Key contract:

- Inputs: selected prompt slugs
- Outputs: canonical `PromptSpec` objects, print slugs, prompt titles, dependent prompt expansion
- Side effects: none

### `prompt_generation.py`

Low-level provider request helpers for prompt generation.

Key contract:

- Inputs: provider clients, prompt specs, model names, source prompt output, and optional PDF input paths
- Outputs: normalized `PromptResponseResult` values
- Side effects: provider API calls only

### `prompt_saved_outputs.py`

Saved-output reuse, skip, and print helpers for prompt artifacts.

Key contract:

- Inputs: saved output roots or generated artifact paths plus prompt metadata
- Outputs: skip decisions and printer-target dispatch for saved PDFs
- Side effects: filesystem reads and optional printer invocation only

### `prompt_pipeline.py`

Prompt execution and saved-output orchestration.

Key contract:

- Inputs: downloaded PDF paths, selected `PromptSpec` objects, saved state, model clients
- Outputs: generated response `.md/.html/.pdf`, metadata JSON, updated generated-output state
- Side effects: API calls, filesystem writes, and optional printer invocation for saved PDFs

### `response_artifacts.py`

Shared response rendering and artifact-formatting helpers.

Key contract:

- Inputs: markdown text, source PDF references, prompt metadata, output artifact paths
- Outputs: rendered response HTML, rendered response PDFs, normalized document titles/slugs
- Side effects: PDF rendering writes only

### `video_recommendations.py`

YouTube recommendation validation and markdown rendering helpers.

Key contract:

- Inputs: Gemini JSON output or raw YouTube URLs
- Outputs: validated video recommendation structures and rendered markdown blocks
- Side effects: optional oEmbed validation HTTP requests only

### `generated_metadata.py`

Provider-neutral metadata helpers for generated tutoring artifacts.

Key contract:

- Inputs: prompt metadata payloads, Canvas file details, prompt specs, and model identifiers
- Outputs: normalized metadata dictionaries and provider-neutral metadata payloads for saved artifacts
- Side effects: none

### `site_content.py`

Study-guide summary extraction and guided-learning prompt helpers for chapter pages.

Key contract:

- Inputs: `DocumentRecord` values and saved study-guide HTML/markdown content
- Outputs: normalized summary text/HTML and guided-learning prompt text
- Side effects: filesystem reads only

### `site_sections.py`

Reusable HTML section renderers for shared page fragments.

Key contract:

- Inputs: normalized section data such as headings, links, prompt text, and page href builders
- Outputs: stable HTML fragments for headers, guided-learning cards, and overview cards
- Side effects: none

### `site_shell.py`

Shared page shell rendering for generated tutoring pages.

Key contract:

- Inputs: normalized page body HTML, page metadata, document records, and href builders
- Outputs: complete HTML documents with shared CSS, MathJax bootstrapping, and page layout
- Side effects: none

### `site_theme.py`

Shared CSS and helper scripts for generated site pages.

Key contract:

- Inputs: none beyond the generated shell including the constants
- Outputs: stable CSS and shared in-page helper JavaScript for copy-button behavior
- Side effects: none

### `site_navigation.py`

Sidebar and navigation rendering for generated site pages.

Key contract:

- Inputs: document records, active page state, deployment base path, and page-href builder
- Outputs: stable sidebar HTML fragments for library and non-library pages
- Side effects: none

### `site_assets.py`

Site output path and href resolution helpers.

Key contract:

- Inputs: source artifact paths, site/output directories, and deployment base-path settings
- Outputs: copied asset paths and browser hrefs suitable for generated site pages
- Side effects: may copy generated assets into the deploy tree

### `state_store.py`

Saved-state loading and normalization for fetch and generated-output tracking.

Key contract:

- Inputs: `fetch_state.json`, `generated_output_state.json`
- Outputs: normalized in-memory state objects
- Side effects: filesystem reads/writes only

Note: `generated_output_state.json` is the only supported filename for generated-output state.

### `site_models.py`

Shared data models for site-generation flows.

Key contract:

- Inputs: record and prompt-output fields gathered during site generation
- Outputs: stable dataclass structures used by the builder and rendering helpers
- Side effects: none

### `site_cards.py`

Reusable rendering and assignment-selection helpers for chapter/document pages.

Key contract:

- Inputs: document records, prompt outputs, assignment files, and path builders
- Outputs: HTML fragments for reusable site cards
- Side effects: assignment card rendering may copy assignment PDFs into the target site tree

### `site_challenges.py`

Chapter-specific challenge-card loading and rendering for document pages.

Key contract:

- Inputs: document records, deployment base path, page-href builder, and generated chapter exam JSON
- Outputs: stable HTML fragments for the chapter challenge card plus chapter exam index lookups
- Side effects: filesystem reads only from generated chapter challenge catalogs

### `site_records.py`

Reusable record-page rendering for document pages.

Key contract:

- Inputs: document records, prompt outputs, assignment files, site/output paths, and href builders
- Outputs: stable HTML fragments for chapter overview cards, guided learning sections, and full record pages
- Side effects: filesystem reads only

### `site_prompt_cards.py`

Prompt-card ordering and rendering for generated chapter pages.

Key contract:

- Inputs: document records, prompt outputs, assignment files, and site/output paths
- Outputs: stable HTML fragments for ordered prompt cards and prompt output fallbacks
- Side effects: assignment-card rendering may copy assignment PDFs into the target site tree

## Data Contracts

### Saved input artifacts

- `output/responses/*.md` are the expensive model-generated source artifacts
- `output/downloads/` can be re-fetched if needed
- `output/generated_output_state.json` is reconstructable but useful operational state

### Derived artifacts

- HTML/PDF response files are derivable from saved markdown
- challenge exam JSON catalogs are derivable from saved markdown and MCQ files
- deploy site output is derivable from saved artifacts plus source code

## Hardening Strategy

The project should evolve by:

1. moving pure logic into small modules
2. locking behavior with unit tests
3. documenting module contracts before large refactors
4. avoiding changes that rewrite expensive saved artifacts unless explicitly intended
