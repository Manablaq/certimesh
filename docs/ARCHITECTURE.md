# CertiMesh R1 architecture

## Split deployment boundary

The production deployment is four contracts. `CertiMeshProgramRegistry` owns
immutable program versions. `CertiMeshRegistry` owns assessment state,
finalization, expiration, and certificates. `CertiMeshEvidenceRegistry` owns
authority attestations and the bound evidence-set digest.
`CertiMeshAdjudicator` owns no protocol state that can authorize a certificate;
it only retrieves the Registry's immutable review snapshot, runs the validator
consensus boundary, and sends a finalized callback back to the Registry.

The Program Registry is deployed first. The Assessment Registry is deployed
with its address as an immutable constructor value. The Evidence Registry is
deployed with both registry addresses. The Adjudicator is then deployed with
the Assessment Registry address. The Assessment Registry owner may bind the
Evidence Registry and Adjudicator exactly once, and each binding requires the
counterparty's reciprocal `registry_address()` view to return the expected
Registry address. This prevents misbound or replacement components and leaves
no administrator verdict path.

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

An adjudicator dispatch can be re-emitted as `EVIDENCE_BOUND -> EVIDENCE_BOUND`
through the requester-only `retry_assessment` recovery method. This preserves
the original evidence binding and generation; it is not a new review or a
verdict override. A callback can advance the state only from the same exact
bound generation and evidence-set hash.

## Evidence binding

The Evidence Registry is the only write surface for evidence. Each assessment
commitment is unique, and each generation requires exactly one
primary and one corroborating authority.
Authorities, record ids, immutable source references, source hashes, versions,
publication timestamps, observation timestamps, and expiry are committed before
review. The bound evidence-set digest is stored on the assessment and included
in the certificate digest.

## Consensus boundary

The nondeterministic function has no storage writes. The Adjudicator fetches both committed
sources, checks status/size/UTF-8/payload-and-content hashes, frames the bytes inside
`UNTRUSTED_EVIDENCE`, and asks for exactly one JSON decision key. Subjective
review uses GenLayer's non-comparative equivalence principle with strict
format and metadata validation; validators independently verify the committed
review output rather than requiring byte-for-byte model phrasing. A disagreement
or malformed result produces no callback and is recoverable through the exact
bound-request retry path.
The Registry callback accepts only the bound Adjudicator, the exact assessment
generation, and the exact evidence-set digest.
