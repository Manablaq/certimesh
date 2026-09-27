# CertiMesh R1 architecture

## Immutable program versions

`create_program` creates version 1. `create_program_version` creates only the
next sequential version and is restricted to the original creator. Criteria,
evidence policy, authority addresses, and timing commitments are stored with
the version and are never edited. Retiring a version only blocks new
assessments; it does not alter existing assessments or certificates.

## State machine

```text
REQUESTED -> EVIDENCE_BOUND -> PROVISIONAL -> FINAL
     |             |               |
     |             |               +-> CHALLENGED -> REQUESTED (new generation)
     |             +-> REPAIR_REQUIRED -> REQUESTED (new generation)
     +-------------------------------------------> EXPIRED
```

`REPAIR` is a terminal outcome for the current generation, never a certificate.
`EXPIRED` is terminal. Only `PROVISIONAL` can enter `FINAL`, and only after its
challenge deadline has passed without a challenge.

## Evidence binding

Each assessment commitment is unique, and each generation requires exactly one
primary and one corroborating authority.
Authorities, record ids, immutable source references, source hashes, versions,
publication timestamps, observation timestamps, and expiry are committed before
review. The bound evidence-set digest is stored on the assessment and included
in the certificate digest.

## Consensus boundary

The nondeterministic function has no storage writes. It fetches both committed
sources, checks status/size/UTF-8/payload-and-content hashes, frames the bytes inside
`UNTRUSTED_EVIDENCE`, and asks for exactly one JSON decision key. The validator
repeats the whole fetch/evaluation and compares status, decision, failure code,
observed hash, and evidence-set hash. A disagreement rejects the transaction.
