# Publishing run-hy8 to PyPI

## One-time setup

Add a pending publisher at [PyPI account publishing](https://pypi.org/manage/account/publishing/)
for the first release, or use the project's Publishing settings if it already exists.
Enable two-factor authentication on your PyPI account.

| Field | Value |
| --- | --- |
| PyPI project | `run-hy8` |
| GitHub owner | `Chain-Frost` |
| GitHub repository | `run-hy8` |
| Workflow filename | `pypi-publish.yml` |
| Environment | `pypi` |

The GitHub `pypi` environment allows `v*` tags without a required reviewer, so publication
is automatic after release validation. Actions must be allowed to create PRs; the
workflows request write permissions only in the preparation/finalization jobs.
No PyPI API token or GitHub personal access token is stored.
A pending publisher does not reserve the project name.

The main ruleset requires PRs, squash merges, resolved review conversations and successful
up-to-date CI. Required approvals remain zero for the solo-maintainer workflow. The
maintainer bypass is limited to PRs. Release tags require CI and cannot normally be
updated or deleted; tag creation remains permitted for the workflow token. Merged
branches are automatically deleted. The PR records live configuration and validation.

## Automated release

1. Run **Actions > Release to PyPI > Run workflow** on `main`.
2. The shared release-preparation helper selects the next Perth calendar version,
   updates metadata, and invokes the existing verified builder. A builder failure
   restores metadata and preserves the builder's retained-artifact safeguards.
3. Review the generated `release/pypi-<version>` PR. Approve its PR-event workflows
   if GitHub displays **Approve workflows to run**. Dispatched CI cannot substitute
   for the required PR checks.
4. Squash merge after every required check passes. Main push CI is preserved per run,
   even when later merges arrive. Successful CI at that exact merge SHA triggers
   **Finalize PyPI release**, which parses the merged TOML version and creates
   `v<version>` and a stable GitHub Release.
5. Finalization explicitly dispatches **Publish to PyPI** on the tag. Publication
   requires an existing published, non-draft, non-prerelease release, matching version
   and a commit reachable from main. It rebuilds without bumping, runs the repository
   verifier and Twine, smoke-tests the exact wheel, and uploads that artifact through OIDC.
6. Check the publication run and [PyPI project](https://pypi.org/project/run-hy8/).

Ordinary PR merges do not publish. Preparing the release PR is a deliberate manual start;
merge is the human review boundary. No additional publication approval is required.
The version scheme remains `yyyy.m.d.revision` so existing version ordering is preserved.
Release preparation uses Perth time (UTC+08:00), independent of the runner's timezone.
Normal local build behaviour remains documented in [packaging](packaging.md).

## Recovery and manual releases

Only one release PR may be open at a time. If preparation fails after pushing a branch,
inspect it and any PR before retrying. Rerun failed CI at the exact release merge SHA;
a later successful SHA does not finalize an earlier release. Finalization is safe to retry
when the existing tag points to the same SHA; it refuses a conflicting tag or prerelease.
After correcting a publication failure, rerun the publisher on the same stable release tag.
Do not move release tags or reuse a version already uploaded to PyPI.

A manually published stable GitHub Release also triggers publication. Its tag must exactly
match `v` plus the declared version and point to a commit on main. A bare tag or draft does
not publish; a prerelease cannot bypass the stable-release gate through manual dispatch.

After publication, install or upgrade with:

```powershell
python -m pip install --upgrade run-hy8
```

The Python import remains `run_hy8`. A publication or packaging smoke check is not
new engineering validation and does not run HY-8. Hydraulic validation limitations and
optional local executable checks remain unchanged.

## CI scope

CI checks workflows using checksum-verified Actionlint 1.7.12. Superseded PR runs cancel;
main push runs remain independent for release finalization. Multi-command PowerShell
steps stop at the first failed check. Builders verify their candidates, so immediately
repeating that verification is unnecessary; retained-wheel verification remains separate.
Test duration reports identify future bottlenecks without disabling hydraulic tests.

Python 3.13 and 3.14 checks remain distinct compatibility evidence. Hosted tests select
the tests directory and exclude requires_hy8 and legacy_parity. Publication uses the
existing temporary-target smoke test, which installs the declared runtime dependencies
and checks every exported public symbol outside the checkout.

References:

- [PyPI pending publishers](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
- [GitHub workflow triggers](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)

Publication also rejects direct URL dependencies, including optional extras, before
upload. Publish run-hy8 before testing the optional ryan-culverts external-validation
extra; that extra now resolves run-hy8 from PyPI rather than from Git.
