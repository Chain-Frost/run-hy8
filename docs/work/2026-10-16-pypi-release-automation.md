# PyPI release automation and CI consistency

| Field | Value |
| --- | --- |
| Status | Complete |
| Owner | Unassigned |
| Created | 2026-10-16 |
| Updated | 2026-10-16 |
| Next review | None |
| Delivery | Setup PR #10 and release PR #11 merged; main at 8f2e5b5; PyPI 2026.10.16.1 published |

## Scope

Set up the same reviewed release-PR, post-merge CI, stable-release and OIDC publication
process as ryan-tools. Add consistent Perth-date preparation and focused CI improvements.
Preserve package interfaces, interpreter coverage and hydraulic validation boundaries.

## Current state

The common release lifecycle is merged and first publication succeeded. The
[publication guide](../pypi_publishing.md) owns future setup/release/recovery instructions.
The public wheel matches the publication CI artifact and passed an isolated installation
with all exported symbols checked. No user-site installation was replaced.

## Next action

No release-setup work remains here. Future releases start with **Release to PyPI** on
main. Continue the separately tracked ryan-culverts and ryan-tools publications.

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
Hosted publication and OIDC are verified by the completed runs listed below.

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
Both PyPI pending publishers were confirmed by the user's screenshot. Setup and release workflows are merged through PRs #10/#11; completed publication evidence follows below.

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

## First publication complete, 2026-10-16

- Setup PR #10 merged as 2a36c73; release PR #11 merged as 8f2e5b5.
- Preparation run 38774040263 succeeded and selected the Perth date correctly.
- Release PR CI run 38774199047 passed both Python 3.13 and 3.14 jobs.
- Main CI run 38774544708 passed at the exact release SHA; Pages also succeeded.
- Finalization run 38774817463 created v2026.10.16.1 and dispatched publication.
- Publication run 38774844924 passed build/verification/smoke and Trusted Publishing.
- Public version: [2026.10.16.1](https://pypi.org/project/run-hy8/2026.10.16.1/).
- Downloaded from the public PyPI index and compared SHA-256 against both PyPI JSON
  and the pypi-distributions CI artifact: exact match.
- Wheel SHA-256: `1ba5010ecf1c559899cf05ee7c20a25bdae4bb8c26a188571ac9290c13e2bdbc`.
- Installed with declared dependencies in a fresh target and used isolated Python
  (`-I -S`) outside the checkout. Version, import location, typed marker and every
  public export passed. No HY-8 executable or new hydraulic comparison was run.
- Local proof: `C:/Users/Ryan/AppData/Local/Temp/run-hy8-public-release-proof-h9oxqqzx/proof.json`.
- The ryan-culverts release candidate's external-validation extra successfully resolved
  this public release and passed an isolated API/geometry smoke before its release merge.
- Code/version/wheel are committed, pushed and merged. This completion handoff is
  included in cleanup PR #6.
