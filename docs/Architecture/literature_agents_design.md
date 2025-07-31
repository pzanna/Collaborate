# Design Specification: Literature Review Agents for Eunice Research Platform

This document provides detailed design specifications for the Literature Review pipeline agents: **Literature Search Agent (LSA)**, **Screening & PRISMA Agent (SPA)**, **Synthesis & Review Agent (SRA)**, and **Writer Agent (WA)**. It also elaborates on the tasks, workflows, and responsibilities required to produce high-quality PRISMA reports and PhD-level literature reviews.

---

## 1. Literature Search Agent (LSA)

### Purpose

The LSA discovers and collects bibliographic records from multiple academic sources, normalises the results, and stores them for further screening.

### Core Responsibilities

- Query multiple data sources (e.g., PubMed, CrossRef, Semantic Scholar, arXiv).
- Apply filters (e.g., year, publication type, keywords) as specified by the Research Manager.
- Deduplicate results using DOI, PMID, or title/author/year heuristics.
- Store both raw source data and normalised records.

### Task Execution Steps

1. Receive a `SearchQuery` task from the Research Manager.
2. For each source:
   - Construct query URLs/APIs.
   - Paginate through results with appropriate rate limiting.
   - Parse metadata into a common schema.
3. Deduplicate records using hashing and fuzzy title matching.
4. Store results in the Literature Database via the Database Agent.
5. Return a `SearchReport` summarising:
   - Number of records fetched per source.
   - Number of duplicates removed.
   - Any errors or missing fields.

### Key Data Models

```python
class SearchQuery(BaseModel):
    lit_review_id: str
    query: str
    filters: dict[str, Any]
    sources: list[str]
    max_results: int

class SearchReport(BaseModel):
    lit_review_id: str
    total_fetched: int
    total_unique: int
    per_source_counts: dict[str, int]
    start_time: datetime
    end_time: datetime
```

### Metrics

- **Recall** of search queries vs. benchmarked queries.
- Deduplication effectiveness.
- API success/error rates.

---

## 2. Screening & PRISMA Agent (SPA)

### Purpose

The SPA manages systematic review screening, applies inclusion/exclusion criteria, and maintains a transparent PRISMA-compliant audit trail.

### Core Responsibilities

- Perform title/abstract and full-text screening.
- Apply rules or model-assisted classification against defined inclusion/exclusion criteria.
- Track all PRISMA flowchart counts.
- Maintain logs for human overrides and decisions.

### Task Execution Steps

1. **Initialisation:** Create a PRISMA session and register criteria (from YAML or JSON templates).
2. **Batch Screening:** For each record:
   - Evaluate against each criterion.
   - Produce a decision (include, exclude, unsure) with confidence scores.
   - Store the decision and rationale in the screening table.
3. **Human-in-the-loop:** Allow manual overrides via UI.
4. **Report Generation:** Compute PRISMA node counts and produce structured JSON for diagramming.

### Key Data Models

```python
class Criteria(BaseModel):
    name: str
    description: str
    type: Literal["include", "exclude"]

class ScreeningDecision(BaseModel):
    record_id: str
    stage: Literal["title_abstract", "full_text"]
    decision: Literal["include", "exclude", "unsure"]
    reason: str
    confidence: float
    timestamp: datetime
```

### Metrics

- Precision/recall of automated screening vs. human validation.
- Time saved by automated classification.
- Decision consistency (e.g., inter-rater reliability).

---

## 3. Synthesis & Review Agent (SRA)

### Purpose

The SRA analyses the included studies, extracts key data, and synthesises findings into structured summaries and meta-analysis outputs.

### Core Responsibilities

- Extract structured data (e.g., outcomes, sample sizes, statistics) from full-text or data tables.
- Aggregate findings to perform meta-analysis where applicable.
- Generate evidence tables and GRADE quality assessments.

### Task Execution Steps

1. **Data Extraction:** Parse outcomes from PDFs or structured XML/HTML.
2. **Analysis:**
   - Compute pooled effect sizes, confidence intervals, and heterogeneity metrics (I², τ²).
   - Generate visualisations (e.g., forest plots).
3. **Narrative Synthesis:** Create summaries highlighting study comparisons and trends.
4. **Report Storage:** Save outputs to the Literature Database.

### Key Data Models

```python
class OutcomeDatum(BaseModel):
    record_id: str
    outcome_name: str
    group_labels: list[str]
    means: list[float]
    sds: list[float]
    ns: list[int]

class MetaAnalysisResult(BaseModel):
    outcome_name: str
    pooled_effect: float
    ci: tuple[float, float]
    heterogeneity_i2: float
```

### Metrics

- Extraction accuracy vs. manual data extraction.
- Reliability of meta-analysis outputs.

---

## 4. Writer Agent (WA)

### Purpose

The WA transforms synthesised data into a structured, scholarly manuscript following PRISMA guidelines and PhD-level literature review standards.

### Core Responsibilities

- Draft Introduction, Methods, Results, and Discussion sections.
- Integrate PRISMA flowchart, evidence tables, and meta-analysis visuals.
- Ensure proper citation formatting (APA, Vancouver, etc.).
- Validate citations against the Literature Database.

### Task Execution Steps

1. **Draft Generation:** Produce a manuscript in Markdown, LaTeX, or Word.
2. **Revision Loops:** Support iterative refinement of sections.
3. **Citation Check:** Validate and correct references.
4. **Export:** Provide formatted outputs (PDF, DOCX).

### Key Data Models

```python
class DraftRequest(BaseModel):
    lit_review_id: str
    format: Literal["markdown", "latex", "docx"]
    style: Literal["apa", "vancouver"]

class DraftResponse(BaseModel):
    manuscript_text: str
    references: list[dict]
```

### Metrics

- Citation resolution rate (must be 100%).
- Human edit distance from first draft to final version.
- Compliance with PRISMA checklist.

---

## 5. Workflow Orchestration

A typical workflow:

1. **Search:** `LSA.search` → store records.
2. **Screen:** `SPA.screen_batch` → store inclusion/exclusion.
3. **Synthesis:** `SRA.extract_outcomes` → `SRA.meta_analyse`.
4. **Write:** `WA.draft_manuscript` → `WA.revise_section`.

The **Research Manager** coordinates these agents, ensuring data integrity and auditability.

---

## 6. Guidelines for Task Execution

- **Idempotence:** Each agent should ensure tasks can be re-run without duplicate entries.
- **Explainability:** All inclusion/exclusion and synthesis steps must produce human-readable rationales.
- **Evaluation:** Regularly benchmark the accuracy of automated components (e.g., screening or extraction).
- **Scalability:** Each agent can be horizontally scaled to handle large document sets.

---

## 7. Future Extensions

- Automated GRADE evidence profiling.
- Integration with external systematic review tools (e.g., Rayyan, Covidence).
- Enhanced semantic search using vector databases.
- Domain-specific customisation of review templates.

---

This document serves as a blueprint for implementing and refining the literature review pipeline within the Eunice platform.

