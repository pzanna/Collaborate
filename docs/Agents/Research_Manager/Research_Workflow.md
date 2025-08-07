### Workflow for Automated PhD-Level Literature Review on Avian Neuron Culturing

This workflow is designed to be orchestrated unattended by a combination of business logic (rule-based decision-making for process control, error handling, and progression) and an AI model (for semantic processing, summarization, and synthesis). It assumes an orchestration platform (e.g., Apache Airflow, AWS Step Functions, or a custom script-based system) that can execute API calls, run AI inferences (via models like Grok or similar LLMs), and manage state. The workflow processes the provided research plan JSON as input, focusing on sourcing literature from the specified databases, addressing key areas, questions, and objectives, and producing the defined outcomes within the 14-hour timeline.

The total timeline is enforced by allocating execution slots to phases (e.g., via timed tasks or quotas), with business logic monitoring progress and aborting/retrying if thresholds are exceeded (e.g., API rate limits). AI model integration handles natural language tasks like query generation, relevance filtering, and report writing. All steps are API-driven for unattended operation; no manual intervention is required. Error handling includes retries for network issues and fallbacks (e.g., if one source fails, prioritize others).

#### Assumptions and Prerequisites
- **API Access**: Use public APIs for sources (PubMed E-Utilities, ArXiv API, Semantic Scholar API, CORE API, CrossRef API). Obtain API keys if needed (e.g., for rate-limited access).
- **AI Model**: An LLM (e.g., Grok API or equivalent) for query refinement, summarization, and synthesis. Input prompts will be templated for consistency.
- **Tools/Environment**: Python-based execution environment with libraries like `requests` for API calls, `pandas` for data structuring, and `PyPDF2` or similar for parsing PDFs if full texts are fetched.
- **Storage**: Temporary cloud storage (e.g., S3) for fetched papers, metadata, and intermediate outputs.
- **Budget/Timeline Enforcement**: Business logic caps API calls (e.g., max 100 per source) and phases to fit hours (assuming 1 hour ≈ 1,000 API calls + AI inferences).
- **Ethical Considerations**: Only fetch open-access or metadata; respect robots.txt and fair use. Log all queries for traceability.

#### High-Level Phases and Timeline Allocation
The workflow mirrors the plan's phases, with business logic sequencing them:
1. **Literature Search (3 hours)**: Query sources and collect metadata.
2. **Data Collection (5 hours)**: Fetch and process content.
3. **Analysis (4 hours)**: AI-driven evaluation and extraction.
4. **Synthesis (2 hours)**: Compile outcomes.
Total: 14 hours, with parallelization where possible (e.g., multi-threaded API calls across sources).

#### Detailed Workflow Steps
The workflow is a directed acyclic graph (DAG) of tasks, orchestrated sequentially with branches for parallelism. Each step includes:
- **Inputs/Outputs**: Data flow.
- **Business Logic**: Rules for decisions.
- **AI Model Role**: Where inference is used.
- **Execution Details**: API/code snippets (pseudocode for illustration; implement in orchestration tool).

1. **Parse Research Plan (Setup, <1 min)**
   - **Inputs**: JSON research plan.
   - **Outputs**: Extracted elements (sources list, key_areas, questions, objectives as strings/arrays).
   - **Business Logic**: Validate JSON structure; if invalid, abort with error report.
   - **AI Model Role**: None.
   - **Execution**: Use code to parse JSON (e.g., `json.loads()` in Python).

2. **Generate Search Queries (Literature Search Phase, ~30 min)**
   - **Inputs**: Key_areas, questions, objectives.
   - **Outputs**: List of refined queries (e.g., 5-10 per source, tailored to API formats).
   - **Business Logic**: Limit to 10 queries max; prioritize questions as primary keywords.
   - **AI Model Role**: Prompt AI with: "Generate precise search queries for [source] API based on these key areas [list], questions [list], and objectives [list]. Focus on Avian neuron culturing, common ingredients, cost, etc. Output as list of strings."
   - **Execution**: AI inference call; store queries (e.g., ["avian cerebral neurons growth requirements site:pubmed.ncbi.nlm.nih.gov", "cost-effective media ingredients arxiv"]).

3. **Query Sources and Collect Metadata (Literature Search Phase, ~2.5 hours)**
   - **Inputs**: Sources list, generated queries.
   - **Outputs**: Metadata dataset (e.g., CSV/JSON with title, abstract, DOI, authors, year, relevance score for 50-200 papers total).
   - **Business Logic**: Parallelize across sources (e.g., 5 threads). Cap at 50 results per source. If <10 results, broaden query (e.g., remove filters). Handle rate limits with exponential backoff.
   - **AI Model Role**: None here; AI filters in next step.
   - **Execution**: API calls in parallel:
     - PubMed: `requests.get('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmax=50')` → Fetch IDs, then esummary for metadata.
     - ArXiv: `requests.get('http://export.arxiv.org/api/query?search_query={query}&max_results=50')` → Parse XML for entries.
     - Semantic Scholar: `requests.get('https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=50')`.
     - CORE: `requests.get('https://api.core.ac.uk/v3/search/works?q={query}&pageSize=50')`.
     - CrossRef: `requests.get('https://api.crossref.org/works?query={query}&rows=50')`.
     - Store metadata; log query success.

