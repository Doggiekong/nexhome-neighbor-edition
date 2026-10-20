# Phase 2 Stage A — existing HA installer core

Scope: an already working HA; no HA installation, platform provisioning, discovery,
device commands, production rollout, HACS publication or background auto-update.
Runtime integration remains the 23-file Candidate `1.1.17.dev3`, field-tested at
`f9bbf3afcc711d23b9a7484156ca5d75c8d30d24`; Phase 1 documentation baseline
`24eb40c5a8a0b931aa350eeddd508e47cbb5c325` has identical runtime files.

## Modules and trust boundaries

`neighbor_installer` is a separate Linux/Python package, not a HA integration runtime
dependency. `environment` reports capabilities; `detection` classifies ownership;
`artifact` verifies a trusted manifest SHA256, exact payload inventory, domain/version,
Python syntax and tested HA matrix; `files` provides bounded regular-file operations,
exclusive flock and durable journals; `engine` coordinates transactions; `lifecycle`
controls HA through an explicitly authorized external runtime adapter; `__main__`
is a minimal local CLI. `build` packages an explicitly pinned Git commit offline.

Source origin is restricted to the private Community repository or an explicitly
labelled local test fixture. A SHA256 received alongside an untrusted download is
**not authentication**: the launcher must obtain its expected manifest pin through a
trusted channel. Signed release manifests remain future work. No downloads or
telemetry are implemented. Source commit does not prove a public release exists.

## Exclusive ownership

| Detected state | Result / permitted action |
|---|---|
| No code, no marker, no HACS claim | Install; becomes NEIGHBOR_INSTALLER |
| OFFICIAL_HACS | Diagnose/backup only; refuse installer writes |
| COMMUNITY_HACS | Diagnose/backup only; HACS remains sole updater |
| NEIGHBOR_INSTALLER marker + exact tree hashes | Same tree no-op; newer version transactional upgrade |
| MANUAL_UNKNOWN / conflicting claims / changed tree | No automatic overwrite; backup and report |
| Existing normal entry | Preserve entry; no creation, deletion, repair or discovery |
| Existing failed/retrying/migrating entry | Stop for explicit diagnosis; no automatic discovery |

Manual adoption requires explicit confirmation of the **current exact tree fingerprint**;
HACS claims or unknown HACS metadata still block adoption. Same-version changed code
and downgrades are refused. CLI diagnose reads metadata but never outputs entry data,
SN, endpoint, passwords or entity states. Ownership marker is an operational convention,
not a cryptographic defense against a privileged local administrator.

HACS storage is private implementation detail. The current read-only fixture adapter
recognizes dictionary repository records containing installed/domain/full_name, and
requires a separately trusted tree fingerprint to assert HACS ownership. Unknown
schema, unverified tree or conflicting marker => MANUAL_UNKNOWN and **no write**.
This is safe detection, not broad HACS-version compatibility certification. Stage A
does not install HACS or modify its metadata. A future source transfer must use
supported HACS UI/user actions; no private write API or source-switch hacks.

## Transaction / recovery

One nonblocking OS lock covers mutation; a crashed process releases its lock, but an
unfinished journal blocks another apply until explicit `recover`.

PRECHECK → BACKUP → DEPLOY → ACTIVATE → HEALTH_CHECK → COMMITTED.
Failures after deployment: FAIL → ROLLBACK (stop failed runtime) → RESTORE →
health check → ROLLED_BACK. Interrupted PRECHECK/BACKUP has no deployment to undo.
Every operation has a UUID and durable record under `.nexhome-installer/transactions`.
Backups include the integration regular files, exact hashes, manifest/source/owner,
entry-state baseline, identity digest and transaction metadata. They do not include
the full HA configuration, database or registry content. Backups/state are mode700,
files600. Integration backups can contain credentials hardcoded by prior users;
they are local sensitive material, never uploaded or printed.

