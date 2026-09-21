# Multi-Course Site Plan

## Status

Phases 1 through 5 are completed. Phase 6A and the Phase 6B study-guide pilot were
approved on 2026-09-19. Later Calculus prompt families remain unapproved.

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
- At the time of this phase, the watched deployment tree used
  `math_tutor/output/deploy/math_tutor/site/` with base path `/site/`; Phase 7 later superseded
  that layout with the canonical domain-root deployment.
- The user verified the deployed Chapter 2 experience on `mathdelight.com`.

## Phase 5: Chapter 2 Cengage Textbook Navigation

Approved for an authenticated feasibility spike only on 2026-09-19. Site implementation,
deployment, and publication remain subject to a separate approval after the spike reports
its findings.

### Goal

Make the AP Calculus AB Chapter 2 page a convenient starting point for the course's
online Cengage textbook. Prefer verified section-level links that keep protected textbook
content on Cengage and let Cengage enforce each student's entitlement.

Supplied reader URL:

```text
https://ng.cengage.com/static/nb/ui/evo/index.html?snapshotId=1529049&id=677758950&eISBN=9780357049105
```

### Approved Feasibility Spike

- Reuse the existing Canvas/OneLogin credentials and authenticated browser flow without
  requiring interactive user input when the existing login remains sufficient.
- Use an ephemeral Playwright browser context; do not persist browser storage unless a
  later plan explicitly requires and receives approval for it.
- Inspect the Calculus Canvas Modules area for the authorized Cengage/MindTap launch path.
- Open the authenticated reader and identify Chapter 2's title, ordered section structure,
  and navigation identifiers without publishing or logging protected chapter text.
- Test whether section destinations remain usable in a fresh authenticated context.
- Determine whether access is a direct Cengage login, a Canvas LTI launch, or a
  session-bound route.
- Report feasibility and recommend the smallest safe site integration before writing tests
  or implementation code.

### Safety and Rights Boundaries

- Never log, commit, deploy, or expose credentials, cookies, session tokens, signed launch
  parameters, or other authentication material.
- Do not mirror, scrape for republication, or deploy protected textbook pages, prose,
  illustrations, exercises, or DRM-controlled assets without documented permission.
- Navigation metadata may include chapter/section titles, ordering, stable publisher URLs,
  and non-secret publisher identifiers when verified safe.
- If usable navigation requires session-bearing URLs or copied protected content, stop and
  report the limitation rather than attempting to bypass Cengage access controls.

### Approved Integration

- Store validated, non-secret Chapter 2 navigation metadata in the source-controlled
  `site_textbook.py` module so clean builds remain deterministic.
- Render a clearly labeled `Chapter 2 Textbook` section on
  `courses/ap-calculus-ab/doc-4839635.html`.
- Open textbook destinations on Cengage, where each student authenticates with their own
  entitlement.
- Keep Algebra and other Calculus chapters unchanged.
- Validate publisher hosts and reject URLs containing credentials, tokens, or session data.

### Planned TDD Sequence

1. Red/green/refactor for textbook-manifest validation and unsafe-URL rejection.
2. Red/green/refactor for Calculus course and Chapter 2 isolation.
3. Red/green/refactor for ordered textbook navigation on the Chapter 2 page.
4. Red/green/refactor for safe missing or invalid metadata behavior.
5. Regression validation for the existing Algebra and Calculus experiences.
6. Build into `/tmp`, inspect emitted URLs and files, and only then request deployment
   approval.

### Acceptance Criteria

1. The Chapter 2 page distinguishes the school class note from the publisher textbook.
2. Verified textbook sections appear in the correct order when stable safe destinations
   exist.
3. Cengage continues to enforce student authentication and entitlement.
4. No protected textbook body content or authentication material is emitted into the site,
   logs, source control, or saved metadata.
5. Missing or invalid navigation metadata fails safely and explicitly.
6. No textbook resource appears in Algebra or an unrelated Calculus chapter.
7. Existing tests and the production-shaped staging build remain green.

### Recovery and Rollback

The feasibility spike is read-only and uses an ephemeral browser context. A future
implementation would add only isolated navigation metadata and generated-page rendering;
rollback would remove that metadata/rendering and rebuild the site. The saved Chapter 2
class note and all existing course artifacts remain untouched.

