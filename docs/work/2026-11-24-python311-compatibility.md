# Python 3.11 compatibility migration

| Field | Value |
| --- | --- |
| Status | Needs review: local source and wheel validation pass; hosted validation pending |
| Owner | Unassigned |
| Updated | 2026-11-24 |
| Next review | 2026-11-25 |
| Baseline | `329eef3651a97b3f12f00588ee501fb9cf55bb0e` |
| Branch | `compat/python311` |
| Issue | [#21](https://github.com/Chain-Frost/run-hy8/issues/21) |

## Scope

Support Python 3.11, 3.12, 3.13 and 3.14; retain Python 3.14 as preferred development interpreter.
Exact standalone CPython 3.11.11 represents the owner's ArcGIS Pro version target;
it does not establish execution inside ArcGIS Pro. Preserve algorithms, numerical tolerances,
reference fixtures, licensing and publication protections. No merge or publication is authorized.

## Validation

Windows isolated environments: Python 3.11.11, 3.12.14, 3.13.15 and 3.14.6.
All four applicable source suites pass: **358 passed** per interpreter / 47 native/legacy cases deselected.
Ruff 0.16.6 lint/format and strict Pyright target Python 3.11; rule selection and complexity limits are unchanged.
Source compilation under Python 3.11.11 passed. Wheel and sdist builds pass.
Clean wheel installation, isolated import-origin verification and pip check pass on all four interpreters.
Installed CLI help passes where a CLI is exposed. FFA distribution verification and its independent
clean-wheel/console-entrypoint smoke also pass. Independent exact-head review and hosted results remain pending.
Native HY-8, ArcGIS Pro and Flike acceptance are not established by these checks.

## Changes and dependencies

Replace PEP 695 aliases and the enum-coercion generic with TypeAlias/TypeVar. Runtime dependency bounds are unchanged.

## Next action

Publish the checked compatibility PR, obtain independent review of its exact head and verify the final hosted matrix. No merge or release.

Local evidence directory: `E:/Github/compat311-evidence` (not required at runtime). Ruff safe fixes: 2 automatic; 1 generated TypeVar naming finding corrected manually.
