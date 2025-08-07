# --- search.py ---

import os
import time
import json
import requests
import numpy as np
import re
from tqdm import tqdm
import onnxruntime as ort
from transformers import AutoTokenizer
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass
class SearchQuery:
    """Search query data model for literature search requests."""
    lit_review_id: str
    plan_id: str = ""
    research_plan: Dict[str, Any] = field(default_factory=dict)
    query: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    sources: List[str] = field(default_factory=list)
    max_results: int = 50
    search_depth: str = "standard"


# Import search engine functions
from search_engines import (
    query_openalex, query_pubmed, query_arxiv, query_core,
    SIMILARITY_QUANTILE, TOP_K_TERMS, MAX_RETRIES, BACKOFF_BASE, SEARCH_LIMIT, YEAR_RANGE,
    NCBI_API_KEY, OPENALEX_EMAIL, CORE_API_KEY
)

# Load environment variables (needed for this file's functions)
# Look for .env file in parent directory (repository root)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Print API key status
print(f"NCBI API Key: {'✓ Found' if NCBI_API_KEY else '✗ Not found'}")
print(f"OpenAlex Email: {OPENALEX_EMAIL if OPENALEX_EMAIL else '✗ Not configured'}")
print(f"CORE API Key: {'✓ Found' if CORE_API_KEY else '✗ Not found'}")

# --- Rank Phrases ---
def rank_phrases(plan, phrases, top_k):
    print("Loading tokenizer and ONNX model...")
    # Load tokenizer and ONNX session
    tokenizer = AutoTokenizer.from_pretrained("./onnx_models/")
    session = ort.InferenceSession("./onnx_models/model.onnx")

    print("Reviewing results...")
    def get_embedding(text: str) -> np.ndarray:
        try:
            if not text or not text.strip():
                # Return zero vector for empty text
                print("Empty text provided, returning zero vector")
                return np.zeros(384)  # MiniLM-L6-v2 has 384 dimensions
            
            # Truncate very long text to avoid memory issues
            max_length = 512  # BERT-style models typically handle 512 tokens max
            if len(text) > max_length * 4:  # Rough estimate: 4 chars per token
                text = text[:max_length * 4]
                print(f"Truncated text to {len(text)} characters")
            
            # print(f"Tokenizing text of length {len(text)}")
            inputs = tokenizer(text, return_tensors="np", padding=True, truncation=True, max_length=max_length)
            
            # print("Running ONNX inference...")
            outputs = session.run(None, {
                "input_ids": inputs["input_ids"],
                "attention_mask": inputs["attention_mask"]
            })
            
            # print(f"ONNX inference completed, output shape: {outputs[0].shape}")
            result = np.mean(outputs[0], axis=1).squeeze()
            # print(f"Final embedding shape: {result.shape}")
            return result
            
        except Exception as e:
            print(f"Error in get_embedding: {e}")
            print(f"Text that caused error: '{text[:100]}...'")
            # Return zero vector as fallback
            return np.zeros(384)
        
    print("Computing embeddings...")
    # Compute average embedding for all search terms
    query_embeddings = []
    for term in phrases:
        try:
            embedding = get_embedding(term)
            if np.any(embedding):  # Only add non-zero embeddings
                query_embeddings.append(embedding)
        except Exception as e:
            print(f"Failed to compute embedding for term '{term}': {e}")

    if not query_embeddings:
        print("No valid query embeddings generated, skipping ranking")
        raise ValueError("No valid query embeddings")
    
    # Compute plan embedding for comparison
    print("Computing plan embedding...")
    plan_embedding = get_embedding(plan)
    
    # Compute cosine similarity between each phrase and the plan
    scores = []
    for embedding in query_embeddings:
        # Compute cosine similarity using numpy with safety checks
        dot_product = np.dot(plan_embedding, embedding)
        norm_plan = np.linalg.norm(plan_embedding)
        norm_embedding = np.linalg.norm(embedding)
        
        # Avoid division by zero
        if norm_plan == 0 or norm_embedding == 0:
            similarity_score = 0.0
        else:
            similarity_score = dot_product / (norm_plan * norm_embedding)
        scores.append(float(similarity_score))

    return sorted(zip(phrases, scores), key=lambda x: x[1], reverse=True)[:top_k]

