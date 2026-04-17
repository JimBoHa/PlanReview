# Training Data Needed For A True CAD-Semantic / Code-Reasoning Model

The current application now has:

- OCR fallback,
- ontology-backed symbol/system detection,
- two-pass drawing/spec semantics,
- cross-sheet/spec graph reasoning,
- optional local semantic embeddings.

That is useful, but it is not enough for human-equivalent plan review. To move toward a genuinely trained local model, the most valuable training data is the following.

## 1. Drawing Sheet Understanding Dataset

Goal: classify and semantically understand each sheet.

Per page labels:

- `sheet_number`
- `sheet_title`
- `discipline`
- `page_class`
  - examples: `cover`, `plan`, `detail`, `section`, `elevation`, `schedule`, `legend`, `diagram`, `spec-section`
- `title_block_bbox`
- `revision_block_bbox`
- `scale_callout_bbox`
- `north_arrow_bbox`

Recommended volume:

- 10,000+ pages minimum for a useful model
- 50,000+ pages for robust generalization across firms/disciplines

Annotation format:

- PDF page image path
- normalized page size
- bounding boxes in pixel coordinates
- canonical sheet metadata

## 2. Symbol Ontology Detection Dataset

Goal: detect and classify graphical symbols, not just text mentions.

Per symbol instance:

- `symbol_class_id`
- `discipline`
- `bbox`
- optional `rotation`
- optional `connected_line_ids`
- optional `text_leader_bbox`

Initial ontology should include at least:

- electrical devices
- panelboards and switchboards
- light fixtures and controls
- fire alarm devices
- fire protection devices
- plumbing fixtures and drains
- accessibility symbols
- life safety / egress symbols
- detail / section callouts

Recommended volume:

- 500 to 2,000 labeled instances per symbol class
- 100+ classes to start being truly useful

## 3. Linework / Geometry Understanding Dataset

Goal: infer walls, doors, rooms, conduits, pipes, equipment blocks, and diagram connectivity.

Per page labels:

- polylines grouped into semantic objects
- `wall`, `door_swing`, `room_boundary`, `pipe`, `conduit`, `duct`, `equipment_outline`, `callout_bubble`
- connectivity graph between lines and symbols

Recommended volume:

- 2,000+ fully labeled sheets
- more important than raw count: strong discipline diversity

## 4. Cross-Sheet Reference Dataset

Goal: resolve references like `3/A601`, section cuts, enlarged plans, keynote references, and schedules.

Per reference:

- source page
- source bbox
- reference text
- target sheet number
- target detail number if applicable
- whether target exists in set
- whether reference is correct

Recommended volume:

- 100,000+ reference instances

## 5. Specification Parsing Dataset

Goal: parse spec sections into structured requirement clauses.

Per spec section:

- `section_number`
- `title`
- `discipline`
- clause segmentation
- clause type:
  - `scope`
  - `submittal`
  - `material`
  - `execution`
  - `quality`
  - `testing`
- requirement modality:
  - `mandatory`
  - `directive`
  - `informational`
- entities mentioned
- quantitative constraints

Recommended volume:

- 20,000+ full spec sections
- 250,000+ clause-level annotations

## 6. Drawing-to-Spec Alignment Dataset

Goal: learn that a drawing page/detail is governed by specific spec sections.

Per linked pair:

- source drawing page
- optional source bbox/region
- target spec section number
- relation type:
  - `explicit-reference`
  - `semantic-match`
  - `required-by-discipline`
- reviewer confidence

Recommended volume:

- 50,000+ drawing/spec links

## 7. Code Compliance Finding Dataset

Goal: train finding generation, ranking, and explanation.

Per finding:

- project type
- governing standards
- source document kind
- page number
- source bbox
- violated citation
- severity
- reviewer comment
- normalized issue type
- disposition:
  - `true-positive`
  - `false-positive`
  - `needs-context`

Recommended volume:

- 100,000+ adjudicated findings across many code families

This is the most valuable dataset if the end goal is actual review quality.

## 8. Versioned Code Corpus Metadata

Goal: map contract date, jurisdiction, and owner type to the correct baseline.

Per standard/version:

- issuer
- family
- version
- publication date
- effective date
- retirement date
- jurisdiction applicability
- owner applicability
- copyright status

This data does not need model labeling, but it must be extremely accurate.

## Labeling Guidance

If you can only procure one thing first, prioritize in this order:

1. adjudicated historical review comments linked to drawing/spec regions
2. drawing-to-spec alignment labels
3. symbol detection labels
4. cross-sheet reference labels
5. spec clause parsing labels

For every labeled example, capture:

- source PDF
- page index
- sheet number
- exact screenshot region
- normalized label schema version
- reviewer identity or confidence

## Recommended Storage Schema

Use JSONL with one record per labeled object. Example fields:

```json
{
  "project_id": "sample-001",
  "document_kind": "drawings",
  "page_number": 12,
  "sheet_number": "E201",
  "task": "symbol_detection",
  "bbox": [1142, 866, 1220, 932],
  "label": "electrical.receptacle.gfci",
  "source_pdf": "uploads/project-a/drawings.pdf"
}
```

For compliance findings:

```json
{
  "project_id": "sample-001",
  "task": "compliance_finding",
  "document_kind": "drawings",
  "page_number": 12,
  "sheet_number": "E201",
  "bbox": [820, 640, 1210, 910],
  "citation": "NFPA 70 310.16",
  "issue_type": "undersized_conductor",
  "comment": "250 kcmil feeder is undersized for 450A breaker.",
  "disposition": "true-positive"
}
```

## What A Small Local Model Should Eventually Learn

If you procure enough labeled data, the first practical local models to train would be:

1. page classifier for sheet type / discipline
2. symbol detector
3. callout/reference resolver
4. drawing-to-spec ranker
5. compliance finding ranker / false-positive suppressor

That sequence is more realistic than trying to train one monolithic model first.