### Current Spike Status

- An unauthenticated request reached the MindTap reader shell but exposed no chapter
  structure, confirming that authenticated inspection is required.
- The first authenticated Playwright attempt stopped before login because Chromium could
  not start inside the filesystem/process sandbox (`Operation not permitted`). The approved
  rerun outside that sandbox started successfully.
- The existing Canvas/OneLogin flow authenticated successfully to Canvas course `4446`.
- Neither the rendered Calculus Modules page nor its authenticated Modules API metadata
  contains a Cengage/MindTap external URL or external-tool launch item.
- Opening the supplied reader URL inside the authenticated Canvas browser redirected to
  `/static/nb/logout.html`. Cengage states that MindTap must be restarted from Cengage login
  or the learning-management system; Canvas authentication alone does not establish the
  required Cengage entitlement session.
- Cengage exposes a first-party two-step login at `account.cengage.com`. One corrected,
  ephemeral sign-in attempt using the already configured school credentials did not leave
  the Cengage login page, and the reader again redirected to the logout page. No further
  credential attempts were made to avoid account-lockout risk.
- A later inspection of the authenticated Canvas Assignments API found seven Chapter 2
  external-tool assignments. They launch through `gateway.cengage.com` and cover sections
  2.1, 2.2, 2.3, 2.5, 2.6, 2.7, and 2.8. Canvas assignment IDs are non-secret navigation
  metadata; signed launch parameters were not recorded.
- The launch uses Cengage's LTI/OIDC authorization flow at
  `gateway.cengage.com/ws/mlapi/ltioidc/authorize`. This authorization endpoint is
  session-bound and must not be published as a reusable student link.
- Launching a Chapter 2 assignment through authenticated Canvas successfully established a
  WebAssign session. The supplied WebAssign route then opened the entitled course homework.
- WebAssign exposes JavaScript-driven `Read It` controls. Activating one opened the supplied
  MindTap reader successfully in the same ephemeral browser context.
- The authenticated reader exposed the Chapter 2 table-of-contents entries:
  - 2.1: The Tangent and Velocity Problems
  - 2.2: The Limit of a Function
  - 2.3: Calculating Limits Using the Limit Laws
  - 2.4: The Precise Definition of a Limit
  - 2.5: Continuity
  - 2.6: Limits at Infinity; Horizontal Asymptotes
  - 2.7: Derivatives and Rates of Change
  - 2.8: The Derivative as a Function
- The raw MindTap reader URL remains an authenticated resource: it redirects to the logout
  page before the LTI/WebAssign session exists, but opens after the legitimate Canvas launch
  and WebAssign `Read It` flow establish entitlement.
- No protected textbook body content, browser state, credentials, cookies, signed launch
  data, or tokens were printed or saved.
- Feasibility was confirmed for navigation, with an important constraint: the site may
  publish stable Canvas assignment links and the non-secret reader location, but it cannot
  publish or synthesize the transient LTI/OIDC authorization request. The implementation
  should provide an `Open Cengage access` bootstrap through a normal Canvas assignment and
  an ordered Chapter 2 textbook index, clearly explaining that a current entitled Cengage
  session is required. A section-specific MindTap stability probe did not expose a reliable
  reusable deep-link contract, so no section-specific reader URLs are stored.

### Implementation Status

Approved, implemented, and deployed on 2026-09-19.

- `site_textbook.py` owns immutable Chapter 2 textbook metadata, validates exact Cengage
  reader query keys, allowlists the school Canvas host/course assignment paths, and rejects
  fragments, off-domain destinations, duplicate sections, and unordered sections.
- The Calculus Chapter 2 page renders one reliable access path: launch a normal Canvas
  assignment, then choose `Read It` inside the entitled WebAssign session.
- The page lists sections 2.1 through 2.8 in order. Sections with verified Canvas homework
  link to their normal assignment; section 2.4 is labeled as textbook-only.
- External links open in a new tab with `noopener noreferrer`.
- The component is responsive and uses the existing Calculus source-page visual language.
- Course/chapter lookup prevents the component from appearing on Algebra or unrelated
  Calculus pages.
- Generated-site tests assert that no `gateway.cengage.com`, `ltioidc`, or `token=` value is
  emitted.
- No textbook body content, Cengage cookies, tokens, signed requests, or protected assets
  are stored or deployed.
