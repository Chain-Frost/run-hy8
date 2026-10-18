# run-hy8 documentation

`run-hy8` provides a Windows-only Python interface for generating, reading,
executing, and analysing HY-8 version 8 culvert projects. Python 3.13 and 3.14
are supported by the current package.

For installation, usage examples, release information, and limitations, see the
[repository README](https://github.com/Chain-Frost/run-hy8#readme).

## Using the library

- [API reference](api.md) — models, execution, hydraulic helpers, result parsers, and elliptical catalogues
- [Headwater and flow helpers](headwater_helpers.md) — forward and inverse hydraulic calculations
- [Roadway overtopping](roadway_overtopping.md) — road geometry, overtopping policy, and validation limits
- [HY-8 v8 inlet configurations](hy8_v8_inlet_configurations.md) — shape/material-specific inlet definitions

## Packaging and publishing

- [Verified package builds](packaging.md) — local wheel verification and installation
- [PyPI publishing](pypi_publishing.md) — current trusted publishing and release policy
- [Automatic release policy](AUTO_PYPI_RELEASES.md) — cutover and eligible merges

## Development and validation history

- [Contributing](CONTRIBUTING.md) and [agent guidance](agents.md)
- [Roadway overtopping validation history](work/2026-10-05-roadway-overtopping-validation-support.md)
- [Release automation history](work/2026-10-16-pypi-release-automation.md)

Historical work records describe the work at the time; refer to the feature
documentation and publishing policy for the current supported behaviour.
