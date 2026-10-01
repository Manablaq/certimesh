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

The deployment record in
[`verification/bradbury/deployment-evidence.json`](../verification/bradbury/deployment-evidence.json)
is the source of truth. It must contain the active split-stack addresses and
only receipts that are both `FINALIZED` and `FINISHED_WITH_RETURN`. A CLI
success banner, an `ACCEPTED` transaction, or a trace with an execution error
is not sufficient evidence and must remain recorded as negative evidence.

The active deployment is intentionally recorded only after the sequential
deployment, reciprocal bindings, readback, and a fresh end-to-end assessment
have all been finalized. The external VerdictGraph UI is not part of this
repository; this repository contains the protocol contracts, artifacts, tests,
and release evidence only.
