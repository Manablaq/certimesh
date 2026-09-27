# Bradbury verification runbook

Bradbury verification is a post-Direct-Mode release gate. The frozen commit
must be deployed exactly as tested; source, ABI, dependency lock, and runtime
manifest hashes must be recorded before deployment.

The live campaign must cover:

1. compliant evidence -> `CERTIFIED`
2. noncompliant evidence -> `REJECTED`
3. conflicting/unavailable evidence -> `REPAIR`
4. challenge -> fresh generation -> reassessment -> finalization

For every case record network, chain id, contract address, contract source hash,
deployment transaction, method/input commitments, GenLayer transaction id,
final status, execution result, final state, raw response hash, timestamp, and
Git commit. `ACCEPTED` alone is not proof; require `FINALIZED` and
`FINISHED_WITH_RETURN`.

Never use `--leader-only` as proof. If a live write returns a transaction id,
poll it instead of resubmitting.

## Current release record

The current frozen source and compact transport artifact pass the local release
gates, Direct Mode, and GenVM validation. Bradbury read-only gas estimation
accepts the payload, but the GenLayer CLI deployment request is rejected before
consensus acceptance with `gas limit too high`. Therefore this repository does
not claim a deployed CertiMesh address or positive on-chain contract evidence.
The exact source/artifact hashes, RPC estimate, rejected request hash, and
negative evidence status are recorded in
[`verification/bradbury/deployment-evidence.json`](../verification/bradbury/deployment-evidence.json).
