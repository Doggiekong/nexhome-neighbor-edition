# Distribution — 0.1.0 PRIVATE RC, not published

## Status and ownership

Product0.1.0 / upstream1.1.16 remain independent. Repository remains PRIVATE. No public download, Release, tag, HACS/Beta, signing-key publication, neighbor distribution or pilot is created by this design. License / publication authorization is USER MANAGED / OUTSIDE TECHNICAL GATE; see NOTICE.md. No legal review is performed here.

## One Candidate, two bootstrap paths

An immutable Candidate packet contains the same schema2 runtime artifact, installer/launcher SDK, trusted source definitions, upstream NOTICE and build manifest. App and Terminal consume the identical packet; they cannot rebuild from moving main or select latest silently. The release-candidate-manifest records full source commit mapping, exact file inventories, SHA-256 and tested platform matrix. Internal Candidate replacement gets a distinct build ID, never overwrites the frozen packet, and invalidates affected Pilot gates. A product release version maps to one final immutable artifact; abandoned internal Candidate builds remain evidence only.

## Implemented RC delivery, not public publication

The same repository now has official HA App repository metadata and one visible App folder. The old packaging template is hidden to prevent duplicate App slugs. Supervisor actually shallow-cloned a controlled local Git equivalent, built/installed the helper and ran its existing Ingress UI in VM201. No source was pre-copied to the local App folder.

The Terminal bootstrap is a standalone stdlib frontend: one full command downloads/verifies the pinned bootstrap; it verifies the frontend and immutable 0.1.0 packet, discovers Docker/HA/config/origin, presents arrow-key menus and invokes the original SDK in the selected existing HA image. It never downloads moving main.zip or upgrades host Python. Credentials stay in memory/stdin and the temporary login grant is revoked at exit.

The ordinary default is a fixed v0.1.0 Release URL. **That Release does not exist yet.** Current actual evidence uses an explicitly permitted local equivalent, with the exact one-line command and limitations in [RC distribution verification](rc-distribution-bootstrap.md). A test source is not advertised as a public download. The pinned project command is the trust anchor; packet hashes alone are not a signature or independent provenance service. No signing system is claimed. App Docker base is version-pinned; a digest-published image/CDN distribution remains unverified, not fabricated.

VM400 cold-start used host Python3.13 only for the stdlib frontend and the existing official HA2026.10.2 image/Python3.14 for the frozen SDK. Container config must be a writable host bind mounted at the same absolute host path. Current tested scope is amd64 HAOS/Linux Docker. Named volumes/custom TLS/other platforms fail conservatively or remain unverified. Docker access is powerful local host access, disclosed before confirmation; unrelated containers are not operated.

## Updates and conflicts

Future0.1.1/0.2.0 uses semantic product version comparison plus ownership/source/hash evidence. Same version and same files gives NO_OP; same version with different deployed files is refused. Candidate rebuild is not an excuse to silently overwrite an existing release version. Official version numbers do not participate in Neighbor ordering. Existing config entry remains, no repeated discovery. HACS-owned code is not overwritten: explicit supported ownership transfer first; MANUAL_UNKNOWN refuses writes until source and user intent are safely established. No unstable HACS private API.

## Recovery contract

- REVERSIBLE: deployment-only file/owner changes with verified backup and health rollback, including fresh install back to absent code; preserve original entry and references.
- FORWARD_ONLY_BUT_COMPATIBLE: additive semantic migration that retains legacy identity and references; code rollback does not automatically erase registry changes.
- RECOVERY_REQUIRED: unknown/partial ownership, registry/schema mutation that cannot be proven reversible, failed restore, concurrent modification or unexpected identity churn. Stop, retain journal/baseline, recover using supported HA backup/snapshot procedures; never claim code rollback equals full HA state rollback.

No release promotion until the Stage E gates and subsequent explicit release authorization. Longer real observation, production distribution infrastructure and untested platforms remain explicit boundaries. Publication authorization is user-managed and is not a technical/license gate here.
