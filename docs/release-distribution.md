# Distribution design — Stage E, not published

## Status and ownership

Product0.1.0 / upstream1.1.16 remain independent. Repository remains PRIVATE. No public download, Release, tag, HACS/Beta, signing-key publication, neighbor distribution or pilot is created by this design. Public redistribution is blocked pending upstream license confirmation; see NOTICE.md.

## One Candidate, two bootstrap paths

An immutable Candidate packet contains the same schema2 runtime artifact, installer/launcher SDK, trusted source definitions, upstream NOTICE and build manifest. App and Terminal consume the identical packet; they cannot rebuild from moving main or select latest silently. The release-candidate-manifest records full source commit mapping, exact file inventories, SHA-256 and tested platform matrix. Internal Candidate replacement gets a distinct build ID, never overwrites the frozen packet, and invalidates affected Pilot gates. A product release version maps to one final immutable artifact; abandoned internal Candidate builds remain evidence only.

## App delivery (future, not implemented publication)

After separate release authorization and license clearance, an official project-controlled HA App repository would expose a versioned helper built from the pinned source. Images must be addressed by platform-specific digest with the build/source manifest available. Initially only tested amd64 HA OS is eligible. HA-native App install/start/Ingress, shared transactional core, native config flow and explicit READY remain the flow. A hash supplied inside the same untrusted packet is integrity, not independent provenance. No private-source URL is advertised as a public installer.

## Terminal delivery (future, not implemented publication)

A versioned project-controlled release location should provide the complete packet, canonical checksums and a signed manifest/signature verified against a separately published trust root. The convenient path may automate download+verify+execute only after trust setup; auditable path downloads to disk first, verifies a separately obtained checksum/signature, inspects metadata, previews, then explicitly confirms. Neither path pipes an unchecked network script into a shell. No claim is made that a signing service, trust root or release host already exists.

Actual reference execution uses Python3.14 from the fixed official HA2026.10.2 image; VM400 host Python3.13 is not used or upgraded. Container execution requires the existing config bind to appear at the same absolute host path for mapping verification, Docker CLI/socket access restricted to the one-shot maintainer process, explicit target container, compatible runtime/network, and short-lived local HA authorization. This is powerful local Docker access, not an end-user web permission. Temporary token files must be0600 in a0700 directory, excluded from Git, revoked/deleted after use. Exact platform/image/resource evidence is retained with the Pilot.

## Updates and conflicts

Future0.1.1/0.2.0 uses semantic product version comparison plus ownership/source/hash evidence. Same version and same files gives NO_OP; same version with different deployed files is refused. Candidate rebuild is not an excuse to silently overwrite an existing release version. Official version numbers do not participate in Neighbor ordering. Existing config entry remains, no repeated discovery. HACS-owned code is not overwritten: explicit supported ownership transfer first; MANUAL_UNKNOWN refuses writes until source and user intent are safely established. No unstable HACS private API.

## Recovery contract

- REVERSIBLE: deployment-only file/owner changes with verified backup and health rollback, including fresh install back to absent code; preserve original entry and references.
- FORWARD_ONLY_BUT_COMPATIBLE: additive semantic migration that retains legacy identity and references; code rollback does not automatically erase registry changes.
- RECOVERY_REQUIRED: unknown/partial ownership, registry/schema mutation that cannot be proven reversible, failed restore, concurrent modification or unexpected identity churn. Stop, retain journal/baseline, recover using supported HA backup/snapshot procedures; never claim code rollback equals full HA state rollback.

No release promotion until the Stage E gates and subsequent explicit release authorization. Longer real observation, license clearance, image/signature distribution infrastructure and untested platforms remain explicit release conditions.
