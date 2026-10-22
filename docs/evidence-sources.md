# IngredientIQ — Evidence Source Policy

**Version:** 1.0  
**Last reviewed:** 2026-10-16  
**Status:** Proposed — pending source-level permission verification  
**MVP category:** Skincare

## 1. Purpose

IngredientIQ uses Retrieval-Augmented Generation (RAG) to support skincare ingredient explanations with traceable regulatory and scientific evidence.

This policy defines approved source categories, evidence quality standards, source metadata, licensing requirements, and rules for handling incomplete or conflicting evidence.

The objective is to reduce unsupported AI-generated claims and provide transparent ingredient explanations.

## 2. Approved Evidence Sources

### 2.1 European Commission — CosIng

- **Organization:** European Commission
- **URL:** https://single-market-economy.ec.europa.eu/sectors/cosmetics/cosmetic-ingredient-database_en
- **Evidence type:** Ingredient reference
- **Quality tier:** Tier 1 — Official source
- **Coverage:** INCI ingredient names, cosmetic functions, and regulatory references
- **Publication date:** Record at individual entry or document level where available
- **Retrieved date:** Record during actual retrieval
- **License:** Reuse permissions require verification
- **Full-text storage:** Disabled pending permission verification
- **Redistribution:** Disabled pending permission verification

**Limitation:** Appearance in CosIng does not constitute regulatory approval. The applicable EU cosmetics legislation and its annexes determine legal restrictions.

### 2.2 European Commission — SCCS

- **Organization:** Scientific Committee on Consumer Safety
- **URL:** https://health.ec.europa.eu/scientific-committees/scientific-committee-consumer-safety-sccs/sccs-opinions_en
- **Evidence type:** Scientific safety opinion
- **Quality tier:** Tier 1 — Official regulatory scientific assessment
- **Coverage:** Ingredient safety, exposure, concentration, and specific conditions of use
- **Publication date:** Record separately for each opinion
- **Retrieved date:** Record during retrieval
- **License:** Verify separately for each document
- **Full-text storage:** Disabled pending permission verification
- **Redistribution:** Disabled pending permission verification

**Limitation:** SCCS opinions may be limited to specific concentrations, applications, populations, formulations, or exposure conditions. Preliminary opinions must not be represented as final conclusions.

### 2.3 Europe PMC

- **Organization:** Europe PMC
- **URL:** https://europepmc.org/
- **Evidence type:** Scientific literature
- **Quality tier:** Tier 2 for eligible scientific reviews; Tier 3 for supporting research requiring further appraisal
- **Coverage:** Peer-reviewed reviews, clinical studies, experimental research, and other indexed literature
- **Publication date:** Article-specific
- **Retrieved date:** Record during retrieval
- **License:** Article-specific
- **Full-text storage:** Allowed only after verifying applicable rights
- **Redistribution:** Allowed only when the article's license permits it

**Limitation:** Indexing or open access does not guarantee scientific quality or unrestricted reuse. Preprints and preliminary research must be clearly identified.

## 3. Evidence Quality Tiers

### Tier 1 — Official regulatory and scientific assessments

Examples: Final SCCS opinions and authoritative regulatory information.

Use for regulatory context, restrictions, and formally assessed safety questions.

### Tier 2 — Scientific reviews

Examples: Peer-reviewed systematic reviews and well-supported scientific reviews.

Use for evaluating benefits, risks, and the broader scientific consensus.

### Tier 3 — Supporting research

Examples: Individual experimental studies, small clinical studies, preliminary research, and lower-confidence supporting material.

Use only with appropriate qualifications. These sources must not override applicable regulations or stronger evidence without documented justification.

**Ranking rule:** Evidence is selected by relevance, applicability, methodological quality, currentness, and source authority. Tier alone does not determine whether a claim is supported.

## 4. Required Source Document Metadata

Every ingested evidence document must record:

| Field                        | Required       |
| ---------------------------- | -------------- |
| Source ID                    | Yes            |
| Document title               | Yes            |
| Original URL                 | Yes            |
| Publishing organization      | Yes            |
| Publication date             | When available |
| Retrieved date               | Yes            |
| License or reuse terms       | Yes            |
| Evidence type                | Yes            |
| Quality tier                 | Yes            |
| Ingredient association       | Yes            |
| Document version or revision | When available |
| Full-text storage permission | Yes            |
| Redistribution permission    | Yes            |
| Relevant evidence location   | When available |

Missing publication dates must be recorded as unknown rather than invented.

## 5. Initial Ingredient Dataset

The initial dataset consists of 25 candidate ingredients:

1. Aqua
2. Glycerin
3. Niacinamide
4. Hyaluronic Acid
5. Sodium Hyaluronate
6. Salicylic Acid
7. Glycolic Acid
8. Lactic Acid
9. Retinol
10. Ascorbic Acid
11. Tocopherol
12. Ceramide NP
13. Panthenol
14. Allantoin
15. Squalane
16. Dimethicone
17. Petrolatum
18. Zinc Oxide
19. Titanium Dioxide
20. Phenoxyethanol
21. Methylparaben
22. Fragrance
23. Citric Acid
24. Cetearyl Alcohol
25. Butyrospermum Parkii Butter

