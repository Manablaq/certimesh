# CertiMesh security review — 2026-10-03

## Scope

This is an internal adversarial code review of the split CertiMesh protocol:

- `contracts/certimesh_program_registry.py`
- `contracts/certimesh_registry.py`
- `contracts/certimesh_evidence_registry.py`
- `contracts/certimesh_adjudicator.py`
- the direct-VM tests and release gates

The review covers authorization, write-once commitments, state transitions,
cross-contract binding, evidence integrity, retry behavior, model-output
validation, replay protection, and generated deployment-artifact equivalence.
It is not a third-party penetration test, formal verification report, or legal
security certification.

## Finding resolved

### CM-001 — duplicate retry dispatches could be spammed

**Severity:** Medium operational risk

Before this review, `retry_assessment` accepted repeated calls while an
assessment remained `EVIDENCE_BOUND`. Each call emitted another adjudication
request for the same generation and evidence hash. This could create duplicate
work, confusing frontend state, and unnecessary transaction cost before the
first retry reached a terminal callback.

**Resolution:** the Registry now stores `last_retry_at`, rejects another retry
until a 1,800-second cooldown elapses, exposes `retry_available_at` through the
assessment context, and clears the timer when a new repair generation opens.
The initial adjudication dispatch also starts the same timer, so a requester
cannot immediately add a second dispatch before the first callback resolves.
The regression tests prove both that immediate duplicate paths are rejected
and that a retry after the cooldown is accepted.

## Controls verified

- Program versions are write-once; terms and authority addresses are snapshotted.
- Program creation requires two non-zero, distinct authorities.
- Registry/Evidence Registry/Adjudicator bindings are reciprocal and one-shot.
- Assessment commitments prevent duplicate subject commitments for the same
  program version and subject digest.
- Evidence is role-bound, HTTPS/IPFS-reference constrained, freshness checked,
  expiry checked, hash checked, and duplicate record/source checked.
- Evidence binding requires the requester and exactly two distinct authorities,
  record IDs, and immutable source references.
- Adjudicator requests are Registry-only and keyed by assessment, generation,
  and evidence-set hash for replay-safe cached results.
- Validator output is required to be an exact JSON object with a supported
  decision and matching request metadata.
- Registry callbacks are Adjudicator-only and must match the bound generation
  and evidence-set hash.
- Provisional results cannot be finalized before the challenge window closes;
  challenged, repair, expired, and already-finalized paths are gated.
- Certificate digests include the assessment, evidence set, decision, times,
  and a monotonic decision nonce; used digests cannot be replayed.
- No owner/admin verdict override exists in the reviewed contracts.
- The generated Registry deployment source passed the reversible executable-AST
  equivalence check against the canonical source.

## Verification evidence

Executed in a fresh pinned virtual environment:

```text
19 passed in 0.34s
CERTIMESH_RELEASE_GATE=PASS
FAIL supported-runtime evidence package is incomplete
PASS deployment artifact is executable-AST equivalent
git diff --check: clean
```

The release gate and tests are necessary controls; they are not a substitute
for a third-party audit.

## Multi-validator evidence status

The repository intentionally does not contain fabricated validator logs. The
real Bradbury runtime campaign was attempted with the full `gltest` mode and
stopped before executing tests because no `gltest.config.yaml` accounts were
configured. The campaign requires temporary, funded Bradbury test accounts and
must persist raw leader and validator outputs, exact command/network metadata,
and hashes of those artifacts. No private key is stored in this repository.

Therefore the supported-runtime package is **not complete**. The release gate
only confirms that the package has the required documentation and is ready to
receive a real campaign; it does not claim that a multi-validator campaign has
run.

## Residual risk / required external assurance

The code review found no unresolved high-severity issue in the reviewed scope
after CM-001 was fixed, but this cannot establish that the system has no
weaknesses. Production submission should still obtain an independent security
review and run the multi-validator Bradbury campaign with controlled test
accounts before treating CertiMesh as externally audited or production-ready.
