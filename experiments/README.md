# Academic Literature Search System

An AI-powered literature search system that automatically discovers, scores, and expands academic papers based on a research plan using semantic similarity and citation network analysis.

## Recent Updates ✨

**v2.1 - Enhanced API Reliability (Current)**

- ✅ **Comprehensive Exponential Backoff**: All Semantic Scholar API requests now include robust retry logic
- ✅ **Improved Rate Limit Handling**: Automatic detection and graceful handling of HTTP 429 responses  
- ✅ **Enhanced Error Recovery**: 5-retry exponential backoff with delays: 5s → 10s → 20s → 40s → 80s
- ✅ **Better Logging**: Detailed debug information for failed requests and data quality metrics

## Overview

This system implements an automated recursive literature search that:

- Extracts key search terms from a research plan using NLP
- Searches multiple academic databases (Semantic Scholar, PubMed, arXiv)
- Scores papers using semantic similarity embeddings
- Expands results through citation network analysis (references + citations)
- Produces a ranked list of highly relevant academic papers

## Key Features

### 🔍 **Multi-Database Search**

- **Semantic Scholar**: Comprehensive academic database with citation data
- **PubMed**: Medical and life sciences literature
- **arXiv**: Preprints in physics, mathematics, computer science, and more

### 🧠 **AI-Powered Term Extraction**

- Uses spaCy NLP to extract meaningful noun phrases from research plans
- Ranks phrases by semantic similarity to the research objective
- Focuses on 1-4 word phrases for optimal search precision

### 📊 **Semantic Scoring**

- Employs sentence transformers for document relevance scoring
- Uses `all-MiniLM-L12-v2` embeddings for high-quality semantic understanding
- Adaptive quantile-based filtering (default: 85th percentile)

### 🔗 **Citation Network Expansion**

- **Reference Expansion**: Finds papers cited by relevant documents (backward citations)
- **Citation Expansion**: Finds papers that cite relevant documents (forward citations)
- Comprehensive network analysis for complete literature coverage

### 🚀 **Robust API Integration**

- Comprehensive exponential backoff for all Semantic Scholar requests
- Proper rate limiting for all academic APIs  
- API key support for faster access (NCBI, CORE)
- Intelligent retry mechanisms with exponential backoff (5s, 10s, 20s, 40s, 80s)
- Graceful handling of rate limit responses (HTTP 429)

## System Architecture

```
Research Plan Input
       ↓
Term Extraction (spaCy + Embeddings)
       ↓
Multi-Database Search (Semantic Scholar, PubMed, arXiv)
       ↓
Deduplication & Semantic Scoring
       ↓
High-Scoring Document Selection (85th percentile)
       ↓
Citation Network Expansion (References + Citations)
       ↓
Final Scoring & Ranking
       ↓
JSON Output with Ranked Results
```

## Installation

### Prerequisites

- Python 3.8+
- spaCy English model: `python -m spacy download en_core_web_sm`

### Dependencies

```bash
pip install sentence-transformers spacy requests numpy tqdm python-dotenv
```

Required packages:

- `sentence-transformers`
- `spacy`
- `requests`
- `numpy`
- `tqdm`
- `python-dotenv`

### Environment Setup

Create a `.env` file with API keys:

```env
NCBI_API_KEY=your_ncbi_api_key_here
CORE_API_KEY=your_core_api_key_here
```

## Usage

### 1. Prepare Research Plan

Create a `plan.json` file with your research objectives:

```json
{
    "outcomes": [
      "Literature review summarizing key findings on machine learning approaches for protein structure prediction.",
      "Data analysis report detailing experimental results on models for genomic sequence analysis."
    ],
    "objectives": [
      "Investigate machine learning approaches for protein structure prediction",
      "Analyze deep learning models for genomic sequence analysis"
    ],
    "key_areas": [
    "bioinformatics",
    "computational biology",
    "neural networks"
  ],
  "questions": [
    "What are the latest advances in AI-driven protein folding?",
    "How effective are transformer models for DNA sequence analysis?"
  ]
}
```

### 2. Run the Search

```bash
python search.py
```

### 3. Review Results

The system outputs `output.json` containing ranked papers with:

- Title, abstract, authors
- Relevance scores
- Source database
- Discovery method (initial search, reference, citation, or both)
- External IDs (DOI, PMID, arXiv ID)

## Configuration

