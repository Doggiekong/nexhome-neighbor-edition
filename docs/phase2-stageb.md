# Phase 2 Stage B — existing installation and identity preservation

Completed in the disposable lab, not production. Stage C remains unstarted.

## A. Strategy and identity model

USER INTENT WINS. Keep the existing config entry, registry identities and legacy
switches. Add a semantic light/fan only with an explicit per-object approval tied
to the exact legacy entity_id, and only without conflicting user customization.
HA does not provide trustworthy entity_id-edit history: absence of evidence is
not permission. Unknown/unproven rows are conservative skips. This deliberately
tightens dev3's automatic untouched-legacy policy.

Runtime `1.1.17.dev4` changes only migration.py, version constant and manifest from
the field-tested dev3 runtime. No new physical-device field verification is claimed.
Transport, scheduler and light/climate/cover control implementation are unchanged.

`neighbor_installer.identity` captures a machine-readable baseline: entry ID,
domain/unique ID/title/disabled/schema, hashes of individual stored data values and
options, entity registry ID/entity_id/unique_id/platform/original and user name,
hidden/disabled/Area/device/aliases/labels, device IDs/identifiers/entry relations,
and hashes of top-level automation/group/config plus Dashboard/Area storage.
Raw credentials/SN are not copied into it. Baselines/journals are private local files.

An optional explicit migration preview allows only known additive entry metadata
(`identity_mode=compat`, same-SN alias, minor1→2), approved semantic additions on
the same physical device, and a proven integration-owned hide. All original
identities, user metadata and references must remain. Unexpected mutation stops
or enters RECOVERY_REQUIRED. No registry deletion/rebuild/automatic template scan.

Live entity/device registries are read using supported HA WebSocket APIs, including
`get_entries` because `list` is partial. Reads are bounded and redirects refused.
This avoids Store's delayed disk persistence. Device storage v3's config_entry_id
is recognized; missing linked devices fail closed. The detailed API's computed-name
alias `null` is normalized out of the user alias set; real alias strings remain
strictly protected. Unknown detailed schemas fail closed.

## B. Composite fixture and test coverage

The same installation contains untouched, manual light/fan wrapper, user-hidden,
integration-owned-hidden, renamed, entity_id-only edited, Area-assigned, user-disabled,
manual metadata and unproven legacy rows. It contains legacy automation/group and
stored Dashboard references. Only explicitly approved untouched rows migrate;
the compatibility switch remains usable under its old identity.

| Cases | Isolated HA/filesystem fixtures | Actual VM201 |
|---|---|---|
| B1 official1.1.16 existing entry/registry | Additive schema/identity contract | Exact official Git bfcc161… installed, normal official config flow against fake gateway |
| B2 old Community/installer existing entry | dev2-like→current fixture; loaded/disabled preservation | Stage A old-version result is historical, not rerun here |
| B3–B7 rename/entity_id/hidden/owned marker/Area | Composite repeated with minor1 and minor2 | One composite fixture, original IDs preserved |
| B8 automation references | Exact byte/reference preservation | Loaded disabled automation, never triggered |
| B9 group/Dashboard references | Preserved | Loaded group and stored Dashboard config; no UI playback/click claim |
| B10 unavailable/stale entry | Stop diagnosis, no discovery/delete/recreate | No real Hub repair attempted |
| B11 MANUAL_UNKNOWN | Refuse without exact explicit adoption | Actual default refusal, backup, then explicit fixture fingerprint confirmation |
| B12 interrupted/partial migration | Directory, activation and semantic-marker interruption recovery | Successful lifecycle only; no additional fault injection |

All sixteen requested tests are represented by the above suites. The high-priority
composite is mandatory and passed both isolated actual HA registries and VM201.
No claim that every HA variant, model or wrapper convention was exhaustively tested.

## C. Identity results

Actual VM baseline: one existing entry, 11 NEXhome entities (10 legacy plus one
pre-existing owned semantic), 10 devices, two genuine switch-as-X helpers. After:
the same entry ID; all 11 original registry IDs/entity IDs/unique IDs/device IDs
and metadata retained; one approved semantic light added, total12. The untouched
legacy switch changes hidden_by from none to integration with its ownership marker.
User-hidden/disabled/rename/Area/entity_id-only rows and both wrappers remain.
No semantic duplicate for skipped objects. No devices recreated. Automation/group/
stored Dashboard references have identical hashes. Reload remains12/10/two wrappers.