Deployment stages a verified tree on the same filesystem, renames old and new
directories and journals progress. A crash between the two renames is recovered
from the verified backup. Partial staged files must be a matching subset of expected
files; changed/unrecognized files stop recovery before Core is stopped. Directory
rename is not a single atomic exchange; recovery depends on intact local storage.
File data and JSON records are fsynced, but catastrophic disk loss/power-loss filesystem
corruption cannot be guaranteed recoverable without an external backup.

Rollback restores code/owner or original absence, starts Core, verifies handler
visibility and exact pre-existing entry states, and rechecks identity digest. No
registry edits, state fabrication or entity recreation occur. A migration that
changes registry metadata cannot be undone by code backup alone: code is restored,
then RECOVERY_REQUIRED is reported if identity differs. Full existing-install
migration needs a separate test/checkpoint before production approval.

## User flow and launchers

For a neighbor: open trusted installer → inspect HA/update owner → confirm version
and restart → local backup/install → HA restarts → health passes or original code
is restored → only then separately configure the integration. This Stage A stops
before configuration/discovery and does not quietly create a Hub client.

| Entry point | HA OS | HA Container | Stage A decision |
|---|---|---|---|
| HACS custom repository | Available after HACS setup | Same | Supported installation channel, sole writer; migration not implemented |
| Temporary installer add-on | Suitable managed config mount + Supervisor lifecycle | No Supervisor/add-ons | Promising future simple launcher, not shipped here |
| Shell/bootstrap | Requires authorized filesystem access | Host config mount + container control | Engine usable; not yet a novice product |
| External HA API launcher | HA API alone cannot write integration files | Same | Needs separate authorized writer/lifecycle adapter |
| Manual copy | Possible with file access and restart | Host bind mount and restart | Documented fallback; ownership initially unknown |

The official REST API exposes configuration/entries/states/services, not a general
custom_components file deployment endpoint. This is also consistent with local
HA2026.10.2 route inspection. Supervisor API is a separate privileged boundary.
In this lab Supervisor `/core/api/...` returned401; the adapter uses a distinct HA
access token for ordinary HA API reads and Supervisor token only for lifecycle.
Authenticated redirects are refused. Credentials come from environment, not CLI
arguments; the launcher must keep/remove any temporary env file securely.

VM201 validation uses an ephemeral companion outside Core, based on the existing
official HA image, with an authorized config mount and network. The lab-only PVE/QGA
transport is **not** an installer platform adapter. The engine must survive Core
restart; executing it inside Core would not satisfy rollback requirements.

Example local CLI (inside an already authorized Linux companion):

```text
python -m neighbor_installer --config /config inspect
python -m neighbor_installer --config /config backup
python -m neighbor_installer --config /config apply --artifact /artifact --sha256 TRUSTED_MANIFEST_HASH
python -m neighbor_installer --config /config recover
python -m neighbor_installer --config /config rollback TRANSACTION_ID
```

No credential values go in those commands. Container lifecycle remains an injected
interface exercised offline; only Supervisor adapter is implemented and lab-tested
in Stage A. Native Windows execution is unsupported (POSIX locks/filesystem semantics).

## Preservation and safety gates

Fingerprints cover entry IDs/unique IDs/titles/options/disabled state, registry IDs,
renames/hidden/disabled/Area associations, device identities, Areas, Dashboard storage,
and top-level configuration/automation/group/script/scene files. Values are hashed
in memory, not copied into diagnostics. This catches changes; it does not repair
registries or exhaustively fingerprint every possible YAML include path.

Fixture tests cover loaded/disabled identity preservation, stale entry refusal,
all ownership states, failure rollback and interrupted transactions. Actual VM201
tests use **zero NEXhome entries**, so they prove code deployment/handler availability,
not live Hub setup or existing official migration. HACS source transfer, HA Container
runtime, other HA versions and novice launcher packaging remain subsequent gates.

References: [HA REST API](https://developers.home-assistant.io/docs/api/rest/),
[HACS integration repositories](https://www.hacs.dev/docs/use/repositories/type/integration/).
