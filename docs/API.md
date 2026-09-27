# CertiMesh R1 API

## Writes

```text
create_program(program_id, criteria_json, evidence_policy_json,
  primary_authority, corroborating_authority, challenge_window_seconds,
  max_evidence_age_seconds, certificate_validity_seconds,
  max_assessment_horizon_seconds) -> version
create_program_version(...) -> next_version
retire_program_version(program_id, version)
create_assessment(program_id, version, subject_id, subject_digest,
  assessment_deadline) -> assessment_id
attest_evidence(assessment_id, generation, role, record_id, record_version,
  source_url, immutable_source_ref, evidence_payload_hash,
  source_content_hash, published_at, observed_at, expires_at)
bind_evidence(assessment_id)
assess(assessment_id)
challenge_assessment(assessment_id, challenge_material)
open_repair_generation(assessment_id) -> generation
finalize_assessment(assessment_id)
expire_assessment(assessment_id)
```

## Views

```text
get_program(program_id, version)
get_latest_program_version(program_id)
get_assessment(assessment_id)
get_evidence(assessment_id, generation, role)
get_certificate(assessment_id)
get_assessment_count()
```

`role=1` is primary and `role=2` is corroborating. All SHA-256 values are
exactly 64 lowercase hexadecimal characters. Source URLs must be HTTPS, and
the immutable reference must be HTTPS or IPFS. R1 requires
`evidence_payload_hash == source_content_hash`; the fetched bytes must match
that committed digest. Assessment commitments are unique per
`program/version/subject_digest`, and an assessment deadline must
leave the full configured challenge window.
