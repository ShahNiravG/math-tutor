## Safety Guardrails (Strict Permissions)

These rules are mandatory unless you explicitly override them in the same message.

### 1) Default execution mode
- Use sandboxed execution only.
- Prefer read-only inspection commands first.
- Do not edit files, run installers, or execute generated scripts unless explicitly approved.

### 2) Write scope restrictions
- If editing is required, use `workspace-write` only.
- Only edit files under `/home/nshah` unless explicitly approved.
- Never create or modify dotfiles (`.env`, `.gitconfig`, shell profiles, etc.) unless explicitly approved.

### 3) Network restrictions
- Keep network access restricted by default.
- Do not install packages, pull remote repos, call external APIs, or download files unless explicitly approved.

### 4) Escalation and approvals
- Any action requiring escalated permissions must include a one-line justification and wait for approval.
- No implied consent from prior approvals; ask again for each new sensitive action.

### 5) Forbidden operations without explicit approval
- `rm`, recursive deletes, bulk moves, or overwrites.
- `git reset --hard`, `git checkout --`, rebases, force-pushes, history rewrites.
- Running GUI/open commands.
- Secrets access (credential managers, keychains, token files).

### 6) Git safety rules
- Never change git history unless explicitly requested.
- Never commit unless explicitly asked.
- Never amend commits unless explicitly requested.
- Do not revert unrelated local changes.

### 7) Approval prefix scope
- If requesting reusable approvals, keep prefix rules narrow (for example: `["pytest"]`, `["npm","run","test"]`).
- Do not request broad prefix approvals such as `["python"]` or `["bash"]`.

### 8) Transparency requirements
- Before any file edit: state which files will be changed and why.
- After changes: summarize exactly what changed with file paths.
- If blocked by permissions, stop and ask instead of attempting workarounds.

### 9) Secrets and sensitive data
- Never print full secrets, tokens, or keys in output.
- If a file may contain secrets, summarize findings without exposing values.

## Software Development Lifecycle

### 1) Specification and design approval

For every implementation task, begin with a written specification and design plan.

Before modifying implementation code:

- Define requirements, scope, and acceptance criteria.
- Document the proposed architecture and interfaces.
- Identify risks, failure modes, dependencies, and assumptions.
- Define the testing strategy.
- Address deployment, migration, rollback, and recovery when applicable.
- Present the specification and design to the user.
- Obtain explicit user approval.

Do not begin implementation until the user explicitly approves the specification and design.

### 2) Red/green/refactor test-driven development

Use strict red/green/refactor TDD for every behavior change:

1. **Red:** Write or update the smallest test that defines the intended behavior.
2. Run it and confirm it fails for the expected reason.
3. If it passes before implementation, correct the test or explain why it does not establish new behavior.
4. **Green:** Implement only enough production code to make the failing test pass.
5. Run the new test and relevant regression tests and confirm they pass.
6. **Refactor:** Improve the implementation and tests without changing behavior.
7. Run the relevant test suite again and keep it green.

Provide evidence of both the expected red result and the subsequent green result.

Do not:

- Write production code before establishing the failing test.
- Batch unrelated behavior into one red/green cycle.
- Weaken, delete, skip, or bypass tests merely to obtain a green result.
- Treat a test that fails because of syntax, setup, dependency, or environment errors as a valid red test.
- Claim TDD was followed unless the red result was actually observed.

### 3) Mission-critical engineering

Apply mission-critical engineering standards. Prioritize:

- Correctness
- Reliability and deterministic behavior
- Security
- Data integrity
- Recoverability
- Observability
- Maintainability

During design and implementation:

- Identify and address failure modes.
- Validate inputs and invariants defensively.
- Use explicit error handling.
- Never silently ignore unexpected errors.
- Prefer atomic and idempotent operations where appropriate.
- Protect preserved data and previously generated artifacts.
- Test failure paths, boundary conditions, interruption behavior, and recovery.
- Provide safe migrations, rollback plans, and recovery procedures when applicable.
- Prefer proven, understandable designs over unnecessary complexity.

### 4) Backward compatibility

Preserve backward compatibility for:

- Public interfaces
- Command-line behavior
- Data and file formats
- Configuration
- Stored state and generated artifacts
- Existing workflows
- Deployment behavior

Explicitly analyze backward compatibility during design and test existing behavior.

If backward compatibility cannot be maintained:

1. Stop before implementation.
2. Explain what would break and why.
3. Describe affected users, data, interfaces, and workflows.
4. Propose a migration and rollback path.
5. Obtain explicit user permission for the breaking change.

Do not introduce a breaking change without that explicit approval.
