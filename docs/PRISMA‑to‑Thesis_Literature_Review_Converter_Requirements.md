# PRISMA‑to‑Thesis Literature Review Converter – Requirements Specification (v1.0)

**Author:** Sky (for Paul Zanna)  
**Date:** 23-07-2025  
**Status:** Draft  
**Target System:** Automated Literature Review Application (ALRA) – “PRISMA JSON ➜ PhD Thesis Lit Review” module

---

## 0. Change Log

| Version | Date       | Author | Summary |
|---------|------------|--------|---------|
| v1.0    | 23-07-2025 | Sky    | Initial requirements document |

---

## 1. Purpose & Scope

This document defines the requirements to implement functionality that **transforms a PRISMA-style JSON output** (plus associated artefacts) into a **PhD thesis–quality literature review chapter**. It covers:

- Parsing and validating PRISMA JSON and related data.
- Mapping systematic review artefacts to thesis-oriented narrative sections (context, theory, gaps, conceptual model).
- Automating draft generation (Markdown/LaTeX) using templates and LLM prompts.
- Providing human-in-the-loop checkpoints and deterministic reproducibility.

**Out of scope:** Producing the original PRISMA JSON, performing the initial systematic review, or handling full thesis compilation beyond the literature review chapter.

---

## 2. Definitions & Acronyms

- **PRISMA JSON:** Machine-readable log of counts, reasons, and metadata from a systematic review workflow (e.g., `prisma_log.json`, evidence tables).
- **Evidence Table:** Structured data of included studies (CSV/JSON).
- **LLM:** Large Language Model used for thematic synthesis, gap analysis, etc.
- **Thesis Lit Review:** Chapter(s) in a PhD thesis providing theoretical framing, critique, gaps, and research questions.
- **Template Engine:** System (e.g., Jinja2, Mustache) to render Markdown/LaTeX from data.

---

## 3. Input & Output Specification

### 3.1 Inputs

| Artefact | Required | Format | Description |
|----------|----------|--------|-------------|
| `prisma_log.json` | Yes | JSON | Counts for each PRISMA stage + exclusion reasons |
| `studies.json` / `evidence.csv` | Yes | JSON/CSV | Included study metadata & outcomes |
| `bias.json` (optional) | No | JSON | Risk-of-bias scores per study |
| `themes.json` (optional) | No | JSON | Pre-computed thematic clusters |
| `gaps.json` (optional) | No | JSON | Prioritised gaps |
| Config file | Yes | YAML/JSON | User preferences (section order, template paths, style) |
| Prompt library | Yes | YAML/JSON | LLM prompt templates with variables |
| CSL/Bib file (optional) | No | `.csl`, `.bib` | Citation style & bibliography database |
| User overrides | Optional | Markdown/JSON | Manual text snippets to force-insert |

### 3.2 Outputs

| Artefact | Format | Purpose |
|----------|--------|---------|
| Draft literature review chapter | Markdown (primary), optionally LaTeX/Docx | Main deliverable |
| Figures | Mermaid/TikZ/SVG/PNG | PRISMA flow, conceptual model |
| Appendices | Markdown/PDF | Full tables, search strings, RoB details |
| Audit log | JSONL | Provenance of generation (prompts, model IDs) |
| Diff report (optional) | HTML/Markdown | Changes vs. previous run |

---

## 4. High-Level Workflow

