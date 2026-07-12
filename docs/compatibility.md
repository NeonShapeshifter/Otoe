# Compatibility And Versioning

Otoe is pre-alpha and uses `0.x` versions. This policy prevents casual breakage;
it is not a stable-API declaration.

## Version Meaning

- Patch releases fix defects, documentation, tests, packaging, and behavior that
  violated an existing documented contract. They should not intentionally remove
  a documented app-author API.
- Minor releases may change preview APIs, portable behavior, or artifacts. Every
  intentional breaking change must be listed in the changelog with a migration.
- A release already present on PyPI is immutable. Corrections always use a new
  version; tags and artifacts are never replaced.

## Guarantees By Tier

| Tier | Pre-1.0 compatibility intent |
| --- | --- |
| `core-preview` | Protect documented behavior. Deprecate before removal when technically possible. |
| `product-preview-ui` | Preserve preferred `otoe.ui` imports across patch releases; minor releases may revise props with migration notes. |
| `preview-support` | Best-effort compatibility; behavior follows documented app-author workflows. |
| `experimental-native` | No compatibility guarantee. Changes must remain explicit and must not break the dependency-light default path. |
| `experimental-backend` | Contract/schema versions govern artifacts; Python helper APIs may change without deprecation. |
| Internal modules | No compatibility guarantee. |

Top-level aliases remain compatibility shims during pre-alpha. New app code
should use the preferred import recorded by `api_status(name)`.

## Deprecation Process

For `core-preview` and `product-preview-ui` APIs:

1. Add the replacement and preserve the old behavior.
2. Emit `DeprecationWarning` from the old call or import path when practical.
3. Document the replacement and first deprecated version in the changelog.
4. Keep regression coverage for both paths for at least one minor release.
5. Remove only in a later minor release and include a concrete migration example.

Immediate removal is reserved for a security boundary, unreleased code, or a
contract that cannot work correctly. The changelog must explain the exception.

## Artifact And Schema Compatibility

Serialized RenderTree, styleOps, bundle, backend package, and evidence formats
must carry a schema/format version. Readers reject unsupported versions and
malformed required fields rather than guessing. A schema change requires fixture
updates, compatibility tests, and a migration or explicit rejection policy.

## Stable Graduation Bar

No API becomes stable merely because it is popular. A stable tier requires:

- the native vertical slice and relevant hardware gates to exercise it;
- runtime and typing contracts that match;
- at least one release-candidate cycle with downstream apps;
- documented supported platforms and optional dependencies;
- a SemVer deprecation window suitable for `1.0`.
