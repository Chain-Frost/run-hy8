# PyPI release automation and CI consistency

| Field | Value |
| --- | --- |
| Status | Active |
| Owner | ChatGPT |
| Created | 2026-10-16 |
| Updated | 2026-10-16 |
| Next review | 2026-10-23 |
| Delivery | feature/pypi-release-automation; [PR #10](https://github.com/Chain-Frost/run-hy8/pull/10) |

## Scope

Set up the same reviewed release-PR, post-merge CI, stable-release and OIDC publication
process as ryan-tools. Add consistent Perth-date preparation and focused CI improvements.
Preserve package interfaces, interpreter coverage and hydraulic validation boundaries.

## Current state

Added preparation/finalization/publication workflows and the release helper. The
[publication guide](../pypi_publishing.md) owns setup, release and recovery instructions.
[PR #10](https://github.com/Chain-Frost/run-hy8/pull/10) owns current review status. No release or PyPI upload has been started.

## Next action

Review the new PR and its hosted checks, merge reviewed automation, then run the first
release explicitly. Publish run-hy8 first, then validate the optional ryan-culverts extra.
The user supplied screenshots confirming both pending PyPI publishers are configured.

## Validation and delivery

Local validation on Python 3.14:

- Calendar and transactional rollback tests: 16 passed.
- Ruff check and format passed; strict Pyright passed with zero diagnostics.
- Actionlint passed across all workflows; PowerShell parsing passed for every pwsh block.
- Executed workflow JavaScript locally against 13 mocked stable-release/finalization
  scenarios, including ordinary merges, two/four-digit years, retries and invalid tags.
- URL-dependency validation passed against the retained wheel, accepted a normal optional
  PyPI requirement and rejected a synthetic Git URL dependency in an extra.
- Full preparation through the real verified builder and Twine passed in an isolated
  temporary source copy. Normal checkout versions were not bumped.
- Git diff whitespace checks passed before commit.
No hydraulic coefficients, methods or retained comparison evidence changed.

HY-8 executable comparison was not run; it is not required to configure publication.
Hosted publication and OIDC remain untested until the PyPI setup and PR merge.

## Repository-specific evidence

- Scoped ordinary suite with PYTHONPATH=src: 320 passed, 46 external/legacy cases
  deselected in 2.84 seconds; no skips. No HY-8 executable comparison ran.
- Ruff format: 86 files already formatted; strict typing of package and new helper/tests
  had zero diagnostics. Strict MkDocs build passed.
- Existing retained 2026.10.5.1 wheel verifier, Twine and temporary-target installed-wheel
  smoke passed. No source/package metadata changed in this setup PR, so no retained-wheel
  replacement was necessary.
- Real preparation in a temporary source copy built and verified 2026.10.16.1.
- Python 3.13 regression validation is retained in hosted CI; it was not run locally.
- Markdown lint passed for all modified/new documents. An optional full-tree Markdown
  scan found pre-existing MD012/MD022 blank-line issues at lines 514-515 of
  `2026-10-05-roadway-overtopping-validation-support.md`; that historical file was
  preserved. Global Markdown lint is not part of the existing run-hy8 CI workflow.

## GitHub and PyPI setup

Configured and re-read the main/tag rulesets, squash-only repository merge settings,
automatic branch deletion, Actions PR creation and tag-only pypi environment. Main
requires this repository's existing CI contexts and resolved review conversations,
with zero required approvals and maintainer bypass restricted to PRs. Tags require
CI, permit creation by automation and restrict updates/deletions. No API token was stored.
Both PyPI pending publishers were confirmed by the user's screenshot. Setup workflows
are committed and pushed in PR #10; no merge, release or upload was performed.

## Retry review fix, 2026-10-16

The review correctly identified duplicate publication dispatch on finalizer retries.
Across all three repositories, finalization now checks PyPI and active publication runs
before dispatching. Already published or active revisions skip dispatch; missing versions
with no active run remain recoverable. Transient/unknown lookup failures fail closed.
All 16 mocked release/finalization/retry scenarios passed, including already published,
active, failed previous attempts and unavailable lookup service. Actionlint and touched
document checks are rerun before pushing; exact-head hosted CI must pass before merging.

The user asked to continue with first-publication validation. Complete review fixes and
required CI, then merge and publish run-hy8 first, verify its public installation, and
subsequently publish ryan-culverts and validate the optional integration.

Restored the original UTF-8 README after a generated edit corrupted an em dash; the
README diff against main now contains only the publishing-guide link.