# --- Document Scoring ---
def score_documents(plan, docs):
    missing_title = sum(1 for doc in docs if not doc.get('title'))
    missing_abstract = sum(1 for doc in docs if doc.get('abstract') is None)
    if missing_title or missing_abstract:
        print(f"[WARN] {missing_title} docs missing title, {missing_abstract} docs missing abstract.")
    
    # Load tokenizer and ONNX session for document scoring
    tokenizer = AutoTokenizer.from_pretrained("./onnx_models/")
    session = ort.InferenceSession("./onnx_models/model.onnx")
    
    def get_embedding(text: str) -> np.ndarray:
        try:
            if not text or not text.strip():
                # Return zero vector for empty text
                return np.zeros(384)  # MiniLM-L6-v2 has 384 dimensions
            
            # Truncate very long text to avoid memory issues
            max_length = 512  # BERT-style models typically handle 512 tokens max
            if len(text) > max_length * 4:  # Rough estimate: 4 chars per token
                text = text[:max_length * 4]
            
            inputs = tokenizer(text, return_tensors="np", padding=True, truncation=True, max_length=max_length)
            
            outputs = session.run(None, {
                "input_ids": inputs["input_ids"],
                "attention_mask": inputs["attention_mask"]
            })
            
            result = np.mean(outputs[0], axis=1).squeeze()
            return result
            
        except Exception as e:
            print(f"Error in get_embedding for document scoring: {e}")
            # Return zero vector as fallback
            return np.zeros(384)
    
    texts = [
        (str(doc.get('title')) if doc.get('title') else "") + ". " + (str(doc.get('abstract')) if doc.get('abstract') else "")
        for doc in docs
    ]
    
    # Get plan embedding using ONNX model
    plan_emb = get_embedding(plan)
    
    # Get document embeddings using ONNX model
    doc_embeddings = []
    for text in texts:
        doc_emb = get_embedding(text)
        doc_embeddings.append(doc_emb)
    
    # Compute cosine similarity scores
    scores = []
    for doc_emb in doc_embeddings:
        # Compute cosine similarity using numpy with safety checks
        dot_product = np.dot(plan_emb, doc_emb)
        norm_plan = np.linalg.norm(plan_emb)
        norm_doc = np.linalg.norm(doc_emb)
        
        # Avoid division by zero
        if norm_plan == 0 or norm_doc == 0:
            similarity = 0.0
        else:
            similarity = dot_product / (norm_plan * norm_doc)
        scores.append(float(similarity))
    
    for doc, score in zip(docs, scores):
        doc['score'] = score
    print(f"Scored {len(docs)} documents using ONNX model")
    return docs

def filter_high_docs(docs, quantile):
    scores = np.array([d['score'] for d in docs])
    cutoff = np.quantile(scores, quantile)
    print(f"Quantile cutoff for scores: {cutoff:.3f} (quantile={quantile})")
    return [d for d in docs if d['score'] >= cutoff], cutoff

# --- Reference and Citation Expansion ---
def extract_references(docs):
    refs = set()
    docs_with_refs = 0
    docs_without_refs = 0
    for doc in docs:
        references = doc.get('references', [])
        if references is None:
            references = []
        if references:
            docs_with_refs += 1
            for ref in references:
                # Handle different reference formats
                if isinstance(ref, dict):
                    # CORE/Semantic Scholar format
                    rid = ref.get('paperId')
                    if rid:
                        refs.add(rid)
                elif isinstance(ref, str):
                    # OpenAlex format - extract ID from URL
                    if ref.startswith('https://openalex.org/'):
                        refs.add(ref.split('/')[-1])
        else:
            docs_without_refs += 1
    print(f"Reference extraction: {docs_with_refs} docs with refs, {docs_without_refs} docs without refs")
    return list(refs)

