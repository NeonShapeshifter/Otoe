# Security Policy

## Supported Versions

Otoe is pre-alpha. Security fixes are made only on the latest release and the
current `main` branch. Older releases are not maintained.

## Reporting A Vulnerability

Do not publish exploit details in a public issue. Use GitHub's private
[security advisory form](https://github.com/NeonShapeshifter/Otoe/security/advisories/new)
to report the affected version, reproduction steps, impact, and any suggested
mitigation.

Otoe executes trusted local Python code and is not a sandbox. Read
[`docs/security.md`](../docs/security.md) before reporting behavior that depends
on running an untrusted app, backend package, or generated bundle.