Edit these variables in `search.py`:

```python
# Core Configuration
SIMILARITY_QUANTILE = 0.85    # Keep top 15% of papers
TOP_K_TERMS = 5              # Number of search terms to extract
SEARCH_LIMIT = 50            # Papers per term per database
YEAR_RANGE = (2000, 2025)    # Publication year filter

# API Reliability Configuration  
MAX_RETRIES = 5              # Number of retry attempts for failed requests
BACKOFF_BASE = 5             # Base delay in seconds for exponential backoff
                            # Delays: 5s, 10s, 20s, 40s, 80s
```

## Detailed Workflow

### Phase 1: Term Extraction

1. **Text Processing**: Loads research plan from `plan.json`
2. **NLP Analysis**: Uses spaCy to identify noun chunks (key phrases)
3. **Semantic Ranking**: Ranks phrases by similarity to research plan using embeddings
4. **Term Selection**: Selects top N terms for database searches

### Phase 2: Initial Search

1. **Multi-Database Query**: Searches each term across all databases
2. **Data Normalization**: Standardizes results from different APIs
3. **Deduplication**: Removes duplicate papers based on title similarity
4. **Source Tracking**: Tags each paper with its originating database

### Phase 3: Semantic Filtering

1. **Embedding Generation**: Creates embeddings for titles + abstracts
2. **Similarity Scoring**: Computes cosine similarity with research plan
3. **Quantile Filtering**: Keeps only papers above 85th percentile score
4. **Quality Control**: Reports papers with missing titles/abstracts

### Phase 4: Citation Network Expansion

1. **Reference Extraction**: Extracts cited papers from high-scoring documents
2. **Citation Discovery**: Finds papers that cite high-scoring documents
3. **Network Combination**: Merges and deduplicates reference and citation lists
4. **Abstract Retrieval**: Fetches full details for expansion papers

### Phase 5: Final Ranking

1. **Expansion Scoring**: Scores all expansion papers against research plan
2. **Final Filtering**: Applies quantile filter to expansion results
3. **Method Tracking**: Tags papers by discovery method
4. **Output Generation**: Creates ranked JSON with complete metadata

## Output Format

The `output.json` file contains an array of papers with:

```json
[
  {
    "title": "Deep Learning for Protein Structure Prediction",
    "abstract": "This paper presents...",
    "authors": [{"name": "Jane Doe"}, {"name": "John Smith"}],
    "year": 2023,
    "score": 0.89,
    "source": "semantic_scholar",
    "expansion_type": "citation",
    "externalIds": {
      "DOI": "10.1000/xyz123",
      "PMID": "12345678"
    },
    "paperId": "abc123xyz"
  }
]
```

## API Rate Limits & Exponential Backoff

### Semantic Scholar

- **Rate Limit**: 5 requests/second (unofficial)
- **Exponential Backoff**: 5s → 10s → 20s → 40s → 80s delays
- **Max Retries**: 5 attempts per request
- **Implementation**: All three API endpoints now include robust retry logic
  - Paper search: `query_semantic_scholar()`
  - Citation lookup: `extract_citing_papers()`
  - Abstract fetching: `fetch_abstract()`

### PubMed (NCBI)

- **Without API Key**: 3 requests/second
- **With API Key**: 10 requests/second
- **Best Practice**: Use NCBI_API_KEY environment variable for faster searches
- **Backoff**: Same exponential strategy as Semantic Scholar

### arXiv

- **Rate Limit**: 1 request every 5 seconds (strictly enforced)
- **Best Practice**: Conservative 5-second delays implemented
- **Backoff**: Exponential backoff for 429 responses

## Performance Considerations

### Typical Execution Time

- **Small search** (5 terms, 20 papers each): 2-3 minutes
- **Medium search** (5 terms, 50 papers each): 5-8 minutes
- **Large search** (10 terms, 100 papers each): 15-20 minutes

### Bottlenecks

1. **Citation expansion**: Individual API calls for each reference/citation
2. **arXiv rate limits**: 5-second delays between requests
3. **Embedding computation**: Scales with number of papers

### Optimization Tips

- Use API keys for faster PubMed access
- Adjust `SEARCH_LIMIT` based on quality vs. speed needs
- Consider running during off-peak hours for better API performance

## Error Handling & Robustness

The system includes comprehensive error handling for production use:

### API Reliability

