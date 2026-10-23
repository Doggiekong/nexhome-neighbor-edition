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

E4 production handoff committed on 2026-10-23 using the identical frozen packet. Before source release, scoped source/registry/reference backup, official HA homeassistant-folder backup and a PVE disk snapshot were preserved. The original locally patched tree correctly failed HACS source/hash ownership detection. After explicit user approval, supported HACS Remove (ignoring its configured-entry advisory without deleting the HA entry) released the official source, then the reviewed installer transfer committed. No trusted hash was fabricated and no HACS private API/storage edit was used. This maintainer-reviewed patched-source handoff must not be represented as an unattended ordinary-user unknown-source overwrite.

Production now reports 0.1.0 / NEIGHBOR_INSTALLER, all 25 file hashes match, HACS claim count is zero, and the same sole entry is enabled/loaded. Core/Supervisor are healthy. The entire inspected entity registry baseline (88 entities), device baseline (86 devices), and ten reference-file hashes match exactly. Original entry data is unchanged except additive identity_mode=compat; minor_version advances from 1 to 2. Existing 47 integration-hidden markers and 86 device Area assignments survive. There are no additional semantic entities.

Read-only postflight found zero unavailable, six honest unknown positionless covers, no pending properties, no transport errors/timeouts, and successful last update. The production UI displays version 0.1.0, 86 devices and 88 entities; the existing family dashboard renders. VM201's synthetic entry remains user-disabled; VM400's reference container remains stopped. An eight-second passive traffic sample showed production communication and zero VM201 traffic.

The user is temporarily unavailable and expressly requested checks without device actions. No production device command was issued after migration. Production light/dimmer/cover/climate and wall-control confirmation are deferred; completion remains CONFIGURED with control_readback_verified=false. E4 is therefore only partially verified. E5 is recorded only for its actual observation window; E6 final readiness remains pending. Do not repeat E2 controls or E3 transactions on resume.

Rollback classification is FORWARD_ONLY_BUT_COMPATIBLE: code rollback alone cannot promise reversal of additive config-entry schema or external HACS source release. Preserve original backups and report RECOVERY_REQUIRED when full safe recovery cannot be proven.

One non-blocking Terminal copy issue was observed: a successful same-version READY check still appends generic “component deployed; finish connection” guidance. The runtime/control result is correct; the frozen packet has not been silently changed. Record this in final Manual/UI accuracy assessment or fix in a separately identified Candidate with affected gates repeated.

Public redistribution remains blocked pending upstream license clarification. Mobile hardware, voice platforms, remote access changes, deliberate real Hub failure and long-run production observation have not been validated by this checkpoint. See `release-distribution.md` and root `NOTICE.md`.

## Production read-only continuation

At the user's request, production field commands remain deferred. The full offline suite was actually rerun during this continuation: 287 PASS in 9.24s (129 runtime, 103 installer, 55 launcher), and Ruff PASS. This is a new execution, not a copied historical result; runtime/SDK and the frozen deployment packet remain unchanged. The first temporary process-sampling attempt did not execute because its shell wrapper used CRLF; it provides no valid observation time. Only subsequent successful, timestamped samples may be used as observation evidence.

A successful supplementary read-only observation ran from 2026-10-23 20:37:10 to 20:52:10 UTC+8 (900.08s, 16 samples approximately 60s apart). Core threads remained 19 at every sample, SyncWorker names 12, gateway TCP/ESTABLISHED connections 0–1; RSS ranged 556,437,504–558,239,744 bytes. No sustained thread/connection growth was observed in this window; transient peaks between samples and long-run leaks are not excluded. Final postflight remained healthy/loaded, zero unavailable/six expected unknown, exact identity/reference validation. Cumulative transport counters were 18,395 requests, zero errors/timeouts; these are not a 15-minute request delta. No device commands were sent. The installer App is stopped, Core integration remains enabled, temporary transfer/diagnostic scripts are closed/removed, and backups/journals are retained. Formal E4 physical confirmation and subsequent E5/E6 gates remain pending; no release-candidate-ready claim is made.
