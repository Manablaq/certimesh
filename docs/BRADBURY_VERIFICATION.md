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

The supported-runtime campaign requires three temporary, funded Bradbury test
accounts. Copy `gltest.config.example.yaml` to `gltest.config.yaml` and
`.env.example` to `.env`, fill only the local copies with those keys, and keep
both files out of Git. The exact full-validator command is:

```bash
gltest --network testnet_bradbury --chain-type testnet_bradbury \
  --contracts-dir contracts --artifacts-dir artifacts tests
```

Do not use `--leader-only`, and do not claim runtime evidence until raw
leader/validator outputs and their manifest hashes are committed under
`verification/supported_runtime/`.

There are two receipts to verify for a write. First verify the EVM wrapper
receipt: it must be successful and emit `NewTransaction`. A reverted wrapper
(`status: 0x0`) is not a GenLayer transaction and must not trigger a second
logical action. On Bradbury, the CLI may under-estimate wrapper gas; preserve
the exact calldata and resend it once, sequentially, with an explicit gas
ceiling above the current `eth_estimateGas` result. Then track only the
`NewTransaction` id and require its final receipt to be `FINALIZED` with
`FINISHED_WITH_RETURN`.

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

The superseding corrected redeployment is tracked separately in
[`verification/bradbury/corrected-run-20261003.json`](../verification/bradbury/corrected-run-20261003.json).
That record remains pending until the asynchronous adjudicator callback's
unchallenged challenge window closes and `finalize_assessment(1)` is read back;
the prior active record must not be used for the corrected retry-cooldown
release.

## Current validator-recomputation appeal run

The finalized split-stack validator-recomputation campaign is recorded in
[`verification/bradbury/validator-recomputation-run-20261005.json`](../verification/bradbury/validator-recomputation-run-20261005.json).
It records the corrected program registry, assessment registry, evidence
registry, and adjudicator deployments; finalized reciprocal bindings; two
finalized independent evidence attestations; the assessment dispatch and
callback; and the final `CERTIFIED` certificate after the challenge window.

The adjudicator result reached consensus `AGREE`, but the receipt records two
validator-local exceptions (`TIMEOUT` and `DETERMINISTIC_VIOLATION`) rather
than claiming identical outputs from all five validators. The supported-runtime
campaign was not run because no real three-account `gltest` configuration and
raw validator outputs were available; the release remains fail-closed and no
unsupported-runtime evidence is claimed.