- **Exponential Backoff**: All Semantic Scholar requests use 5-retry exponential backoff
- **Rate Limit Detection**: Automatic detection and handling of HTTP 429 responses
- **Graceful Degradation**: Continues operation even if individual API calls fail
- **Connection Timeouts**: Robust handling of network connectivity issues

### Data Quality Management

- **Missing Abstracts**: Handles papers without abstracts or metadata gracefully
- **Malformed Responses**: Validates API responses and handles parsing errors
- **Deduplication**: Prevents processing duplicate papers across databases
- **Progress Tracking**: Real-time progress updates during long operations

### Logging & Diagnostics

- **Debug Information**: Detailed logging for failed abstract retrievals
- **Performance Metrics**: Tracks success rates and data quality statistics
- **Rate Limit Alerts**: Clear messages when rate limits are encountered
- **Retry Notifications**: Informative backoff delay announcements

## Troubleshooting

### Common Issues

**No results found:**

- Check `plan.json` format and content
- Verify internet connection
- Ensure search terms aren't too specific

**API rate limiting (updated):**

- System now includes comprehensive exponential backoff for all Semantic Scholar requests
- Rate limits are automatically detected and handled with increasing delays
- No manual intervention required - system will retry up to 5 times per request
- Monitor console output for "Rate limited. Retrying in Xs..." messages
- If issues persist, consider reducing `SEARCH_LIMIT` or increasing `BACKOFF_BASE`

**Missing spaCy model:**

```bash
python -m spacy download en_core_web_sm
```

**Memory issues with large searches:**

- Reduce `SEARCH_LIMIT`
- Process in smaller batches
- Monitor system resources

## Implementation Details

### Term Extraction Algorithm

Based on the methodology document, the system implements:

1. **Noun Phrase Extraction**: Uses spaCy's linguistic analysis to identify meaningful noun chunks
2. **Length Filtering**: Keeps phrases between 1-4 words for optimal specificity
3. **Semantic Ranking**: Ranks candidates using cosine similarity with the research plan
4. **Top-K Selection**: Selects the most relevant terms for database queries

### Scoring and Ranking

Following the methodology document's recommendations:

```python
# Adaptive quantile-based thresholding
scores = np.array([doc['score'] for doc in documents])
dynamic_cutoff = np.quantile(scores, 0.85)  # keep top 15%
high_scoring_docs = [doc for doc in documents if doc['score'] >= dynamic_cutoff]
```

### Citation Network Analysis

The system implements both backward and forward citation analysis:

- **References**: Papers cited by high-scoring documents (foundational work)
- **Citations**: Papers that cite high-scoring documents (recent developments)
- **Deduplication**: Prevents processing the same paper multiple times

## Extending the System

### Adding New Databases

1. Create a new query function following the pattern of `query_pubmed()`
2. Add parser for the new API response format
3. Update the main search loop to include the new database

### Custom Scoring Methods

Replace the semantic similarity scoring in `score_documents()` with:

- TF-IDF based scoring
- Custom domain-specific embeddings
- Hybrid scoring combining multiple methods

### Advanced Filtering

Enhance the filtering logic to include:

- Author reputation scoring
- Journal impact factor weighting
- Citation count consideration
- Publication venue filtering

## Technical Architecture

### Core Libraries

- **spaCy**: NLP processing and noun phrase extraction
- **sentence-transformers**: Semantic embeddings and similarity computation
- **requests**: HTTP API interactions
- **numpy**: Numerical computations for scoring
- **tqdm**: Progress tracking for long operations
- **python-dotenv**: Environment variable management

### API Integration

- **Semantic Scholar**: Primary source with citation data
- **PubMed/NCBI**: Medical literature via eUtils API
- **arXiv**: Preprint repository via REST API

### Data Flow

1. Research plan → Term extraction → Database queries
2. Raw results → Normalization → Deduplication → Scoring
3. High-scoring papers → Citation expansion → Final ranking
4. Structured output with metadata and provenance tracking

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

Areas for contribution:

- Additional database integrations
- Enhanced term extraction algorithms
- Performance optimizations
- Better error handling and recovery
- Unit tests and integration tests

## License

[Your chosen license]

## Support

For issues and questions:

- Check the troubleshooting section
- Review the methodology document: `search_methodology_document.md`
- Open an issue on GitHub
- Contact: [your-email@domain.com]
