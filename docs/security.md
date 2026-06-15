# Security and Trust Boundaries

Otoe executes local Python code. It is a UI/runtime framework and build tool,
not a sandbox.

## Local Code Execution

`otoe dev`, `otoe render`, `otoe plan`, `otoe build`, and generated runners all
load user-selected Python targets. Event handlers execute as normal Python code
with the same permissions as the process. `otoe dev` is intended for local
development and should not be exposed as a public service.

The live preview event endpoint accepts only small JSON payloads and validates
the event id, argument list, and event ordering fields before dispatch. These
checks reduce malformed local requests and obvious oversized payloads; they do
not add authentication, authorization, or a sandbox boundary.

## Backend Packages

Backend packages are experimental renderer-candidate artifacts. Package checks
can execute Python entrypoints and subprocesses. Do not run backend packages
from untrusted sources.

## Dependency Audit

`otoe deps` is audit-only. It can report missing packages, undeclared imports,
visible dynamic imports, and visible runtime policy concerns, but it does not
install dependencies, create a lockfile, or isolate execution.

## Offline Bundles

Offline bundles verify manifest entries, sizes, SHA-256 hashes, generated
artifacts, backend reports, and runtime policy metadata. These checks help catch
drift and tampering inside the bundle format. They do not isolate Python code
from the operating system.

Runtime policy warnings and errors are developer guardrails. They are not
OS-level containment for network, filesystem, subprocess, or device access.

## Recommendations

- Use a virtual environment per project.
- Review backend package manifests and entrypoints before running checks.
- Run bundles only from trusted sources.
- Keep hardware/cage profile builds in controlled deployment directories.
- Use containers, VMs, or OS sandboxing when you need real isolation.
- Treat experimental backend and native surfaces as trusted-code development
  tools unless a separate containment layer is present.
