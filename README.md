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
contracts/certimesh_core.py          one deployable product contract
tests/test_certimesh_direct.py       adversarial Direct Mode suite
verification/supported_runtime/      multi-validator evidence package location
scripts/check_release.py             source and forbidden-surface gate
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
gltest --contracts-dir contracts tests
```

`gltest --leader-only` is never a certification proof and is not used by the
release checks. Bradbury deployment is deliberately a later gate after Direct
Mode and full multi-validator testing pass.