- Live verification showed that a direct MindTap link could still reach the logout page even
  after a separate Canvas launch. That link was removed; generated pages now contain no
  direct `snapshotId` reader URL. Section 2.4 directs students to MindTap's `Full Book` menu.
- Red/green/refactor TDD was observed across metadata validation, rendering, course/chapter
  wiring, and responsive styling.
- Full offline validation passed with 244 tests plus Python compilation and
  `git diff --check`.
- A production-shaped `/tmp` build contained the intended five Calculus files, rendered
  sections 2.1 through 2.8 in order, emitted no gateway/OIDC/token material, and added no
  textbook component to Algebra.
- Desktop and 390-pixel mobile screenshots were inspected successfully. The watched deploy
  tree was not modified.

## Phase 6: AP Calculus AB Generated Learning Content

### Approved Scope

Implement Phase 6A and Phase 6B for the Chapter 2 study guide only. Do not enable or run
mental math, MCQ, olympiad/stretch, inspiring-video, assignment, challenge, or Live Tutor
generation for Calculus in this phase.

### Canonical Chapter Identity

- Chapter identity is keyed by `(course_id, chapter_id)`, never by chapter number alone.
- The canonical Chapter 2 title is `Limits and Derivatives`.
- The student-facing label is `Chapter 2: Limits and Derivatives`.
- Provenance is the authenticated Cengage table of contents observed through the legitimate
  Canvas/WebAssign LTI flow.
- The verified section outline is:
  - 2.1: The Tangent and Velocity Problems
  - 2.2: The Limit of a Function
  - 2.3: Calculating Limits Using the Limit Laws
  - 2.4: The Precise Definition of a Limit
  - 2.5: Continuity
  - 2.6: Limits at Infinity; Horizontal Asymptotes
  - 2.7: Derivatives and Rates of Change
  - 2.8: The Derivative as a Function
- Calculus pages use the canonical title before and after generation. A model-generated title
  cannot override it.
- Algebra keeps its existing static-title and generated-study-guide-title behavior.

### Textbook Metadata Fetch Contract

- A newly fetched Calculus chapter must have verified, course-scoped title and section
  metadata before generation or publication.
- Reuse cached verified metadata on idempotent fetches; do not make every repeat fetch depend
  on Cengage availability.
- An explicit metadata refresh may authenticate through Canvas, launch the matching Cengage
  assignment, choose the entitled `Read It` path, and capture only the chapter title and
  ordered section labels.
- Never save textbook prose, examples, exercises, images, cookies, session tokens, signed
  LTI/OIDC requests, or DRM-controlled assets.
- A failed refresh never erases previously verified metadata. If no verified metadata exists,
  the PDF fetch may remain saved but generation and publication stop.
- If a chapter has no usable Cengage launch, require a reviewed manual title and section
  outline rather than inventing either with a model.

### Phase 6A: Generation Foundation

- Add immutable course-scoped chapter metadata with provenance.
- Make the site, textbook navigation, and Calculus prompt profile consume the same chapter
  definition.
- Preserve all Algebra prompt text, slugs, model selection, artifact paths, title behavior,
  state files, and commands.
- Enable only this Calculus generation command shape:

  ```text
  --course ap-calculus-ab --skip-fetch --chapter 2 --prompt study-guide
  ```

- Require an explicit prompt for Calculus; an omitted prompt must not launch every family.
- Continue rejecting other Calculus chapters, assignment mode, and every non-study-guide
  prompt.
- Support `--dry-run` without Canvas or model calls.
- Keep artifacts isolated under `output/courses/ap-calculus-ab/`.

### Phase 6B: Study-Guide Pilot

The attached school PDF remains the mathematical content authority. Verified Cengage
metadata supplies only the canonical title and ordered organizational outline.

The Calculus prompt must require:

- exact `## Title` value: `Limits and Derivatives`;
- a short summary;
- ordered section coverage entries for 2.1 through 2.8;
- an explicit `Covered`, `Partially covered`, or `Not covered` status for every section;
- definitions, theorems, formulas, and worked explanations supported by the school PDF;
- practice problems and answers based only on concepts supported by the school PDF;
- assumptions, ambiguities, and missing coverage;
- no inference of textbook body content from section titles.

Before canonical persistence, validate that:

