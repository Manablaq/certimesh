# CertiMesh R1

CertiMesh is a reusable, evidence-bound certification protocol for GenLayer.
R1 creates immutable certification-program versions, binds a subject digest and
two independent authority attestations, performs independent validator review,
and issues deterministic certificates only after an uncontested finalization
window.

R1 intentionally does **not** custody tokens, implement staking, marketplace
economics, reputation, a frontend, or administrator verdict overrides.

## Security boundary

The contract accepts only these consequential outcomes:

```text
CERTIFIED | REJECTED | REPAIR
```

The leader and every validator independently retrieve the exact bound HTTPS
evidence, verify that the fetched bytes match both committed hashes, and derive
the same decision. Evidence is framed as untrusted data in the prompt and
cannot change the protocol criteria. Storage writes occur only after consensus
returns.

`CERTIFIED` becomes `PROVISIONAL`; it is not a certificate until the challenge
window closes. A challenge forces a fresh evidence generation. `REPAIR` never
creates a certificate. An expired assessment is terminal and cannot be revived.

## Repository gates

```text
contracts/certimesh_registry.py      deterministic registry and settlement contract
contracts/certimesh_registry_deploy.py generated compact registry artifact
contracts/certimesh_program_registry.py immutable program/version registry
contracts/certimesh_program_registry_deploy.py generated compact program artifact
contracts/certimesh_evidence_registry.py isolated evidence attestation/binding registry
contracts/certimesh_evidence_registry_deploy.py generated compact evidence artifact
contracts/certimesh_adjudicator.py  isolated nondeterministic review contract
contracts/certimesh_adjudicator_deploy.py generated compact adjudicator artifact
contracts/certimesh_core.py          legacy monolith retained only for regression comparison
tests/test_certimesh_direct.py       adversarial Direct Mode suite
verification/supported_runtime/      multi-validator evidence package location
verification/bradbury/               live network evidence and blockers
scripts/check_release.py             source and forbidden-surface gate
scripts/build_registry_artifact.py   ABI-preserving registry artifact builder
scripts/build_program_registry_artifact.py ABI-preserving program artifact builder
scripts/build_evidence_registry_artifact.py ABI-preserving evidence artifact builder
scripts/build_adjudicator_artifact.py ABI-preserving adjudicator artifact builder
scripts/check_supported_runtime_bundle.py  runtime bundle gate
docs/ARCHITECTURE.md                 storage and flow
docs/API.md                          write/view API
docs/SECURITY.md                     threat model and invariants
docs/BRADBURY_VERIFICATION.md        frozen-release live procedure
```

Run from a Python 3.12.14 environment with `requirements-lock.txt` installed:

```bash
python scripts/check_release.py
python scripts/check_supported_runtime_bundle.py
python scripts/build_registry_artifact.py
python scripts/build_adjudicator_artifact.py
gltest --contracts-dir contracts tests
```

`gltest --leader-only` is never a certification proof and is not used by the
release checks. Bradbury deployment is deliberately a later gate after Direct
Mode and full multi-validator testing pass. Deploy the Program Registry first,
then the Assessment Registry with its address, then the Evidence Registry with
both registry addresses, and finally the Adjudicator with the Assessment
Registry address. The Assessment Registry owner must bind the Evidence Registry
and Adjudicator exactly once; each binding requires a reciprocal address check.
No verdict or certificate authority is granted to the deployer by those wiring
operations.

When using the GenLayer CLI, pass constructor addresses as `addr#` followed by
the 40 hexadecimal characters **without** a second `0x` prefix, for example
`addr#24f92ca9C42cC3E093cE6a1D0F2B9a2B474D66A7`. Run deployments and writes
sequentially because Bradbury accounts cannot safely submit nonce-conflicting
transactions in parallel. The CLI success banner is not release evidence:
accept a deployment only after the RPC receipt reports `FINALIZED` and
`FINISHED_WITH_RETURN`; reject `FINISHED_WITH_ERROR` even when consensus says
`ACCEPTED`.

For Bradbury state-changing writes, also verify the EVM wrapper receipt before
waiting on GenLayer consensus. The CLI can under-estimate the wrapper gas for a
write and produce a reverted EVM transaction with no GenLayer transaction at
all. If the wrapper receipt is `status: 0x0` and contains no `NewTransaction`
event, do not submit a new logical action: preserve the original calldata,
nonce, and target, then resend that same calldata sequentially with an explicit
gas ceiling above the current `eth_estimateGas` result. Only the emitted
`NewTransaction` id may then be tracked toward `FINALIZED` and
`FINISHED_WITH_RETURN`.
