# CertiMesh R1 API

## Writes

### Program Registry (`CertiMeshProgramRegistry`)

```text
create_program(...) -> version
create_program_version(...) -> next_version
retire_program_version(program_id, version)
get_program(program_id, version)
get_program_snapshot(program_id, version)
get_latest_program_version(program_id)
```

### Assessment Registry (`CertiMeshRegistry`)

```text
create_assessment(program_id, version, subject_id, subject_digest,
  assessment_deadline) -> assessment_id
assess(assessment_id)
retry_assessment(assessment_id)        # requester-only, same bound evidence/generation
challenge_assessment(assessment_id, challenge_material)
open_repair_generation(assessment_id) -> generation
finalize_assessment(assessment_id)
expire_assessment(assessment_id)
bind_evidence_registry(evidence_registry_address)  # owner-only, one-shot wiring
bind_adjudicator(adjudicator_address)  # owner-only, one-shot wiring
record_assessment_result(...)          # adjudicator-only finalized callback
```

`assess` on the Registry starts the Adjudicator request. It does not accept a
client-supplied decision. `record_assessment_result` is an internal callback
surface and rejects every sender except the reciprocally bound Adjudicator.

`retry_assessment` is the recovery path for a finalized adjudicator dispatch
that ends in `NONDET_DISAGREE`, delivery failure, or another pre-callback
failure. It is requester-only and callable only while the assessment is
`EVIDENCE_BOUND`. It re-dispatches the exact same assessment id, generation,
and evidence-set hash; it cannot replace evidence, change the program, or
advance a verdict. The UI must enable it only after the failed child
transaction has been finalized, and must correlate the exact parent and
adjudicator child transactions before offering it.

### Adjudicator (`CertiMeshAdjudicator`)

```text
assess(assessment_id, generation, evidence_set_hash)  # Registry-only
```

### Evidence Registry (`CertiMeshEvidenceRegistry`)

```text
attest_evidence(assessment_id, generation, role, record_id, record_version,
  source_url, immutable_source_ref, evidence_payload_hash,
  source_content_hash, published_at, observed_at, expires_at)
bind_evidence(assessment_id)             # requester-only, one-shot per generation
get_bound_snapshot(assessment_id)
get_review_records(assessment_id, generation)
get_evidence(assessment_id, generation, role)
```

## Views

```text
get_program(program_id, version)
get_latest_program_version(program_id)
get_assessment(assessment_id)
get_certificate(assessment_id)
get_assessment_count()
get_evidence_registry_address()
get_adjudicator_address()
get_review_context(assessment_id)  # Registry view used by the Adjudicator
```

`role=1` is primary and `role=2` is corroborating. All SHA-256 values are
exactly 64 lowercase hexadecimal characters. Source URLs must be HTTPS, and
the immutable reference must be HTTPS or IPFS. R1 requires
`evidence_payload_hash == source_content_hash`; the fetched bytes must match
that committed digest. Assessment commitments are unique per
`program/version/subject_digest`, and an assessment deadline must
leave the full configured challenge window.