- the title exists exactly once and matches the canonical title;
- required headings exist exactly once;
- sections 2.1 through 2.8 appear exactly once and in order;
- each section contains an allowed coverage status;
- the response is nonempty and contains no provider error text.

A validation failure must not mark the prompt complete or overwrite a prior valid artifact.
Do not automatically retry the first pilot; report the rejected output so prompt defects and
additional model cost remain visible.

### Phase 6 Backward-Compatibility Contract

1. Algebra resolves the existing prompt specifications without text changes.
2. Algebra generation requires no Cengage or course-chapter metadata.
3. Algebra title resolution remains unchanged.
4. Calculus metadata cannot resolve for an Algebra course lookup.
5. Algebra artifact paths and state filenames remain unchanged.
6. Calculus validation failures cannot block an Algebra run.
7. Existing Algebra artifacts are not migrated, regenerated, or rewritten.

### Phase 6 TDD and Execution Sequence

1. Red/green/refactor for course-scoped chapter identity and Algebra isolation.
2. Red/green/refactor for canonical site titles before and after generation.
3. Red/green/refactor for Calculus-only prompt selection and CLI rejection paths.
4. Red/green/refactor for PDF-plus-outline study-guide prompt construction.
5. Red/green/refactor for strict output validation before persistence.
6. Run the full offline validator and a production-shaped `/tmp` build.
7. Run a no-network dry run for the exact study-guide command.
8. Execute one approved Chapter 2 study-guide model call.
9. Review title, structure, source fidelity, mathematical content, artifact isolation, and
   site rendering.
10. Do not deploy until the generated guide is reviewed and deployment is separately
    approved.

### Phase 6 Acceptance Criteria

1. Every Calculus chapter has verified metadata before generation or publication.
2. All Chapter 2 surfaces say `Chapter 2: Limits and Derivatives` consistently.
3. The model receives the school PDF plus title/section metadata, but no textbook body
   content.
4. Only the explicit Chapter 2 study-guide prompt can run for Calculus.
5. Invalid output cannot become canonical or mark generated state complete.
6. Calculus artifacts and state remain isolated from Algebra.
7. Algebra behavior is unchanged and protected by regression tests.
8. The generated page retains the class note and Cengage/WebAssign navigation while adding
   only the reviewed study guide.
9. Calculus still exposes no assignments, challenges, Live Tutor, or other prompt families.
10. Full tests, compilation, diff checks, dry run, and staging build pass.

### Phase 6 Recovery and Rollback

- Existing file-existence skip logic makes a successful pilot idempotent.
- Use targeted force only for the Calculus `study-guide` prompt after an explicit review
  decision.
- Atomic state persistence preserves completed work across interruption or provider failure.
- Rollback reverts the generation policy, prompt profile, and site-title wiring, then rebuilds
  the site. Preserve generated artifacts for review unless deletion is separately approved.
- No artifact migration or database change is required.

### Phase 6 Implementation Status

Phase 6A and the Phase 6B study-guide pilot were implemented and deployed on 2026-09-19.

- `course_curriculum.py` is the single immutable source for the course-scoped Chapter 2 title,
  ordered sections, provenance, and verification date.
- Calculus pages use `Chapter 2: Limits and Derivatives` before and after generation; the
  existing Algebra generated-title behavior is unchanged.
- Calculus accepts only the explicit saved-PDF command
  `--course ap-calculus-ab --skip-fetch --chapter 2 --prompt study-guide`.
- Dry-run performs no Canvas call, credential resolution, model-client initialization, or
  browser launch.
- `calculus-study-guide-v1` validates the exact title, headings, section order, one coverage
  status per section, nonempty output, and provider-error absence before persistence.
- The original GPT-5.4 pilot was replaced with one explicitly approved mastery-oriented run.
  The replacement uses the PDF to establish topic scope while allowing verified supplemental
  teaching within those topics. It contains 15 worked examples and ten progressively structured
  practice problems with fully worked answers. Section 2.4 is `Not covered`; section 2.8 is
  `Partially covered`; the remaining sections are `Covered`.
- Never regenerate this study guide, including with any force option, without explicit user
  approval. Rebuilds consume the saved artifacts and make no model call.
- A staging build preserved the class note and Cengage navigation, added only the study guide,
  and exposed no Calculus challenges, Live Tutor, assignments, mental math, or olympiad links.