def extract_citing_papers(docs, limit_per_paper=10):
    """Extract papers that cite the given documents using OpenAlex API."""
    citing_paper_ids = set()
    docs_with_citations = 0
    total_citations = 0
    
    # Check if we have a valid email for OpenAlex
    if not OPENALEX_EMAIL:
        print("[WARN] No OpenAlex email configured. This may cause 403 errors.")
        print("[INFO] Set OPENALEX_EMAIL environment variable to avoid rate limiting.")
    else:
        print(f"[INFO] Using OpenAlex email: {OPENALEX_EMAIL}")
    
    for doc in docs:
        paper_id = doc.get('paperId')
        if not paper_id:
            continue
        
        # Convert paper_id to string if it's not already
        paper_id = str(paper_id)
            
        # Ensure we have a full OpenAlex ID
        if not paper_id.startswith('https://openalex.org/'):
            paper_id = f"https://openalex.org/{paper_id}"
        
        print(f"[DEBUG] Fetching citations for paper: {paper_id}")
            
        retries = 0
        while retries < MAX_RETRIES:
            try:
                # Use OpenAlex cites filter to find papers citing this one
                url = "https://api.openalex.org/works"
                params = {
                    'filter': f'cites:{paper_id}',
                    'per_page': limit_per_paper,
                }
                
                # Only add mailto if we have a valid email
                if OPENALEX_EMAIL:
                    params['mailto'] = OPENALEX_EMAIL
                
                print(f"[DEBUG] Request URL: {url}")
                print(f"[DEBUG] Request params: {params}")
                
                time.sleep(0.1)  # OpenAlex rate limiting (10 req/sec)
                r = requests.get(url, params=params)
                
                print(f"[DEBUG] Response status: {r.status_code}")
                if r.status_code != 200:
                    print(f"[DEBUG] Response text: {r.text[:200]}...")  # First 200 chars of error
                
                if r.status_code == 200:
                    data = r.json()
                    results = data.get('results', [])
                    if results:
                        docs_with_citations += 1
                        for result in results:
                            citing_id = result.get('id', '').replace('https://openalex.org/', '')
                            if citing_id and citing_id != doc.get('paperId'):
                                citing_paper_ids.add(citing_id)
                                total_citations += 1
                    break  # Success, exit retry loop
                elif r.status_code == 429:
                    delay = BACKOFF_BASE * 2**retries
                    print(f"OpenAlex citations API rate limited. Retrying in {delay}s...")
                    time.sleep(delay)
                    retries += 1
                elif r.status_code == 403:
                    print(f"OpenAlex API access forbidden (403). Check email configuration and API usage.")
                    print(f"Paper ID: {paper_id}")
                    break  # Don't retry 403 errors
                else:
                    print(f"Failed to get citations for paper from OpenAlex: HTTP {r.status_code}")
                    break  # Non-retryable error
                    
            except Exception as e:
                print(f"Error fetching citations from OpenAlex: {e}")
                break  # Non-retryable error
        
        if retries >= MAX_RETRIES:
            print(f"Max retries exceeded for OpenAlex citations search")
    
    print(f"OpenAlex citation search: {docs_with_citations} docs had citing papers, {total_citations} total papers found")
    return list(citing_paper_ids)

