# CertiMesh R1 security model

## Enforced invariants

- Program versions are write-once and assessments retain their exact version.
- Only the program creator can create later versions or retire a version.
- Two distinct authorities are required; sender and role are checked on-chain.
- Record ids and immutable source references cannot be duplicated in a generation.
- A program/version/subject-digest commitment cannot be submitted twice; reassessment
  uses the explicit fresh-generation path after repair or challenge.
- Publication/observation freshness and expiry are checked at attestation, bind,
  and review time.
- The authority-supplied payload digest must equal the committed source-content
  digest; validators then recompute the digest from fetched bytes.
- Subject digest, evidence-set digest, timestamps, and decision nonce are bound
  into a deterministic certificate identity.
- `CERTIFIED` and `REJECTED` are provisional until finalization; `REPAIR`,
  `CHALLENGED`, and `EXPIRED` cannot finalize directly.
- Finalization is single-use and certificate digests are replay-protected.
- There is no owner/admin method that can set a decision or certificate.
- Evidence is untrusted prompt data; it is never treated as protocol instructions.

## Threats rejected

The contract rejects one-source certification, same-authority corroboration,
stale or expired sources, source hash mismatch, payload/source digest mismatch,
wrong generation, duplicate assessment commitments, duplicate evidence, future
timestamps, challenge-after-deadline, finalization-before-deadline, short
deadlines that cannot leave a challenge window, second finalization, and
validator disagreement.

## Operational rule

Every live write must save its transaction id immediately and poll that exact
id until `FINALIZED` with successful execution. A timeout after an id exists is
not permission to blindly retry.
