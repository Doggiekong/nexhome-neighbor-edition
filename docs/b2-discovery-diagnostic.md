# B2 NSDP discovery diagnostic

dev2 rejects an otherwise valid NSDP response when MODEL contains an empty ampersand-delimited segment. In the controlled diagnostic, broadcast requests and responses reached the isolated test VM, but the Core parser rejected MODEL and the flow returned the `no_hubs` menu. This is a receiver/parser defect, independent of the earlier harness evidence gap.

dev3 skips empty MODEL segments only. Duplicate keys, malformed nonempty segments, missing/empty serials, invalid LOCATION and source mismatch remain rejected. No sender, socket, timeout, selection, authentication, polling or device command behavior changes. Temporary VM-only instrumentation is excluded from this commit.

Synthetic regression coverage includes leading, trailing, internal repeated and URL-encoded separators; negative identity/format cases; and the real config-flow/discovery chain with fake network packets. Raw household packets, addresses and identifiers are not committed.

Field validation is limited to B2 and stops before final confirmation submission. It does not validate device controls, active polling, migration, multi-Hub, VLAN or long-term operation. The private local Work evidence records the final deployment hash, actual flow result and passive network capture summaries; no full serial is logged or saved there.