def fetch_abstract(paper_id):
    """Fetch paper details from OpenAlex API using paper ID."""
    retries = 0
    while retries < MAX_RETRIES:
        # Convert paper_id to string if it's not already
        paper_id = str(paper_id)
        
        # Clean the paper ID to get just the ID part
        if paper_id.startswith('https://openalex.org/'):
            clean_id = paper_id.replace('https://openalex.org/', '')
        else:
            clean_id = paper_id
        
        # OpenAlex API endpoint for getting work by ID
        url = f"https://api.openalex.org/works/{clean_id}"
        
        params = {}
        # Only add mailto if we have a valid email
        if OPENALEX_EMAIL:
            params['mailto'] = OPENALEX_EMAIL
        
        time.sleep(0.1)  # OpenAlex rate limiting
        r = requests.get(url, params=params)
        
        if r.status_code == 200:
            try:
                d = r.json()
            except requests.exceptions.JSONDecodeError:
                print(f"Failed to parse JSON for paper {paper_id} (empty response)")
                return None
            except Exception as e:
                print(f"Failed to parse JSON for paper {paper_id}: {e}")
                return None
                
            title = d.get("title") or d.get("display_name")
            
            # Convert abstract inverted index to plain text
            abstract_text = ""
            abstract_index = d.get('abstract_inverted_index', {})
            if abstract_index:
                # Reconstruct abstract from inverted index
                words = [""] * 1000  # Pre-allocate for efficiency
                max_pos = 0
                for word, positions in abstract_index.items():
                    for pos in positions:
                        if pos < len(words):
                            words[pos] = word
                            max_pos = max(max_pos, pos)
                abstract_text = " ".join(words[:max_pos + 1]).strip()
            
            # Debug logging
            if abstract_text:
                print(f"Fetched paper {paper_id} successfully - Name: {title}, Abstract: {abstract_text[:100]}...")
            else:
                print(f"[DEBUG] Paper {paper_id}: title={'Present' if title else 'Missing'}, abstract={'Empty' if abstract_text == '' else 'None' if abstract_text is None else 'Present'}")
            
            # Extract PDF URL
            pdf_url = d.get('primary_location', {}).get('pdf_url')
            
            return {"paperId": clean_id, "title": title, "abstract": abstract_text, "url": pdf_url}
        elif r.status_code == 429:
            delay = BACKOFF_BASE * 2**retries
            print(f"OpenAlex abstract fetch rate limited. Retrying in {delay}s...")
            time.sleep(delay)
            retries += 1
        elif r.status_code == 404:
            print(f"[DEBUG] Paper {paper_id} not found in OpenAlex")
            break  # Paper doesn't exist, no point retrying
        else:
            print(f"[DEBUG] Failed to fetch paper {paper_id} from OpenAlex: HTTP {r.status_code}")
            break  # Non-retryable error
    
    if retries >= MAX_RETRIES:
        print(f"[DEBUG] Max retries exceeded for OpenAlex paper {paper_id}")
    
    return None

def fetch_and_score_papers(paper_ids, plan_text, expansion_type, description):
    """Fetch abstracts for papers and score them against the plan."""
    if not paper_ids:
        print(f"[WARN] {description}: No papers to fetch. Skipping.")
        return []
    
    print(f"{description}: Fetching {len(paper_ids)} papers...")
    docs = []
    failed_fetches = 0
    empty_abstracts = 0
    null_abstracts = 0
    
    for pid in tqdm(paper_ids, desc=f"{description}: Fetching abstracts"):
        d = fetch_abstract(pid)
        if d is None:
            failed_fetches += 1
        elif not d.get('abstract'):
            if d.get('abstract') is None:
                null_abstracts += 1
            else:
                empty_abstracts += 1
        else:
            d['expansion_type'] = expansion_type
            docs.append(d)
    
    print(f"{description}: Fetched {len(docs)} abstracts with non-empty content.")
    print(f"{description}: Data quality summary:")
    print(f"  - Successful fetches: {len(paper_ids) - failed_fetches}")
    print(f"  - Failed API calls: {failed_fetches}")
    print(f"  - Null abstracts: {null_abstracts}")
    print(f"  - Empty abstracts: {empty_abstracts}")
    print(f"  - Valid abstracts: {len(docs)}")
    print(f"  - Abstract availability rate: {len(docs)/len(paper_ids)*100:.1f}%")
    
    if not docs:
        print(f"[WARN] {description}: No docs found. Skipping scoring.")
        return []
    
    print(f"{description}: Scoring {len(docs)} abstracts...")
    scored_docs = score_documents(plan_text, docs)
    high_docs, cutoff = filter_high_docs(scored_docs, SIMILARITY_QUANTILE)
    print(f"{description}: {len(high_docs)} docs above quantile cutoff ({SIMILARITY_QUANTILE}) (cutoff={cutoff:.3f})")
    
    return high_docs