- The superseded guide and its temporary rollback copy were discarded only after the replacement
  passed validation and editorial review. No automatic retry or additional model call occurred.
- The mastery replacement is deployed in the production domain-root tree. A later deterministic
  rebuild corrected multiline display math inside list items without changing the saved Markdown
  or making another model call.
- Guarded production commands now enforce the root deploy directory and empty base path, reject
  nested `site/` output and stale `/site/` links, require explicit production confirmation, and
  verify live Calculus and Algebra content after deployment.
- Full offline validation passes 299 tests plus Python compilation and `git diff --check`.

### Deferred Calculus Mental Math

A cumulative mental-math bank organized by released subsection was discussed after Phase 6, but
the user explicitly abandoned that plan pending further guidance. It is not approved work. Do not
implement a Calculus mental-math prompt, release detector, cumulative bank, site card, or model
generation until a new specification is written and explicitly approved. The existing Algebra II
mental-math behavior remains unchanged.

## Phase 7: External AI Chapter Challenge Cards

Approved, implemented, deployed, and user-verified on 2026-09-20.

### Scope

- Add an `AI Challenge` section only to AP Calculus AB Chapter 2.
- Offer Medium and Hard prompt cards, each configured for ten original sequential MCQs.
- Each card offers Gemini and ChatGPT actions that copy the prompt and open the provider's official
  consumer homepage in a new tab.
- Provide an accessible manual-copy fallback when clipboard access is unavailable.
- Reuse the visual language of the Algebra chapter challenge cards without enabling the Algebra
  challenge application, PHP backend, database, saved progress, or exam catalogs for Calculus.
- Do not make a model API call, select a provider model, generate saved artifacts, or incur a project
  model charge.

### Prompt Boundaries

- Generate original AP Calculus AB-style practice from first principles; never quote, reproduce,
  paraphrase, imitate, or transform a published exam or textbook question.
- Ask one question at a time, wait for the student's response, explain the result, maintain a score,
  and finish after exactly ten questions.
- Require exactly four choices and exactly one correct answer, with private validation before each
  question is shown.
- Stay within the verified Chapter 2 outline while excluding the PDF-uncovered formal epsilon-delta
  definition in section 2.4 and limiting section 2.8 to introductory derivative-as-a-function ideas.
- Exclude later differentiation, integration, differential-equation, optimization, and related-rate
  topics.

### Implementation Status

- `site_ai_challenges.py` owns immutable provider definitions, scoped prompts, URL validation,
  escaped rendering, clipboard behavior, and fallback controls.
- Provider destinations are exact parameter-free HTTPS URLs for `gemini.google.com/app` and
  `chatgpt.com/`; undocumented prompt or model-selection query parameters are not used.
- `site_records.py` wires the component only for `(ap-calculus-ab, 2)` and leaves Algebra unchanged.
- Red/green/refactor TDD covered initial Chapter 2 rendering and responsive styling. Focused
  regression coverage validates prompt boundaries, provider safety, external-link protections,
  accessibility status, clipboard fallback, and course/chapter isolation.
- Full offline validation passes 299 tests plus Python compilation.
- A production-shaped `/tmp` build passed guarded layout validation. Its generated Chapter 2 page
  contains exactly the Medium and Hard cards with both providers, while unique component identifiers
  do not appear anywhere under the Algebra course directory.
- Desktop and 390-pixel mobile screenshots were inspected successfully.
- The initial production deployment exposed a compatibility regression: the guarded command
  refreshed `/site/courses/...` but left the established domain-root `/courses/...` copy stale.
  A temporary repair synchronized both copies. The final approved architecture restores
  `/courses/...` as the sole canonical location: production builds use an empty base path, reject
  nested `site/` output and stale `/site/` links, synchronize the root once, and verify only the
  canonical live pages. The obsolete local and remote `site/` trees were removed after canonical
  live verification passed; the root Chapter 2 URL returns HTTP 200 and the former `/site/` URL
  returns 404.

### Recovery and Rollback

The feature is a deterministic site-rendering component with no stored questions, user state,
database changes, or generated model artifacts. Rollback removes the isolated renderer and its
Chapter 2 wiring, then rebuilds the site. Existing course content and challenge results are
unchanged.