4. **Filter Relevant Papers (Data Collection Phase, ~1 hour)**
   - **Inputs**: Metadata dataset.
   - **Outputs**: Filtered list (top 20-50 papers, with relevance scores >0.7).
   - **Business Logic**: If total papers <20, retry broader queries. Sort by year (prioritize recent) and citations if available.
   - **AI Model Role**: Batch-process abstracts with prompt: "Score relevance (0-1) of this abstract [text] to Avian neuron culturing requirements, common ingredients, and questions [list]. Output: score and 1-sentence rationale."
   - **Execution**: AI inferences in batches; use pandas to filter/sort.

5. **Fetch Full Content (Data Collection Phase, ~4 hours)**
   - **Inputs**: Filtered DOIs/URLs.
   - **Outputs**: Full texts or extended abstracts (stored as PDFs/text).
   - **Business Logic**: Prioritize open-access; fallback to abstracts if full text unavailable. Parallel downloads; cap at 30 full texts to fit time.
   - **AI Model Role**: None.
   - **Execution**: Use APIs/DOIs:
     - PubMed: Efetch for PMC full texts if OA.
     - ArXiv: Download PDFs via links.
     - Others: Use Unpaywall API (`https://api.unpaywall.org/{doi}`) for OA links, then `requests` to download.
     - Extract text with tools like `pdfplumber` in code.

6. **Extract Key Information (Analysis Phase, ~3 hours)**
   - **Inputs**: Full texts/abstracts, key_areas, questions, objectives.
   - **Outputs**: Structured extractions (e.g., JSON with sections: findings per question, key areas coverage, metrics like costs, ingredients).
   - **Business Logic**: Chunk texts (e.g., 2000 tokens per AI call). If extraction incomplete, re-query source.
   - **AI Model Role**: Prompt per chunk: "Extract key findings from this text [chunk] related to [specific question/key area/objective]. Output as bullet points with citations (e.g., page/section)."
   - **Execution**: Batch AI calls; aggregate into dataset (e.g., pandas DataFrame with columns: question, finding, source_paper).

7. **Analyze and Compare (Analysis Phase, ~1 hour)**
   - **Inputs**: Structured extractions.
   - **Outputs**: Analysis report sections (e.g., comparisons, optimizations, risks).
   - **Business Logic**: Ensure coverage of all questions/objectives; if gaps (>20% uncovered), trigger supplemental search (loop back to Step 3 with refined queries).
   - **AI Model Role**: Holistic prompt: "Analyze extractions [data] for comparisons (e.g., common vs. commercial media), optimizations (pH/factors), risks. Address questions [list] and objectives [list]. Output structured sections."
   - **Execution**: Single or few AI inferences; include quantitative elements if data allows (e.g., average costs from texts).

8. **Synthesize Outcomes (Synthesis Phase, ~2 hours)**
   - **Inputs**: All prior outputs, outcomes list.
   - **Outputs**: Final documents (e.g., PDFs/Markdown for each outcome).
   - **Business Logic**: Map to outcomes (e.g., lit review = summary of key findings; data report = experimental metrics from literature). Check timeline adherence; generate executive summary if over budget.
   - **AI Model Role**: Prompt per outcome: "Synthesize a PhD-level [outcome description] based on analyses [data]. Include sections on key areas [list], answers to questions [list], alignment with objectives [list]. Be comprehensive, cite sources."
   - **Execution**: AI-generated reports; compile into final ZIP/archive.

9. **Finalize and Report (Cleanup, <10 min)**
   - **Inputs**: All outputs.
   - **Outputs**: Compiled final report (single document or folder), logs (e.g., sources used, gaps, time spent).
   - **Business Logic**: Validate completeness (e.g., all outcomes generated); email/Slack notification on completion.
   - **AI Model Role**: Optional: "Generate executive summary of the literature review."
   - **Execution**: Merge files; store logs.

#### Monitoring and Orchestration Notes
- **Unattended Operation**: Run as a scheduled job; business logic uses if-then rules (e.g., "if API fails >3 times, skip source").
- **Scalability**: Parallelize API calls and AI batches to fit timeline; use queues for rate limiting.
- **Cost Optimization**: Track API/AI usage; business logic halts if exceeding implicit budgets.
- **Extensibility**: For future runs, add phases like experiment simulation if data allows.
- **Potential Enhancements**: Integrate vector databases (e.g., FAISS via code) for semantic search on fetched papers.

This workflow produces a rigorous, evidence-based literature review aligned with the plan, leveraging automation for efficiency. If implementation details or code templates are needed, provide specifics.