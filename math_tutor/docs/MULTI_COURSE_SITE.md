# Multi-Course Site Plan

## Status

Approved for implementation on 2026-09-19: Phase 1 and Phase 2 only.

This document is the durable checkpoint for continuing the work in a future session.

## Goal

Reorganize Math Delight into a course-aware site. The initial portal offers:

- Algebra II / Trigonometry, containing all existing site content
- AP Calculus AB, present as an empty course with no units, documents, assignments, or challenges yet

## Approved Compatibility Decision

The user explicitly approved breaking existing site URLs and command-line syntax when that produces a simpler final design. This approval does not permit loss or corruption of source PDFs, generated responses, metadata, saved state, question banks, exam results, credentials, or other preserved data.

## Phase 1: Course Foundation

- Introduce an immutable course definition and a validated course registry.
- Use stable course IDs: `algebra-2-trig` and `ap-calculus-ab`.
- Require course identity in site-generation code instead of relying on a hidden default.
- Keep existing Algebra source artifacts in place for this iteration; do not migrate, regenerate, or delete them.
- Represent AP Calculus AB without borrowing or copying Algebra records.

## Phase 2: Site Navigation

Generate this structure:

```text
site/
├── index.html
└── courses/
    ├── algebra-2-trig/
    │   ├── index.html
    │   ├── library.html
    │   ├── live-tutor.html
    │   ├── privacy-policy.html
    │   ├── doc-<file-id>.html
    │   └── challenges/
    └── ap-calculus-ab/
        └── index.html
```

- The root page is a course selector.
- Algebra II / Trigonometry remains fully functional inside its course directory.
- AP Calculus AB has a deliberate empty-state course page and no fabricated learning content.
- Course pages display the current course and provide a clear `Switch Course` path.
- Course-owned links remain inside the selected course.
- The empty Calculus course does not build Algebra challenges or copy Algebra artifacts.

## Deferred Work

- Canvas configuration and fetching for AP Calculus AB
- Course-specific output and state storage
- Artifact migration
- Course-aware generation CLI commands
- Calculus prompt design
- Calculus units, documents, assignments, question banks, and assessments
- Course-aware challenge database changes
- Deployment and removal of legacy generated pages

## Acceptance Criteria

1. A full site build writes the root course selector and both course directories.
2. The selector links to both course home pages.
3. The Algebra course contains the existing library, document, live-tutor, privacy, and challenge experiences.
4. All generated Algebra navigation uses the Algebra course path and offers `Switch Course`.
5. The Calculus course page identifies AP Calculus AB and clearly states that course content is not yet available.
6. The Calculus directory contains no Algebra document pages or challenge application.
7. Existing source artifacts are neither moved nor deleted.
8. Build output is deterministic apart from existing generated timestamps.
9. Relevant behavior is developed with observed red/green/refactor TDD.
10. No network access, Canvas fetch, model call, deployment, database migration, or destructive cleanup occurs in these phases.

## Recovery and Rollback

The implementation changes the generated destination layout but not the source artifacts. Rollback consists of checking out the prior generator code and rebuilding into a fresh staging directory. Existing generated deployment output must not be deleted during development.

## Phase 3: AP Calculus AB Chapter 2 Fetch

Approved for implementation on 2026-09-19.

### Scope

- Treat the school Canvas course and its filenames as the curriculum authority; do not impose College Board unit numbering.
- Reuse the existing Canvas, OneLogin, Playwright, authenticated-cookie, Modules-page, and atomic-download implementation.
- Register Canvas course `4446` for `ap-calculus-ab`.
- Match the school document pattern represented by `Chapter 2 Notetakers.pdf`.
- Fetch Chapter 2 only into an isolated Calculus output tree.
- Preserve original Canvas file identity, display name, download URL, and fetch timestamp.
- Prove a repeated fetch is idempotent.

### Credential Contract

- Load `MATH_TUTOR_USERNAME` and `MATH_TUTOR_PASSWORD` from the existing untracked `.env` file, including `export KEY=value` syntax.
- Never commit, log, or otherwise expose credential values.
- Explicit command-line credentials may override environment values for temporary operator use.
- Stop with a clear configuration error when either required value is absent.

### Calculus Output

```text
math_tutor/output/courses/ap-calculus-ab/
├── downloads/
├── responses/
├── metadata/
├── fetch_state.json
└── generated_output_state.json
```

This increment writes only the fetched PDF and fetch state. It does not generate model responses.

### Exclusions

- No OpenAI or Gemini calls
- No site population or deployment
- No chapters other than Chapter 2
- No Algebra migration or artifact changes
- No Calculus prompt, question-bank, challenge, or database work

### Execution Checkpoint

Completed and verified on 2026-09-19:

- Canvas file ID: `4839635`
- Display name: `Chapter 2 Notetakers.pdf`
- Local path: `math_tutor/output/courses/ap-calculus-ab/downloads/4839635_chapter-2-notetakers.pdf`
- Size: `2,070,159` bytes
- SHA-256: `99a4dd7b02e0934b96e05bc25700ad9337825342930536f8a490f5511dcce874`
- The file has a valid `%PDF-` signature and its recorded source belongs to Canvas course `4446`.
- `responses/` and `metadata/` remain empty; no model generation occurred.
- A second identical fetch used the saved state and cached PDF without logging into Canvas or downloading again.
- Full project validation passed with 235 tests, compilation checks, and `git diff --check`.

## Phase 4: Publish AP Calculus AB Chapter 2

Approved, implemented, deployed, and user-verified on 2026-09-19.

### Published Experience

- The site builder reads Calculus records only from `math_tutor/output/courses/ap-calculus-ab/`.
- The course selector marks AP Calculus AB as ready when saved course content exists.
- The Calculus home and library list `Chapter 2 Notetakers`.
- `doc-4839635.html` links to the original school PDF and clearly identifies generated study guides and practice as unavailable.
- Live Tutor, challenges, assignments, and Algebra artifacts are not exposed in Calculus.
- The source PDF is copied to `courses/ap-calculus-ab/downloads/` with the same SHA-256 checksum as the fetched file.

### Verification

- Red/green/refactor TDD completed for course isolation, feature-aware navigation, source-only presentation, and PDF deployment.
- Full project validation passed with 238 tests, compilation checks, and `git diff --check`.
- A production-shaped `/tmp` build contained only the five intended Calculus files: home, library, chapter page, privacy policy, and PDF.
- The watched deployment tree was rebuilt at `math_tutor/output/deploy/math_tutor/site/` with base path `/site/`.
- The user verified the deployed Chapter 2 experience on `mathdelight.com`.
