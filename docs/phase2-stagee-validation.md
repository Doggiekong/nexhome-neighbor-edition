# Phase 2 Stage E — internal Pilot checkpoint

Status: E0–E3 verified; E4 production migration has not started. This is not a Release or a completed Stage E assessment.

## Fixed Candidate

Product 0.1.0 / upstream 1.1.16 / artifact schema 2. Both App and Terminal used build `0.1.0-candidate-e1-20261022`, runtime and SDK source `c9246a1bce8fa087f2b590667d683fa1f47d4964`.

- Artifact manifest SHA-256: `f6102c029ee3c27f65beafc68a5cbf22639df2a3a2dc713e0131f84144e390e1`
- Archive SHA-256: `9c689161a068d840d1be66f88f1673fca2b5f4866a04b93237fe6b8b8679b093`
- Runtime: 25 files; packet Python sources: 42.

Later documentation commits do not change this frozen packet.

## E2 — HA OS App

The fixed App was installed/deployed through the HA UI. Before real Hub access, a disposable isolated fixture verified native confirmation, five entities, simulated ON/OFF with readback, READY, duplicate prevention, reload, Core restart, exact identity preservation and all 25 runtime hashes. The simulation was then removed without changing the Candidate.

The real fresh flow received one UDP1912 response after one broadcast from HA Core. No known Hub address or identity was entered into the flow. Native confirmation created one entry, 86 devices and 88 entities: 56 light, 1 fan, 12 cover, 16 climate and 3 sensor. No entity was unavailable; six covers without position feedback remained honestly unknown. A study light ON/OFF was read back and physically confirmed by the user. Reload and a Core restart preserved the same entry/entity/device identity fingerprint; explicit OFF after restart also read back correctly. READY was checked against the real entry.

The test entry was disabled before production was re-enabled. An eight-second passive sample then showed production traffic and zero VM201 traffic. VM201 was restored to its existing safe reference snapshot, with the original synthetic entry disabled, no App/lab, and healthy Core/Supervisor. No production code, registry or Core restart occurred in E2.

The previous longer disable interval was caused by external Work quota interruption and was subsequently recovered. It is retained as factual operational audit, not a Candidate defect, Hub failure or migration failure.

## E3 — Container Terminal

The identical archive was verified and used with the existing C0 reference container. Bootstrap ran in the fixed official HA 2026.10.2 image (Python 3.14.6); host Python 3.13.5 was not changed. A temporary restricted authorization file was revoked/deleted after each operation. Config remained owned by uid1000 with mode0700.

Actual checks: preview without deployment, explicit deployment/restart, native HA UI configuration of the isolated gateway, five expected entities, simulated ON/OFF readback, reload identity, READY, and same-version no-op (still one transaction). Ownership was NEIGHBOR_INSTALLER; schema2 and all 25 runtime hashes matched. Diagnostics were collected.

For rollback, the newly created disposable synthetic entry was explicitly removed through supported HA APIs first. The installer then restored absent code with `ROLLED_BACK` and unchanged identity. This does not claim that code rollback automatically removes entries created by a user after installation. Full fixture recovery used C0: exact archive/hash restoration, healthy HA check, no NEXhome/HACS entries, no pending transaction, cleanup and final stopped test container. All four original service container IDs, start times, states, ports and networks were unchanged; Docker networks and data-root were unchanged.

## Actual regression at this checkpoint

129 runtime + 103 installer + 55 launcher = **287 PASS**. Ruff PASS; 42 source files compiled; manifest/schema2 and frozen packet/archive hash validation PASS. This run was performed after E2/E3, not copied from the historical E1 result. Stage E added one frozen-package reproducibility test.

## Remaining gates and boundaries

E4 requires a fresh production identity/source/ownership/backup baseline before any code migration. E5 observation and E6 assessment remain unexecuted. The current browser extension UI is blocking production browser operations; the user has been asked to close it. No production migration was attempted while blocked. Do not repeat completed E2 physical commands or E3 transactions on resume.

One non-blocking Terminal copy issue was observed: a successful same-version READY check still appends generic “component deployed; finish connection” guidance. The runtime/control result is correct; the frozen packet has not been silently changed. Record this in final Manual/UI accuracy assessment or fix in a separately identified Candidate with affected gates repeated.

Public redistribution remains blocked pending upstream license clarification. Mobile hardware, voice platforms, remote access changes, deliberate real Hub failure and long-run production observation have not been validated by this checkpoint. See `release-distribution.md` and root `NOTICE.md`.
