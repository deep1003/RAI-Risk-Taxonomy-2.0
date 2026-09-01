# L4 Golden Reference Validation Record

Generated on 1 September 2026.

## Scope

The golden reference ledger assigns one source-linked evidence record and one short direct quotation to each of the 622 active L4 cards. Internal human-review comments, source instructions, and transformation rationales remain in the internal audit files but are excluded from the public card payload and card interface.

## Coverage

| Check | Result |
|---|---:|
| Active L4 cards | 622 |
| Cards with a reference | 622 |
| Cards with a direct quotation | 622 |
| Cards with a source URL | 622 |
| Unique source URLs | 43 |
| Directly accessible automated checks, HTTP 200 or 202 | 27 |
| Publisher access-controlled checks, HTTP 403 | 16 |
| Missing or failed URLs | 0 |
| Public human-review comment or provenance fields | 0 |

## Source quality

| Source tier | Cards |
|---|---:|
| Peer-reviewed journal or conference paper | 249 |
| Official public-sector report | 100 |
| Identified research paper, including preprints | 257 |
| Established institutional report | 16 |

No unattributed source, dubious journal, or unverifiable bibliographic record is included. Publisher links returning HTTP 403 to automated clients are marked `PASS_ACCESS_CONTROLLED`; they resolve to recognised publisher or institutional hosts and are retained as access-controlled rather than represented as automated full-text successes.

## Selection method

1. Candidate evidence was drawn from the MIT AI Risk Repository source-level evidence export, which preserves source title, author, year, DOI or URL, risk category, risk subcategory, and a source excerpt.
2. Reports were restricted to official or established institutional publishers. Journal, conference, and identifiable research-paper records were retained when bibliographic metadata and a resolvable source link were present.
3. Up to 12 candidates per card were retrieved lexically and reranked against the bilingual L4 title and definition using BGE-M3 semantic embeddings.
4. Low-fit Physical AI cases were conservatively grounded in peer-reviewed surveys on human-robot safety or embodied-AI robustness.
5. Each displayed excerpt is limited to 24 source words, excluding editorial ellipsis marks. The quotation location identifies the repository evidence row or the source abstract.
6. All unique URLs were checked. The public payload was then rebuilt from the verified ledger.

## Interpretation boundary

The ledger records an evidence-supported conceptual match, not a claim that every source uses the exact L4 title verbatim. The direct excerpt is the auditable evidence unit. Preprints are explicitly labelled `Research Paper (Preprint)` and are not represented as peer-reviewed publications.

## Reproducibility artifacts

- `L4_Golden_Reference_Ledger.csv`: final one-reference-per-card ledger
- `Golden_Reference_URL_Check.csv`: unique-URL response record
- `L4_Golden_Reference_Candidates.csv`: lexical candidate set
- `L4_Golden_Reference_Candidates_Reranked.csv`: semantic reranking record
- `build_l4_golden_reference_ledger.py`: candidate construction
- `rerank_l4_golden_reference_candidates.py`: semantic reranking
- `finalize_l4_golden_reference_ledger.py`: source-policy and exception handling
- `apply_l4_golden_references.py`: synchronized application to full internal CSVs