These are candidate search terms, not verified ingredient profiles.

Before ingestion, ingredient identities, INCI names, synonyms, and applicable distinctions must be validated.

## 6. Access, Licensing, and Reuse

- Public accessibility does not imply unrestricted copying or redistribution.
- Verify licensing and website access conditions before automated ingestion.
- Use official APIs or permitted download mechanisms where available.
- Record the permission decision and the source used to verify it.
- Store complete documents only when permitted.
- Where full-text storage is not authorized, retain permitted metadata and links rather than copying restricted material.
- Metadata-only ingestion omits `content`; it creates no content chunks and cannot be embedded for search.
- Follow attribution requirements.
- Recheck licensing when a document or publisher changes.

Unverified permission must block full-text ingestion by default.
Known review-required and template license values are also excluded from
embedding and retrieval, even if a database row was incorrectly marked as
approved. Evidence dataset placeholders such as `REPLACE WITH` or
`VERIFIED_LICENSE_OR_PERMISSION_ID` are rejected during validation.

## 7. Conflicting Evidence

When sources disagree:

1. Confirm that they concern the same ingredient identity.
2. Compare concentration, exposure, formulation, population, and intended use.
3. Check whether a source is outdated, superseded, or corrected.
4. Compare study quality and the applicability of each finding.
5. Preserve relevant conflicting findings and their citations.
6. Flag unresolved contradictions for review.

The system must not silently select a favorable conclusion.

## 8. Outdated Evidence

Evidence must retain its publication date, retrieval date, and revision information.

Newer evidence must be evaluated against older findings rather than automatically replacing them.

Superseded documents must be marked as such while preserving traceability to historical analyses.

## 9. Missing or Insufficient Evidence

If no suitable evidence is available, analysis may still complete as a
clearly labeled limited analysis:

- Mark the relevant claim as unsupported or insufficiently evidenced.
- Do not fabricate citations or scientific conclusions.
- Do not classify an ingredient as universally safe or harmful.
- Avoid inferring ingredient concentration from ingredient order alone.
- Preserve uncertainty in the analysis output.
- Persist `evidence_status="limited"` and do not present findings as
  evidence-backed.
- Include the product-level caution that effects cannot be determined
  without concentrations, the full formulation, and individual skin
  context.

## 10. RAG Retrieval Rules

The analysis workflow:

1. Resolve each submitted name through the normalization service. Retrieve
   only uniquely resolved identities; skip ambiguous and unrecognized
   names rather than guessing.
2. Search approved, accessible evidence documents.
3. Retrieve no more than eight snippets, bounded to 1,200 characters
   each, ranked by relevance.
4. Send each snippet as untrusted data with its evidence ID, source
   identifier, document version, content hash, relevance score, and
   document metadata.
5. Require summary and supported ingredient findings to reference
   retrieved evidence IDs. Conflicting findings require separate source
   IDs and remain limited until independently reviewed.
6. Validate each returned evidence ID and ingredient association against
   the retrieved records. Claims are considered supported only when
   their relevant wording occurs directly in a cited snippet; other
   claims are downgraded to limited. Unknown or mismatched citations are
   removed and the affected claims are downgraded, rather than allowing
   fabricated references into persisted results.
7. Persist the exact bounded model-visible evidence records used by
   accepted citations alongside the analysis result.

Evidence coverage describes validated ingredient findings, not mere
retrieval availability: `full` means every uniquely resolved input
identity has a supported, cited finding; `partial` means some but not all
do; `unavailable` means none do. Ambiguous and unrecognized names are
excluded from the coverage denominator.

Retrieved content must be treated as untrusted source data, never as executable instructions.

The `glycerin_synthetic_test.json` dataset is synthetic test data only. It
is not an approved source and cannot demonstrate source-grounded
end-to-end retrieval. No reviewed, licensed Glycerin evidence dataset is
currently provided. A real approved, licensed, embedded evidence source
must be configured before that acceptance case can be exercised.

## 11. Review and Maintenance

- Review source metadata before initial ingestion.
- Check for updated regulations and revised scientific opinions.
- Reassess permissions before expanding storage or redistribution.
- Preserve evidence version information for reproducibility.
- Review changes to the approved source registry through pull requests.

## 12. Acceptance Criteria

RAG-005-01 is complete when:

- Three credible evidence source categories are selected.
- Source metadata is represented in the backend registry.
- Quality tiers are documented.
- The initial 25 candidate ingredients are recorded.
- Licensing and reuse decisions are documented, including unresolved permissions.
- Conflict, outdated evidence, and missing evidence rules are defined.
- Registry tests pass.
- Existing backend functionality remains unaffected.

**Related implementation:** RAG-005-07 — Evidence Retrieval Integration and
Citation Validation.