```mermaid
flowchart LR
    A[Load Config & Templates] --> B[Ingest & Validate PRISMA JSON]
    B --> C[Normalise & Link Evidence Tables]
    C --> D[Thematic Synthesis (LLM/Rules)]
    D --> E[Gap Analysis & Prioritisation]
    E --> F[Conceptual Model Draft]
    F --> G[RQ/Hypothesis Generation]
    G --> H[Draft Assembly (Markdown/LaTeX)]
    H --> I[Human Review Checkpoints]
    I --> J[Export & Versioning]
````

---

## 5. Functional Requirements (FR)

### FR‑1 Ingestion & Validation

- **FR‑1.1** The system **must** accept PRISMA JSON adhering to a defined schema (Appendix A).
- **FR‑1.2** The system **must** validate JSON and CSV structures; invalid fields produce actionable error messages.
- **FR‑1.3** The system **shall** compute missing counters if derivable (e.g., included = full\_text\_assessed − full\_text\_excluded).
- **FR‑1.4** The system **shall** support evidence tables in CSV or JSON and map them to internal objects.

### FR‑2 Normalisation & Enrichment

- **FR‑2.1** The system **must** normalise study records (consistent field names, types).
- **FR‑2.2** The system **shall** enrich records with derived fields (e.g., bias\_overall from domain scores).
- **FR‑2.3** The system **should** link external bibliographic info (DOI lookup) if configured.

### FR‑3 Thematic Synthesis

- **FR‑3.1** The system **shall** cluster findings into themes using either:
  a) Pre-supplied `themes.json`, or
  b) An LLM prompt pipeline (configurable).
- **FR‑3.2** Each theme **must** include: label, description, representative studies, contradictions.
- **FR‑3.3** The system **should** support deterministic mode (fixed seed/temperature=0).

### FR‑4 Gap Analysis

- **FR‑4.1** The system **shall** derive gaps from themes/conflicts using LLM or rules.
- **FR‑4.2** Gaps **must** be scored by impact/feasibility/novelty (1–5) unless overridden.
- **FR‑4.3** The system **shall** allow manual gap edits prior to draft assembly.

### FR‑5 Conceptual Model Drafting

- **FR‑5.1** The system **shall** propose a conceptual model (text + node/edge list).
- **FR‑5.2** The system **must** output a diagram block (Mermaid/TikZ) renderable on GitHub/LaTeX.
- **FR‑5.3** Users **can** override node/edge sets manually.

### FR‑6 Research Question / Hypothesis Generation

- **FR‑6.1** Generate RQs/Hs that map 1:1 to high-impact gaps.
- **FR‑6.2** Each RQ/H **must** specify constructs and (for hypotheses) predicted direction.
- **FR‑6.3** Provide a configurable template for RQ/H phrasing.

### FR‑7 Draft Assembly

- **FR‑7.1** The system **must** assemble a chapter following a configurable outline (Section 1 scaffold).
- **FR‑7.2** The system **shall** insert tables (study characteristics, bias summary) in condensed form and link full versions in appendices.
- **FR‑7.3** The system **shall** include PRISMA paragraph + flow figure reference.
- **FR‑7.4** The system **must** embed citation keys or numeric references according to CSL if enabled.

### FR‑8 Templates & Prompt Management

- **FR‑8.1** Store templates (Markdown/LaTeX) with placeholders (e.g., `{{theme.summary}}`).
- **FR‑8.2** Store prompts in a versioned library; log prompt text, variables, and model parameters.
- **FR‑8.3** Allow per-section prompt overrides via config.

### FR‑9 Human-in-the-Loop Checkpoints

- **FR‑9.1** Provide checkpoints after: theme extraction, gap list, conceptual model, and final draft.
- **FR‑9.2** Support interactive editing (CLI prompts, web UI forms, or JSON patch files).
- **FR‑9.3** Changes must be captured in the provenance log.

### FR‑10 Export & Versioning

- **FR‑10.1** Export Markdown by default; optional LaTeX, Docx via Pandoc.
- **FR‑10.2** Save all outputs with version tags and SHA‑256 hashes.
- **FR‑10.3** Provide a “reproduce run” command that regenerates the draft from stored artefacts.

### FR‑11 Error Handling & Logging

- **FR‑11.1** All errors **must** be classified (validation, prompt, template, I/O) and logged with stack trace.
- **FR‑11.2** The system **shall** offer fallback (e.g., skip theme extraction if LLM fails and continue with raw data).
- **FR‑11.3** Provide summarised error reports for end-users.

---

## 6. Non‑Functional Requirements (NFR)

| ID    | Category        | Requirement                                                                                       |
| ----- | --------------- | ------------------------------------------------------------------------------------------------- |
| NFR‑1 | Performance     | End-to-end conversion ≤ 2 minutes for 200 studies on standard workstation (LLM latency excluded). |
| NFR‑2 | Determinism     | Deterministic mode using fixed seeds and cached LLM outputs.                                      |
| NFR‑3 | Maintainability | Templates and prompts modular; 80% unit test coverage for core transformation code.               |
| NFR‑4 | Usability       | Clear CLI help, meaningful error messages, docs for config & schemas.                             |
| NFR‑5 | Accessibility   | Markdown output follows heading hierarchy; figures have alt-text.                                 |
| NFR‑6 | Security        | Sanitize external text (escape HTML/JS); redact PII if present.                                   |
| NFR‑7 | Provenance      | Log model IDs, prompts, parameters, timestamps; store in JSONL.                                   |
| NFR‑8 | Extensibility   | Easy to add new sections (e.g., policy implications) via template fragments.                      |

---

## 7. Data Models & Schemas

### 7.1 PRISMA Log Schema (Excerpt)

```json
{
  "identified_total": 0,
  "duplicates_removed": 0,
  "screened_title_abstract": 0,
  "excluded_title_abstract": 0,
  "full_text_assessed": 0,
  "full_text_excluded": 0,
  "included": 0,
  "exclusion_reasons": [
    {"code": "WRONG_POP", "count": 0}
  ]
}
```

### 7.2 Study Record (Internal)

```json
{
  "id": "S01",
  "title": "Example Study",
  "year": 2022,
  "design": "Experimental",
  "population": "Rat cortical neurons",
  "outcomes": ["SNR", "Task performance"],
  "effect_summary": "SNR=12 dB; hit-rate 85%",
  "bias_overall": "Moderate",
  "doi": "10.1234/example",
  "license": "CC-BY"
}
```

### 7.3 Theme Object

```json
{
  "name": "Closed-loop Control",
  "summary": "Several studies demonstrated...",
  "studies": ["S03","S09","S11"],
  "contradictions": [
    {"issue": "Metric inconsistency", "studies": ["S03","S11"]}
  ]
}
```

### 7.4 Gap Object

```json
{
  "id": "G1",
  "description": "Lack of standardised learning benchmarks",
  "impact": 5,
  "feasibility": 4,
  "novelty": 4,
  "linked_themes": ["Closed-loop Control"]
}
```

---

## 8. Template & Prompt Library

### 8.1 Template Placeholder Conventions

- `{{ prisma.paragraph }}`
- `{{ table.study_characteristics }}`
- `{{ themes | render('themes_section.md') }}`

### 8.2 Example Prompt (Theme Extraction)

```yaml
id: theme_extraction_v1
model: gpt-4o
temperature: 0.0
prompt: |
  You are an expert reviewer. Cluster the following studies into 3–5 themes...