# --- Main Pipeline ---
async def search_source(source: str, search_query: SearchQuery) -> List[Dict[str, Any]]:

    # Extract relevant information from the search query
    plan_sections = search_query.research_plan.get("outcomes", []) + \
                    search_query.research_plan.get("objectives", []) + \
                    search_query.research_plan.get("key_areas", []) + \
                    search_query.research_plan.get("questions", [])
    plan_text = " ".join(plan_sections)
    candidates = search_query.query

    ranked = rank_phrases(plan_text, candidates, TOP_K_TERMS)
    top_terms = [term for term, _ in ranked]
    print(f"Top {TOP_K_TERMS} terms: {top_terms}")
    if not top_terms:
        print("[WARN] No top terms after ranking. Exiting.")
        return []

    print("Querying initial papers from all databases...")
    all_docs = []
    
    # Define database queries
    databases = [
        ('OpenAlex', query_openalex, 'openalex'),
        ('PubMed', query_pubmed, 'pubmed'),
        ('arXiv', query_arxiv, 'arxiv'),
        ('CORE', query_core, 'core')
    ]
    
    for term in top_terms:
        print(f"Searching for term: '{term}'")
        for db_name, query_func, source_name in databases:
            papers = query_func(term)
            print(f"  {db_name}: {len(papers)} papers found.")
            for paper in papers:
                paper['source'] = source_name
            all_docs.extend(papers)
        
    print(f"Total papers found across all databases: {len(all_docs)}")
    if not all_docs:
        print("[WARN] No papers found for any top term across all databases. Exiting.")
        return []

    # Remove duplicates and score documents
    print("Removing duplicates and scoring documents...")
    seen_titles = set()
    unique_docs = []
    
    for doc in all_docs:
        title = doc.get('title', '')
        if title and isinstance(title, str):
            # Normalize title for comparison
            normalized_title = re.sub(r'[^\w\s]', '', title.lower()).strip()
            if normalized_title not in seen_titles:
                seen_titles.add(normalized_title)
                unique_docs.append(doc)
    
    print(f"After deduplication: {len(unique_docs)} unique papers")
    
    if not unique_docs:
        print("[WARN] No unique papers after deduplication. Exiting.")
        return []
    
    # Score and filter documents
    scored_docs = score_documents(plan_text, unique_docs)
    high_docs, cutoff = filter_high_docs(scored_docs, SIMILARITY_QUANTILE)
    print(f"Docs above quantile cutoff ({SIMILARITY_QUANTILE}): {len(high_docs)} (cutoff={cutoff:.3f})")
    
    if not high_docs:
        print("[WARN] No high scoring docs after filtering. Exiting.")
        return []

    print(f"Top score cutoff: {cutoff:.3f}. Expanding via references and citations...")
    
    # Extract references and citations from high-scoring papers
    print("Extracting references...")
    paper_ids = extract_references(high_docs)
    print(f"Extracted {len(paper_ids)} unique reference paper IDs.")

    print("Extracting citing papers...")
    citing_paper_ids = extract_citing_papers(high_docs, limit_per_paper=10)
    print(f"Extracted {len(citing_paper_ids)} unique citing paper IDs.")
    
    # Combine and process expansion papers
    all_expansion_ids = list(set(paper_ids + citing_paper_ids))
    print(f"Total unique papers for expansion: {len(all_expansion_ids)} (references + citations)")
    # print(f"Reference IDs: {all_expansion_ids})")
    # Mark expansion type for each paper
    expansion_papers = []
    for pid in all_expansion_ids:
        if pid in paper_ids and pid in citing_paper_ids:
            expansion_type = 'both'
        elif pid in paper_ids:
            expansion_type = 'reference'
        else:
            expansion_type = 'citation'
        expansion_papers.append((pid, expansion_type))
    
    # Fetch and score round 1 expansion papers
    round1_docs = []
    for pid, exp_type in tqdm(expansion_papers, desc="Round 1: Fetching expansion papers"):
        d = fetch_abstract(pid)
        if d and d.get('abstract'):
            d['expansion_type'] = exp_type
            round1_docs.append(d)
    
    if round1_docs:
        print(f"Round 1: Scoring {len(round1_docs)} expansion papers...")
        scored_docs = score_documents(plan_text, round1_docs)
        high_round1_docs, cutoff1 = filter_high_docs(scored_docs, SIMILARITY_QUANTILE)
        print(f"Round 1: {len(high_round1_docs)} docs above quantile cutoff (cutoff={cutoff1:.3f})")
        
        # Round 2: Get citing papers from high-scoring round 1 papers
        print("Round 2: Extracting citing papers from round 1 results...")
        round2_citing_ids = extract_citing_papers(high_round1_docs, limit_per_paper=10)
        final_docs = fetch_and_score_papers(round2_citing_ids, plan_text, 'citation_round2', "Round 2")
    else:
        print("[WARN] No valid papers found in round 1 expansion.")
        final_docs = []

    return final_docs


