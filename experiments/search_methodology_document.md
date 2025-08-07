# Literature Search Automation Requirements Document

## Overview

This document defines the functional and technical requirements for building an AI-assisted literature search system. The system will iteratively retrieve, score, and chain academic documents based on a research plan input, aiming to compile a high-relevance corpus.

## Objectives

- Automate the discovery of academic papers relevant to a provided research plan.
- Use recursive citation chaining to explore the conceptual lineage of relevant documents.
- Score and rank all documents based on semantic similarity to the research plan.
- Terminate when the search corpus meets predefined relevance and coverage conditions.

## System Inputs

- `research_plan` (text): A detailed description of the research goal.
- `target_doc_count` (integer): The number of high-relevance documents required.
- `similarity_threshold` (float): Minimum document score (e.g., 0.7) to be considered high relevance.

## Functional Requirements

### 1. Term Extraction (via Sentence-Transformers)

Extract key search terms directly from the research plan using an embedding-based method that is lightweight and compatible with container environments.

**Steps:**

1. **Preprocessing**
   - Lowercase input, strip punctuation.
   - Sentence-tokenise the research plan.
   - Tokenise into words, removing stopwords.
   - Extract candidate n-grams (1–3 words).
   - Optionally extract fluent noun phrases using spaCy:

```python
import spacy
nlp = spacy.load("en_core_web_sm")

def noun_phrases(text):
    return [chunk.text for chunk in nlp(text).noun_chunks if len(chunk.text.split()) <= 4]
```

2. **Ranking Candidates**
   - Encode all candidate phrases using the same sentence-transformer used for document ranking (e.g., `all-MiniLM-L6-v2`).
   - Encode the full research plan.
   - Compute cosine similarity between each candidate and the plan.
   - Return top-N ranked phrases.

### 2. Initial Search

- Perform a literature search using extracted terms via academic APIs (e.g., CrossRef, PubMed, Semantic Scholar).
- Output: `initial_results` (list of documents with title, abstract, metadata).

### 3. Document Scoring and Ranking

- For each document:
  - Generate embedding.
  - Compute similarity to the research plan embedding.
  - Assign a relevance score ∈ [0, 1].
  - Sort results descending by score.

**Optional:** Use adaptive thresholding instead of fixed similarity:

```python
import numpy as np
scores = np.array([doc['score'] for doc in documents])
dynamic_cutoff = np.quantile(scores, 0.85)  # keep top 15%
high_scoring_docs = [doc for doc in documents if doc['score'] >= dynamic_cutoff]
```

### 4. Reference Extraction and Deduplication

- For documents scoring above threshold:
  - Extract references using available metadata or APIs.
  - Maintain a set of processed DOIs/IDs to prevent duplication and citation loops.

### 5. Abstract Retrieval

- For each extracted reference:
  - Retrieve abstract (preferably via API, fallback to scraping or metadata proxy).
  - Tag references where abstract retrieval fails.

### 6. Recursive Ranking Loop

- Score and rank referenced abstracts against the research plan.
- Repeat steps 4–6 for newly high-scoring documents.
- On each round, adjust similarity threshold or quantile to reflect narrowing focus.

### 7. Stopping Conditions

Terminate the recursive search loop if any of the following are met:

- The number of documents with score > `similarity_threshold` or quantile cutoff reaches `target_doc_count`.
- No new high-scoring documents are found.
- Marginal gain in diversity or score across rounds is below threshold.

## Optional Enhancements

- Inject 5–10% of lower-ranked documents per round to preserve thematic diversity.
- Use perspective-guided question generation to stimulate breadth (see STORM-inspired appendix).
- Visualise citation chains as graphs for debugging or insight.
- Replace `all-MiniLM-L6-v2` with `all-MiniLM-L12-v2` or `multi-qa-mpnet-base-dot-v1` for higher fidelity embeddings if resources permit.
- Implement retry strategy using exponential backoff with jitter for rate-limited API queries.

## Outputs

- Ranked document list with metadata (title, authors, abstract, score, references).
- Structured JSON file suitable for downstream synthesis or review.

## Constraints

- Must be stateless and re-entrant per query.
- Must cache or log document IDs to avoid processing duplicates.
- Should be modular to allow for backend/API substitutions.

## Recommended Technologies

- Python (for NLP and async support)
- HuggingFace Transformers or Sentence-Transformers
- ONNX or PyTorch model for embedding computation
- Semantic Scholar / PubMed / CrossRef APIs

## Deliverables

- Working codebase with modular functions or services
- Configuration file (YAML/JSON) for thresholds and backend selection
- Unit tests for all major functions
- CLI or API interface to run the system

---

This document is suitable for an AI or software engineer to implement an automated recursive academic literature search system aligned with a specified research plan.