HA2026.10 switch-as-X stores links in options; both current options and older data
are recognized. Integration-owned hidden is never inferred merely from hidden_by.
Marker ownership plus the exact semantic identity must exist. User hide/disable
and explicit wrappers override migration. Marker persistence precedes hiding;
interruption after hiding can resume with the same semantic identity, not a duplicate.

## D/E. Unknown source and unavailable entry

Unknown source/hash/owner defaults to refusal. Read-only inspection and private
code backup are allowed; adoption needs an explicit exact current fingerprint,
and HACS claims still block it. Official code in this lab was deliberately a
manual install, not OFFICIAL_HACS. No channel ownership transfer was performed.

Failed/retrying entries are preserved and require diagnosis. A failed setup does
not prove stale endpoint, network failure or invalid SN. No automated repair,
discovery or replacement is invoked. Future confirmed repair must update the
existing entry, not create a replacement. Malformed/future schemas stop safely.

## F. Rollback/recovery categories

* REVERSIBLE: code-only change with unchanged identity/schema; code backup/stop/
  restore/start/health can fully restore the checked scope.
* FORWARD_ONLY_BUT_COMPATIBLE: additive schema/semantic metadata with preserved
  original identities and references. A successful migration can commit.
* RECOVERY_REQUIRED: after a failed migration, code can be restored but additive
  registry/schema changes are not automatically erased; or an unexpected identity
  mutation/unsafe recovery input prevents a verified restoration. Preserve evidence,
  never guess, delete entities or claim automatic registry rollback.

The actual official→dev4 migration is forward-only but compatible. Fault/interruption
and RECOVERY_REQUIRED boundaries were tested in isolated fixtures, not by breaking
the production HA or repeatedly mutating VM201. No private registry rollback API.

## G. Tests actually run this stage

* Runtime full suite: **127 passed**, original122 plus five Stage B tests.
* Installer full suite: **74 passed**, original Stage A53 plus21 Stage B tests.
* Ruff passed. Historical Stage A VM A–E results were not rerun or relabelled.

Composite tests use actual HA registries and repeated setup/reload. Additional tests
protect cache-only mutations, device-storage-v3 detection, missing schemas, user
aliases versus computed sentinel, explicit preview staleness, reference mutation,
unknown sources, stale entries, interruption, full rollback and partial recovery.

## H/I. VM201 and production safety

VM201 used exact official v1.1.16, normal config flow, internal synthetic HTTP
gateway, supported HA metadata APIs and clearly scoped offline fixture seeding
while Core stopped. No VM200 data, backup, registry or real household identity was
copied. No Hub discovery, real-device control, production disable or production restart.
Fake gateway forbids commands and recorded zero attempted commands.

Migration used Candidate runtime commit ec3ca097d976409d86644a32cdd1e6a5b3638f82.
The first coarse on-disk audit was insufficient: delayed registry persistence and
the newer device-storage schema were found during independent API comparison.
The original transaction was not edited. Final installer hardening reads live
detailed registries and fails closed; an augmented audit uses the original PRE-
migration public API baseline plus original transaction's data/reference digests.
It passed for all11→12 entities and all10 devices. Alias-format mismatches were
initially refused, then normalized only for HA's documented computed sentinel.
Full migration was not repeated after this guard hardening; final guards have the
complete offline suite and an actual successful live-API audit, not a second
end-to-end write/restart claim. This is a remaining validation granularity limit.

Final VM201: dev4 installed, healthy, same synthetic entry retained user-disabled/
not_loaded, active0. Fake/companion containers, temporary code/artifacts and token
files removed. Synthetic registry/customization/references and local transaction
backups remain for inspection. Snapshot StageB-BeforeExistingFixture retained;
Fresh baseline also remains. Production VM200 unchanged and Observer healthy.

## J/K/L. Git, limits and recommendation

Private branch phase2/existing-ha-installer; logical implementation commits be23631
and ec3ca09 plus cache-safe identity hardening and this report. Final full HEAD and
clean/pushed status are in Work current-state. No main merge, Release/public/HACS
publication, production migration, launcher or Stage C work.

Not verified: real Hub migration, actual HACS transfer, all manual template/wrapper
patterns, other HA versions/platforms, automatic reverse registry/schema migration,
or production suitability. Unknown objects remain unchanged rather than guessed.
Only recommend separately authorizing **Phase 2 Stage C — HACS & Update Ownership**.
Do not proceed automatically.