if __name__ == "__main__":

    candidates = ["avian neuron culturing techniques", 
            "culturing media for avian neurons", 
            "ingredients for avian neuronal culture", 
            "biochemical properties of neuronal culturing media", 
            "impact of media formulations on neuronal viability", 
            "optimal concentrations for avian neuron growth", 
            "growth and viability assays for avian neurons", 
            "methodologies for assessing neuronal health", 
            "neuron differentiation in avian culture systems"]

    with open("plan.json") as f:
        plan_data = json.load(f)

    # Combine semantically rich fields
    plan_sections = plan_data.get("outcomes", []) + \
                    plan_data.get("objectives", []) + \
                    plan_data.get("key_areas", []) + \
                    plan_data.get("questions", [])
    print(f"Loaded plan.json: outcomes={len(plan_data.get('outcomes', []))}, objectives={len(plan_data.get('objectives', []))}, key_areas={len(plan_data.get('key_areas', []))}, questions={len(plan_data.get('questions', []))}")
    plan_text = " ".join(plan_sections)
    print(f"Combined plan text length: {len(plan_text)}")

    print(f"Extracted {len(candidates)} candidate terms.")
    if not candidates:
        print("[WARN] No candidate terms extracted. Exiting.")
        exit(1)

    search_query = SearchQuery(
        lit_review_id="example_review",
        plan_id="example_plan",
        research_plan=plan_data,
        query=candidates,
        sources=[],
        max_results=SEARCH_LIMIT,
        search_depth="standard"
    )

    # Run the search (since we can't use async in main, we'll call it synchronously)
    import asyncio
    final_docs = asyncio.run(search_source("all", search_query))
    
    with open("output.json", "w") as f:
        json.dump(final_docs, f, indent=2)
    
    # Print summary by source and expansion type
    source_counts = {}
    expansion_counts = {}
    for doc in final_docs:
        source = doc.get('source', 'unknown')
        source_counts[source] = source_counts.get(source, 0) + 1
        
        expansion_type = doc.get('expansion_type', 'initial_search')
        expansion_counts[expansion_type] = expansion_counts.get(expansion_type, 0) + 1
    
    print(f"Saved {len(final_docs)} high relevance documents.")
    print("Final results by source:")
    for source, count in source_counts.items():
        print(f"  {source}: {count} papers")
    print("Final results by discovery method:")
    for exp_type, count in expansion_counts.items():
        print(f"  {exp_type}: {count} papers")
    