inputs:
  - studies_json
outputs:
  - themes_json
```

---

## 9. Error Handling & Recovery

- **Validation errors:** Stop and report; offer `--ignore-validation` to continue.
- **LLM failures/timeouts:** Retry (max N), then fall back to rule-based summaries or leave placeholders.
- **Template errors (missing placeholder):** Warn and continue with placeholder name in output.

---

## 10. Testing & QA

### 10.1 Test Types

- **Unit:** JSON schema validation, table rendering, prompt variable substitution.
- **Integration:** End-to-end on toy datasets (5–10 studies).
- **Regression:** Snapshot tests comparing generated Markdown against approved golden files.
- **Security:** Injection strings in study titles to ensure sanitisation.

### 10.2 Acceptance Criteria (examples)

- Given valid PRISMA JSON, the system outputs a Markdown chapter with all required sections and correct counts.
- Deterministic mode yields identical output across runs.

---

## 11. Security & Compliance

- Strip/escape HTML/JS from input text.
- Redact personal identifiers if present.
- Store API keys encrypted (if calling LLM APIs).
- Log access to sensitive files for audit.

---

## 12. Deployment & Integration

- **CLI Command:** `alra prisma2thesis --config config.yml --out chapter2.md`
- **Python API:** `convert_prisma_to_thesis(prisma, studies, config) -> str`
- **CI Integration:** GitHub Action to regenerate chapter on data/template updates.
- **Containerisation:** Optional Docker image with dependencies (Pandoc, CSL).

---

## 13. Future Enhancements

- GUI editor to drag/drop sections.
- Support for multiple review questions merged into one thesis chapter.
- Automatic figure generation beyond PRISMA (e.g., timeline plots).
- Multilingual output generation.

---

## 14. MoSCoW Summary

| Priority        | Requirement Examples                                                             |
| --------------- | -------------------------------------------------------------------------------- |
| **Must**        | Parse/validate PRISMA JSON; assemble thesis chapter; deterministic mode; logging |
| **Should**      | Automatic theme/gap extraction; conceptual model drafting; citation integration  |
| **Could**       | GUI wizard; multilingual output; LaTeX diagram auto-conversion                   |
| **Won’t (now)** | Full thesis build automation; journal submission formatting                      |

---

## 15. References (Standards/Guides)

- PRISMA 2020 Statement & Checklist
- PRISMA-P (Protocols)
- GRADE guidelines (certainty of evidence)
- University thesis formatting guidelines (user-specific)

---

## Appendix A – JSON Schemas (Full)

*(Provide full JSON Schema definitions for `prisma_log.json`, `study_record.json`, `theme.json`, `gap.json` here.)*

## Appendix B – Example Config (`config.yml`)

```yaml
templates:
  main: templates/chapter.md.j2
  theme_section: templates/theme.md.j2
  prisma_paragraph: templates/prisma_para.md.j2

prompts:
  theme_extraction: prompts/theme_extraction.yaml
  gap_analysis: prompts/gap_analysis.yaml
  conceptual_model: prompts/concept_model.yaml
  rq_generation: prompts/rq.yaml

output:
  format: markdown
  path: out/chapter2.md
  include_appendices: true

deterministic: true
seed: 42
llm:
  provider: openai
  model: gpt-4o
  temperature: 0.0
```

## Appendix C – Minimal Jinja2 Snippet

```jinja2
## 2.4 Systematic Review Results

{{ prisma.paragraph }}

![PRISMA Flow](prisma_flow.svg)

### Study Characteristics
| ID | Design | Outcomes | Effect Summary | RoB |
|----|--------|----------|----------------|-----|
{% for s in studies %}
| {{ s.id }} | {{ s.design }} | {{ s.outcomes|join(", ") }} | {{ s.effect_summary }} | {{ s.bias_overall }} |
{% endfor %}

### Thematic Synthesis
{% for t in themes %}
**{{ t.name }}** — {{ t.summary }}

Representative studies: {{ t.studies|join(", ") }}

{% endfor %}
```

---
