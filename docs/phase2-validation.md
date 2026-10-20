# Phase 2 Stage A validation — 2026-10-21

Stage A stop condition met on disposable VM201. No production changes, real Hub
discovery, config-entry creation or device commands. This is not rollout approval.

## A. Architecture

Separate `neighbor_installer` package: capability/owner detection, pinned artifact
verification, backup and atomic directory staging, durable transaction, lifecycle,
health, explicit rollback/recovery, privacy-safe CLI. Exclusive owner enum is
OFFICIAL_HACS / COMMUNITY_HACS / NEIGHBOR_INSTALLER / MANUAL_UNKNOWN. No-HACS
fresh installation establishes NEIGHBOR_INSTALLER. HACS ownership blocks writes.

## B. User flow

Working HA → trusted local installer → inspect ownership → confirm version/restart
→ verified backup/deploy → restart → health success or original-code restoration.
Current entry point is an engineering CLI/authorized companion; no novice launcher
or permanent automatic updater is claimed. NSDP configuration is a later operation.

## C. Code

Branch: `phase2/existing-ha-installer`, created from `24eb40c5a8a0b931aa350eeddd508e47cbb5c325`.
Core implementation: `9137cf3a5dc19cb9f2c6cb386d8133f51ee3e952`.
Rollback-point and entry-data guard hardening: `989f472` (full hash recorded by Git).
Final documentation/test commit and clean status are recorded in Work final-state evidence.
Repository remains PRIVATE; only this development branch is pushed. No merge/release.
All 23 integration deployment files are unchanged from field-tested `f9bbf3...`.

## D. Tests

* Phase 1 regression suite: **122 passed**.
* Phase 2 installer suite: **53 passed**, isolated filesystem/runtime fixtures.
* Ruff: passed for installer, tests and existing integration.

Coverage includes all four owners, absence, unknown/conflicting HACS metadata,
manual confirmation/backup, idempotency, pinned source/tampering, HA-version gate,
identity/data preservation, failed health, rollback to absence, partial staging and
interrupted directory swap, pending/stale transaction recovery, lock exclusion,
concurrent edits, backup tampering, token separation and redirect refusal.

## E. Actual VM201 tests

Restored `FreshHAOS-BeforeNEXhomeCandidate`, HA OS18.3/Core2026.10.2. No HACS and
no NEXhome directory/entry at start. The installer ran outside Core in an ephemeral
companion using the already-installed official Core image. Core restarts did not
terminate the engine. No add-on or new runtime image was installed.

| Test | Actual result |
|---|---|
| A fresh installation | COMMITTED; dev3, 23 exact file hashes, healthy, handler visible |
| B repeated invocation | NO_OP; no second installation/restart |
| C same version | NO_OP |
| Additional fresh rollback | ROLLED_BACK to absent directory/handler, healthy, identity unchanged |
| D old Community dev2 → dev3 | COMMITTED, original code backup verified |
| E deliberately failed first health check | ROLLED_BACK to dev3, healthy, identity unchanged |
| Final hardened engine | Same-version NO_OP plus separate successful runtime probe |
| Actual browser UI | Add Integration search shows “NEXhome Community Candidate” |

E uses a clearly labelled local fixture (manifest version dev4, fixture origin),
not a real Candidate release. It injects a failed health result; actual syntax-broken
code was not deployed. All normal integration files are from pinned private Git commits.
Final hardening after the initial VM matrix was exercised by the complete offline
suite and an actual VM no-op/probe; the destructive matrix was not repeated.

The lab transport lost a guest-exec PID while collecting E results, revoking its
temporary HA token before the final report probe (401). The transaction journal
already showed ROLLED_BACK/identity unchanged. Fixed the lab poller, verified there
was no remaining companion, and ran a new read-only probe successfully. No device
test or failed transaction was repeated to conceal this harness issue.

Final VM201: running, Core/Supervisor healthy, dev3 installed, owner
NEIGHBOR_INSTALLER, HACS absent, NEXhome entries0 / active0, last transaction
ROLLED_BACK (terminal). Temporary companion, staged lab code/artifacts and token
env file removed. Local installer journals/backups retained for recovery. Fresh
snapshot retained; no active-entry snapshot was restored.

## F. HACS/source boundaries

No-HACS path was actually tested. Official/community HACS, conflicting owners,
unknown schemas and manual adoption were exercised only with fixtures. There was
no actual HACS install, source transfer or production migration. Unknown metadata
fails closed; HACS storage compatibility across versions remains unverified.

## G. Identity preservation

Loaded and user-disabled fixture entries preserve entry ID/data, registry IDs,
device identity, user rename/hide/Area, Dashboard and automation/group/config files.
Only identity digests are recorded; raw registries/config data are not backed up.
Actual VM tests preserve a zero-entry baseline, not an existing live installation.
Existing official→Community runtime migration remains a separate gate. A registry
mutation cannot be automatically undone by code backup; the engine restores code
and reports RECOVERY_REQUIRED rather than claiming a full identity repair.

## H. Security/privacy

Local-only, no telemetry, no password/token/SN in reports or Git. Manifest SHA pin
must come through a trusted channel; SHA alongside an untrusted bundle is not
source authentication. Bounded regular-file trees, symlink refusal, explicit HA
version matrix, local lock and durable journals. Separate HA/Supervisor credentials
via environment; no authenticated redirects. Temporary lab tokens were revoked
and env file deleted. The pre-existing disposable VM admin secret remains in its
authorized private local file until VM destruction; it was never copied to Git.

## I. Remaining blockers/risks

No production authorization. No real existing-install/HACS migration, HA Container
lifecycle, other HA versions, hard disk loss recovery, signed distribution or novice
launcher certification. Fingerprints do not exhaustively cover arbitrary YAML includes.
No automatic registry rollback. The installer requires explicitly granted local
filesystem/lifecycle access; ordinary HA REST API alone is not a deployment channel.
Backups may contain old hardcoded integration secrets and must stay private locally.

## J. Recommendation

Accept Stage A for the stated Fresh/no-HACS engineering gate and stop. Before any
neighbor or production use, separately authorize review and an existing-install
migration fixture/lab gate plus supported launcher/security packaging. Do not start
Phase3 or production rollout automatically.
