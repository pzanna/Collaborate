"""
Literature search pipeline implementation.

Contains the core search algorithms, scoring functions, and utility functions
for multi-source literature discovery and ranking.
"""

import os
import re
import time
import requests
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer
from tqdm import tqdm
from typing import Any, Dict, List
import logging

from .models import SearchQuery

# Set up logger for this module
logger = logging.getLogger(__name__)

# Import constants from local search_engines module
try:
    logger.debug("Attempting to import constants from local search_engines")
    from .search_engines import (
        SIMILARITY_QUANTILE, TOP_K_TERMS, MAX_RETRIES, BACKOFF_BASE, 
        SEARCH_LIMIT, YEAR_RANGE, NCBI_API_KEY, OPENALEX_EMAIL, CORE_API_KEY,
        query_openalex, query_pubmed, query_arxiv, query_core
    )
    logger.info("Successfully imported constants and query functions from local search_engines")
except ImportError as e:
    logger.warning(f"Failed to import from local search_engines: {e}")
    logger.info("Using fallback constants and functions")
    # Fallback constants if local module not available
    SIMILARITY_QUANTILE = 0.8
    TOP_K_TERMS = 1     # How many top search terms to use.
    MAX_RETRIES = 5     # Maximum number of retries for API calls
    BACKOFF_BASE = 5    # Starting backoff time in seconds
    SEARCH_LIMIT = 5    # Limit for search results per search term
    YEAR_RANGE = (2000, 2025)   # Default year range for searches
    NCBI_API_KEY = os.getenv('NCBI_API_KEY')
    OPENALEX_EMAIL = os.getenv('OPENALEX_EMAIL')
    CORE_API_KEY = os.getenv('CORE_API_KEY')
    
    logger.debug(f"Fallback constants set: SIMILARITY_QUANTILE={SIMILARITY_QUANTILE}, TOP_K_TERMS={TOP_K_TERMS}")
    logger.debug(f"Environment variables: NCBI_API_KEY={'Set' if NCBI_API_KEY else 'Not set'}, "
                f"OPENALEX_EMAIL={'Set' if OPENALEX_EMAIL else 'Not set'}, "
                f"CORE_API_KEY={'Set' if CORE_API_KEY else 'Not set'}")
    
    # Import fallback search functions if needed
    try:
        from .search_engines import query_openalex, query_pubmed, query_arxiv, query_core
        logger.info("Successfully imported fallback query functions from local search_engines")
    except ImportError as e2:
        logger.error(f"Failed to import fallback query functions: {e2}")
        raise ImportError("Cannot import search functions from either experiments or local modules")


class LiteratureSearchPipeline:
    """
    Literature search pipeline for multi-source search, scoring, and expansion.
    """
    
    def __init__(self):
        """Initialize the search pipeline."""
        logger.info("Initializing LiteratureSearchPipeline")
        logger.debug(f"Pipeline configuration: SIMILARITY_QUANTILE={SIMILARITY_QUANTILE}, "
                    f"TOP_K_TERMS={TOP_K_TERMS}, SEARCH_LIMIT={SEARCH_LIMIT}")
        
        # Check for required directories and files
        onnx_model_path = "./onnx_models/model.onnx"
        tokenizer_path = "./onnx_models/"
        
        if not os.path.exists(onnx_model_path):
            logger.error(f"ONNX model not found at: {onnx_model_path}")
            logger.warning("ONNX model missing - semantic similarity scoring may fail")
        else:
            logger.debug(f"ONNX model found at: {onnx_model_path}")
            
        if not os.path.exists(tokenizer_path):
            logger.error(f"Tokenizer directory not found at: {tokenizer_path}")
            logger.warning("Tokenizer missing - semantic similarity scoring may fail")
        else:
            logger.debug(f"Tokenizer directory found at: {tokenizer_path}")
        
        logger.info("LiteratureSearchPipeline initialized successfully")
    
    async def search_source(self, search_query: SearchQuery) -> List[Dict[str, Any]]:
        """
        Execute the complete literature search pipeline.
        
        Args:
            search_query: Search query parameters
            
        Returns:
            List of high-scoring literature records
        """
        logger.info(f"Starting search pipeline for query: {search_query.lit_review_id}")
        logger.debug(f"Search query details: sources={search_query.sources}, "
                    f"max_results={search_query.max_results}")

        # Extract relevant information from the search query
        # Handle both string and dict formats for research_plan
        if isinstance(search_query.research_plan, dict):
            logger.debug("Research plan is in dictionary format, extracting sections")
            plan_sections = search_query.research_plan.get("outcomes", []) + \
                            search_query.research_plan.get("objectives", []) + \
                            search_query.research_plan.get("key_areas", []) + \
                            search_query.research_plan.get("questions", [])
            plan_text = " ".join(plan_sections)
            logger.debug(f"Extracted plan text length: {len(plan_text)} characters")
        else:
            # If research_plan is a string, use it directly
            logger.debug("Research plan is in string format")
            plan_text = str(search_query.research_plan)
            logger.debug(f"Plan text length: {len(plan_text)} characters")
        
        if not plan_text.strip():
            logger.error("Empty plan text after processing research plan")
            return []

        logger.info(f"Research plan: {plan_text[:200]}{'...' if len(plan_text) > 200 else ''}")

        # Validate and prepare search candidates
        logger.info(f"🔍 DEBUG: search_query.query type: {type(search_query.query)}")
        logger.info(f"🔍 DEBUG: search_query.query value: {search_query.query}")
        if isinstance(search_query.query, list):
            logger.info(f"🔍 DEBUG: search_query.query is a list with {len(search_query.query)} items")
            candidates = [q for q in search_query.query if q and str(q).strip()]
        elif search_query.query:
            logger.info(f"🔍 DEBUG: search_query.query is not a list, converting to list")
            candidates = [str(search_query.query).strip()]
        else:
            candidates = []
            
        # If no valid candidates, try to extract from plan text
        if not candidates:
            logger.warning("No valid search query provided, attempting to extract from research plan")
            return []

        logger.debug(f"Search candidates: {candidates}")

        try:
            logger.info(f"🔍 DEBUG: About to call rank_phrases with {len(candidates)} candidates:")
            for i, candidate in enumerate(candidates):
                logger.info(f"🔍 DEBUG: Candidate {i+1}: '{candidate}' (type: {type(candidate)}, length: {len(str(candidate))})")
            ranked = rank_phrases(plan_text, candidates, TOP_K_TERMS)
            top_terms = [term for term, _ in ranked if term and term.strip()]
            logger.info(f"Top {TOP_K_TERMS} terms: {top_terms}")
            
            if not top_terms:
                logger.warning("No valid top terms after ranking. Using original candidates.")
                top_terms = candidates[:TOP_K_TERMS]
        except Exception as e:
            logger.error(f"Error during phrase ranking: {e}", exc_info=True)
            logger.warning("Falling back to original candidates")
            top_terms = [c for c in candidates if c and c.strip()][:TOP_K_TERMS]
            
        # Final validation
        if not top_terms:
            logger.error("No valid search terms available after all fallbacks")
            return []

        logger.info("Querying initial papers from all databases...")
        all_docs = []
        
        # Define database queries
        databases = [
            ('OpenAlex', query_openalex, 'openalex'),
            ('PubMed', query_pubmed, 'pubmed'),
            ('arXiv', query_arxiv, 'arxiv'),
            ('CORE', query_core, 'core')
        ]
        
        logger.debug(f"Configured databases: {[db[0] for db in databases]}")
        
        for term_idx, term in enumerate(top_terms, 1):
            logger.info(f"Searching for term {term_idx}/{len(top_terms)}: '{term}'")
            term_docs = []
            
            for db_name, query_func, source_name in databases:
                logger.debug(f"Querying {db_name} for term: '{term}'")
                try:
                    papers = query_func(term)
                    logger.info(f"  {db_name}: {len(papers)} papers found for term '{term}'")
                    
                    for paper in papers:
                        paper['source'] = source_name
                        paper['search_term'] = term
                    term_docs.extend(papers)
                    
                except Exception as e:
                    logger.error(f"Error querying {db_name} for term '{term}': {e}", exc_info=True)
                    logger.warning(f"Continuing with other databases for term '{term}'")
                    
            logger.debug(f"Total papers for term '{term}': {len(term_docs)}")
            all_docs.extend(term_docs)
            
        logger.info(f"Total papers found across all databases and terms: {len(all_docs)}")
        if not all_docs:
            logger.warning("No papers found for any top term across all databases. Exiting pipeline.")
            return []

        # Remove duplicates and score documents
        logger.info("Removing duplicates and scoring documents...")
        seen_titles = set()
        unique_docs = []
        duplicate_count = 0
        
        for doc in all_docs:
            title = doc.get('title', '')
            if title and isinstance(title, str):
                # Normalize title for comparison
                normalized_title = re.sub(r'[^\w\s]', '', title.lower()).strip()
                if normalized_title not in seen_titles:
                    seen_titles.add(normalized_title)
                    unique_docs.append(doc)
                else:
                    duplicate_count += 1
                    logger.debug(f"Duplicate found: '{title[:50]}...'")
            else:
                logger.debug(f"Skipping document with invalid title: {doc.get('source', 'unknown')}")
        
        logger.info(f"After deduplication: {len(unique_docs)} unique papers ({duplicate_count} duplicates removed)")
        
        if not unique_docs:
            logger.warning("No unique papers after deduplication. Exiting pipeline.")
            return []
        
        # Score and filter documents
        logger.info("Scoring documents against research plan...")
        try:
            scored_docs = score_documents(plan_text, unique_docs)
            high_docs, cutoff = filter_high_docs(scored_docs, SIMILARITY_QUANTILE)
            logger.info(f"Docs above quantile cutoff ({SIMILARITY_QUANTILE}): {len(high_docs)} (cutoff={cutoff:.3f})")
            
            if not high_docs:
                logger.warning("No high scoring docs after filtering. Exiting pipeline.")
                return []
        except Exception as e:
            logger.error(f"Error during document scoring: {e}", exc_info=True)
            logger.warning("Skipping similarity scoring, returning all unique documents")
            return unique_docs[:50]  # Return first 50 docs as fallback

        logger.info(f"Top score cutoff: {cutoff:.3f}. Expanding via references and citations...")
        
        # Extract references and citations from high-scoring papers
        logger.info("Extracting references...")
        try:
            paper_ids = extract_references(high_docs)
            logger.info(f"Extracted {len(paper_ids)} unique reference paper IDs.")
        except Exception as e:
            logger.error(f"Error extracting references: {e}", exc_info=True)
            paper_ids = []

        logger.info("Extracting citing papers...")
        try:
            citing_paper_ids = extract_citing_papers(high_docs, limit_per_paper=10)
            logger.info(f"Extracted {len(citing_paper_ids)} unique citing paper IDs.")
        except Exception as e:
            logger.error(f"Error extracting citing papers: {e}", exc_info=True)
            citing_paper_ids = []
        
        # Combine and process expansion papers
        all_expansion_ids = list(set(paper_ids + citing_paper_ids))
        logger.info(f"Total unique papers for expansion: {len(all_expansion_ids)} (references + citations)")
        
        if not all_expansion_ids:
            logger.warning("No expansion papers found. Returning initial high-scoring documents.")
            return high_docs
        
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
        
        logger.debug(f"Expansion paper distribution: {len([p for p in expansion_papers if p[1] == 'reference'])} references, "
                    f"{len([p for p in expansion_papers if p[1] == 'citation'])} citations, "
                    f"{len([p for p in expansion_papers if p[1] == 'both'])} both")
        
        # Fetch and score round 1 expansion papers
        logger.info("Round 1: Fetching expansion papers...")
        round1_docs = []
        fetch_errors = 0
        
        for pid, exp_type in tqdm(expansion_papers, desc="Round 1: Fetching expansion papers"):
            try:
                d = fetch_abstract(pid)
                if d and d.get('abstract'):
                    d['expansion_type'] = exp_type
                    round1_docs.append(d)
                else:
                    logger.debug(f"No abstract found for paper {pid}")
            except Exception as e:
                fetch_errors += 1
                logger.debug(f"Error fetching paper {pid}: {e}")
        
        logger.info(f"Round 1: Successfully fetched {len(round1_docs)} papers ({fetch_errors} errors)")
        
        if round1_docs:
            logger.info(f"Round 1: Scoring {len(round1_docs)} expansion papers...")
            try:
                scored_docs = score_documents(plan_text, round1_docs)
                high_round1_docs, cutoff1 = filter_high_docs(scored_docs, SIMILARITY_QUANTILE)
                logger.info(f"Round 1: {len(high_round1_docs)} docs above quantile cutoff (cutoff={cutoff1:.3f})")
            except Exception as e:
                logger.error(f"Error scoring round 1 documents: {e}", exc_info=True)
                high_round1_docs = round1_docs[:25]  # Fallback: take first 25
                logger.warning(f"Using fallback: returning first {len(high_round1_docs)} documents")
            
            # Round 2: Get citing papers from high-scoring round 1 papers
            logger.info("Round 2: Extracting citing papers from round 1 results...")
            try:
                round2_citing_ids = extract_citing_papers(high_round1_docs, limit_per_paper=10)
                final_docs = fetch_and_score_papers(round2_citing_ids, plan_text, 'citation_round2', "Round 2")
                logger.info(f"Round 2: Final result set contains {len(final_docs)} papers")
            except Exception as e:
                logger.error(f"Error in round 2 processing: {e}", exc_info=True)
                final_docs = high_round1_docs
                logger.warning("Round 2 failed, using Round 1 results as final output")
        else:
            logger.warning("No valid papers found in round 1 expansion.")
            final_docs = high_docs
            logger.info("Using initial high-scoring documents as final output")

        logger.info(f"Pipeline completed successfully. Returning {len(final_docs)} final documents.")
        return final_docs


# --- Utility Functions ---

def rank_phrases(plan, phrases, top_k):
    """Rank search phrases by semantic similarity to research plan."""
    logger.info("Starting phrase ranking with semantic similarity")
    logger.debug(f"Plan text length: {len(plan)} characters")
    logger.info(f"🔍 DEBUG: rank_phrases received {len(phrases)} phrases:")
    for i, phrase in enumerate(phrases):
        logger.info(f"🔍 DEBUG: Phrase {i+1}: '{phrase}' (type: {type(phrase)}, length: {len(str(phrase))})")
    logger.debug(f"Requesting top {top_k} phrases")
    
    # CRITICAL FIX: Split any OR-combined queries into individual terms
    expanded_phrases = []
    for phrase in phrases:
        phrase_str = str(phrase).strip()
        if " OR " in phrase_str:
            logger.warning(f"Found OR-combined query in rank_phrases input, splitting: '{phrase_str[:100]}...'")
            individual_terms = [t.strip() for t in phrase_str.split(" OR ") if t.strip()]
            expanded_phrases.extend(individual_terms)
            logger.info(f"Split OR query into {len(individual_terms)} individual terms")
        else:
            expanded_phrases.append(phrase_str)
    
    if len(expanded_phrases) != len(phrases):
        logger.info(f"Expanded {len(phrases)} input phrases to {len(expanded_phrases)} individual terms")
        phrases = expanded_phrases
    
    logger.info(f"🔍 DEBUG: After OR-splitting, rank_phrases processing {len(phrases)} individual phrases:")
    for i, phrase in enumerate(phrases[:5]):  # Log first 5 for brevity
        logger.info(f"🔍 DEBUG: Individual phrase {i+1}: '{phrase}'")
    if len(phrases) > 5:
        logger.info(f"🔍 DEBUG: ... and {len(phrases) - 5} more phrases")
    
    # Validate inputs and convert plan to string if needed
    if isinstance(plan, dict):
        logger.warning("Plan provided as dictionary, attempting to extract text")
        plan_sections = plan.get("outcomes", []) + \
                        plan.get("objectives", []) + \
                        plan.get("key_areas", []) + \
                        plan.get("questions", [])
        plan = " ".join(plan_sections)
        logger.debug(f"Extracted plan text from dictionary: {len(plan)} characters")
    
    if not plan or not str(plan).strip():
        logger.error("Empty plan text provided for phrase ranking")
        return list(zip(phrases, [0.0] * len(phrases)))[:top_k]
    
    # Ensure plan is a string
    plan = str(plan).strip()
    
    # Filter out empty phrases
    valid_phrases = [p for p in phrases if p and str(p).strip()]
    if not valid_phrases:
        logger.error("No valid phrases provided for ranking")
        return []
    
    if len(valid_phrases) != len(phrases):
        logger.warning(f"Filtered out {len(phrases) - len(valid_phrases)} empty phrases")
    
    # Check if ONNX model and tokenizer are available
    onnx_model_path = "./onnx_models/model.onnx"
    tokenizer_path = "./onnx_models/"
    
    if not os.path.exists(onnx_model_path):
        logger.error(f"ONNX model not found at {onnx_model_path}")
        logger.warning("Cannot perform semantic ranking, returning phrases in original order")
        return list(zip(valid_phrases, [1.0] * len(valid_phrases)))[:top_k]
        
    if not os.path.exists(tokenizer_path):
        logger.error(f"Tokenizer not found at {tokenizer_path}")
        logger.warning("Cannot perform semantic ranking, returning phrases in original order")
        return list(zip(valid_phrases, [1.0] * len(valid_phrases)))[:top_k]
    
    logger.debug("Loading tokenizer and ONNX model...")
    try:
        # Load tokenizer and ONNX session
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
        session = ort.InferenceSession(onnx_model_path)
        logger.info("Successfully loaded tokenizer and ONNX model")
    except Exception as e:
        logger.error(f"Failed to load tokenizer or ONNX model: {e}", exc_info=True)
        logger.warning("Falling back to original phrase order")
        return list(zip(valid_phrases, [1.0] * len(valid_phrases)))[:top_k]

    logger.debug("Setting up embedding function...")
    def get_embedding(text: str) -> np.ndarray:
        try:
            if not text or not text.strip():
                # Return zero vector for empty text
                logger.debug("Empty text provided to get_embedding, returning zero vector")
                return np.zeros(384)  # MiniLM-L6-v2 has 384 dimensions
            
            # Truncate very long text to avoid memory issues
            max_length = 512  # BERT-style models typically handle 512 tokens max
            original_length = len(text)
            if len(text) > max_length * 4:  # Rough estimate: 4 chars per token
                text = text[:max_length * 4]
                logger.debug(f"Truncated text from {original_length} to {len(text)} characters")
            
            inputs = tokenizer(text, return_tensors="np", padding=True, truncation=True, max_length=max_length)
            
            outputs = session.run(None, {
                "input_ids": inputs["input_ids"],
                "attention_mask": inputs["attention_mask"]
            })
            
            result = np.mean(outputs[0], axis=1).squeeze()
            logger.debug(f"Generated embedding with shape: {result.shape}")
            return result
            
        except Exception as e:
            logger.error(f"Error in get_embedding: {e}", exc_info=True)
            logger.debug(f"Text that caused error: '{text[:100]}...'")
            # Return zero vector as fallback
            return np.zeros(384)
        
    logger.info("Computing embeddings for search phrases...")
    # Compute average embedding for all search terms
    query_embeddings = []
    for i, term in enumerate(phrases, 1):
        try:
            logger.debug(f"Computing embedding for phrase {i}/{len(phrases)}: '{term}'")
            embedding = get_embedding(term)
            if np.any(embedding):  # Only add non-zero embeddings
                query_embeddings.append(embedding)
                logger.debug(f"Successfully computed embedding for phrase: '{term}'")
            else:
                logger.warning(f"Zero embedding generated for phrase: '{term}'")
        except Exception as e:
            logger.error(f"Failed to compute embedding for term '{term}': {e}", exc_info=True)

    if not query_embeddings:
        logger.error("No valid query embeddings generated, cannot perform ranking")
        raise ValueError("No valid query embeddings")
    
    logger.info(f"Generated {len(query_embeddings)} valid embeddings from {len(phrases)} phrases")
    
    # Compute plan embedding for comparison
    logger.info("Computing plan embedding...")
    try:
        plan_embedding = get_embedding(plan)
        logger.debug(f"Plan embedding shape: {plan_embedding.shape}")
    except Exception as e:
        logger.error(f"Failed to compute plan embedding: {e}", exc_info=True)
        raise ValueError("Failed to compute plan embedding")
    
    # Compute cosine similarity between each phrase and the plan
    logger.info("Computing cosine similarities...")
    scores = []
    for i, embedding in enumerate(query_embeddings):
        try:
            # Compute cosine similarity using numpy with safety checks
            dot_product = np.dot(plan_embedding, embedding)
            norm_plan = np.linalg.norm(plan_embedding)
            norm_embedding = np.linalg.norm(embedding)
            
            # Avoid division by zero
            if norm_plan == 0 or norm_embedding == 0:
                similarity_score = 0.0
                logger.warning(f"Zero norm detected for phrase {i+1}, setting similarity to 0.0")
            else:
                similarity_score = dot_product / (norm_plan * norm_embedding)
            
            scores.append(float(similarity_score))
            logger.debug(f"Phrase {i+1} similarity score: {similarity_score:.4f}")
            
        except Exception as e:
            logger.error(f"Error computing similarity for phrase {i+1}: {e}", exc_info=True)
            scores.append(0.0)

    # Rank and return results
    ranked_results = sorted(zip(phrases, scores), key=lambda x: x[1], reverse=True)[:top_k]
    logger.info(f"Phrase ranking completed. Top phrases: {[(phrase, f'{score:.4f}') for phrase, score in ranked_results]}")
    
    return ranked_results


def score_documents(plan, docs):
    """Score documents by semantic similarity to research plan."""
    logger.info(f"Starting document scoring for {len(docs)} documents")
    
    missing_title = sum(1 for doc in docs if not doc.get('title'))
    missing_abstract = sum(1 for doc in docs if doc.get('abstract') is None)
    empty_abstract = sum(1 for doc in docs if doc.get('abstract') == '')
    
    if missing_title or missing_abstract or empty_abstract:
        logger.warning(f"Data quality issues: {missing_title} docs missing title, "
                      f"{missing_abstract} docs with null abstract, {empty_abstract} docs with empty abstract")
    
    # Check if ONNX model and tokenizer are available
    onnx_model_path = "./onnx_models/model.onnx"
    tokenizer_path = "./onnx_models/"
    
    if not os.path.exists(onnx_model_path) or not os.path.exists(tokenizer_path):
        logger.error("ONNX model or tokenizer not found, cannot score documents")
        # Return documents with default scores
        for doc in docs:
            doc['score'] = 0.5  # Default neutral score
        return docs
    
    try:
        # Load tokenizer and ONNX session for document scoring
        logger.debug("Loading tokenizer and ONNX model for document scoring...")
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
        session = ort.InferenceSession(onnx_model_path)
        logger.debug("Successfully loaded models for document scoring")
    except Exception as e:
        logger.error(f"Failed to load models for document scoring: {e}", exc_info=True)
        # Return documents with default scores
        for doc in docs:
            doc['score'] = 0.5
        return docs
    
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
            logger.error(f"Error in get_embedding for document scoring: {e}", exc_info=True)
            # Return zero vector as fallback
            return np.zeros(384)
    
    logger.debug("Preparing document texts for embedding...")
    texts = []
    for i, doc in enumerate(docs):
        title = str(doc.get('title')) if doc.get('title') else ""
        abstract = str(doc.get('abstract')) if doc.get('abstract') else ""
        combined_text = title + ". " + abstract
        texts.append(combined_text)
        
        if i < 3:  # Log first 3 documents for debugging
            logger.debug(f"Doc {i+1} text length: {len(combined_text)} chars, "
                        f"title: {'present' if title else 'missing'}, "
                        f"abstract: {'present' if abstract else 'missing'}")
    
    # Get plan embedding using ONNX model
    logger.debug("Computing plan embedding for document scoring...")
    try:
        plan_emb = get_embedding(plan)
        logger.debug(f"Plan embedding computed with shape: {plan_emb.shape}")
    except Exception as e:
        logger.error(f"Failed to compute plan embedding: {e}", exc_info=True)
        # Return documents with default scores
        for doc in docs:
            doc['score'] = 0.5
        return docs
    
    # Get document embeddings using ONNX model 
    logger.info("Computing document embeddings...")
    doc_embeddings = []
    embedding_errors = 0
    
    for i, text in enumerate(texts):
        try:
            doc_emb = get_embedding(text)
            doc_embeddings.append(doc_emb)
            if i % 10 == 0:  # Log progress every 10 documents
                logger.debug(f"Computed embeddings for {i+1}/{len(texts)} documents")
        except Exception as e:
            logger.error(f"Error computing embedding for document {i}: {e}")
            doc_embeddings.append(np.zeros(384))  # Zero vector fallback
            embedding_errors += 1
    
    if embedding_errors > 0:
        logger.warning(f"Failed to compute embeddings for {embedding_errors} documents")
    
    # Compute cosine similarity scores
    logger.info("Computing similarity scores...")
    scores = []
    similarity_errors = 0
    
    for i, doc_emb in enumerate(doc_embeddings):
        try:
            # Compute cosine similarity using numpy with safety checks
            dot_product = np.dot(plan_emb, doc_emb)
            norm_plan = np.linalg.norm(plan_emb)
            norm_doc = np.linalg.norm(doc_emb)
            
            # Avoid division by zero
            if norm_plan == 0 or norm_doc == 0:
                similarity = 0.0
                logger.debug(f"Zero norm detected for document {i}, setting similarity to 0.0")
            else:
                similarity = dot_product / (norm_plan * norm_doc)
            
            scores.append(float(similarity))
            
        except Exception as e:
            logger.error(f"Error computing similarity for document {i}: {e}")
            scores.append(0.0)
            similarity_errors += 1
    
    if similarity_errors > 0:
        logger.warning(f"Failed to compute similarity for {similarity_errors} documents")
    
    # Assign scores to documents
    for doc, score in zip(docs, scores):
        doc['score'] = score
        
    # Log scoring statistics
    if scores:
        avg_score = np.mean(scores)
        max_score = np.max(scores)
        min_score = np.min(scores)
        logger.info(f"Document scoring completed: avg={avg_score:.4f}, max={max_score:.4f}, min={min_score:.4f}")
    else:
        logger.warning("No valid scores computed")
    
    logger.info(f"Scored {len(docs)} documents using ONNX model")
    return docs


def filter_high_docs(docs, quantile):
    """Filter documents above similarity quantile threshold."""
    logger.info(f"Filtering documents using quantile threshold: {quantile}")
    
    if not docs:
        logger.warning("No documents to filter")
        return [], 0.0
    
    scores = np.array([d.get('score', 0.0) for d in docs])
    
    if len(scores) == 0:
        logger.warning("No scores found in documents")
        return [], 0.0
    
    try:
        cutoff = np.quantile(scores, quantile)
        logger.info(f"Quantile cutoff for scores: {cutoff:.4f} (quantile={quantile})")
        logger.debug(f"Score statistics: min={np.min(scores):.4f}, max={np.max(scores):.4f}, "
                    f"mean={np.mean(scores):.4f}, std={np.std(scores):.4f}")
        
        filtered_docs = [d for d in docs if d.get('score', 0.0) >= cutoff]
        logger.info(f"Filtered {len(filtered_docs)} documents above cutoff from {len(docs)} total")
        
        return filtered_docs, cutoff
        
    except Exception as e:
        logger.error(f"Error filtering documents: {e}", exc_info=True)
        logger.warning("Returning all documents due to filtering error")
        return docs, 0.0


def extract_references(docs):
    """Extract reference paper IDs from documents."""
    logger.info(f"Extracting references from {len(docs)} documents")
    
    refs = set()
    docs_with_refs = 0
    docs_without_refs = 0
    total_refs = 0
    
    for i, doc in enumerate(docs):
        references = doc.get('references', [])
        if references is None:
            references = []
        
        if references:
            docs_with_refs += 1
            doc_ref_count = 0
            for ref in references:
                # Handle different reference formats
                if isinstance(ref, dict):
                    # CORE/Semantic Scholar format
                    rid = ref.get('paperId')
                    if rid:
                        refs.add(rid)
                        doc_ref_count += 1
                elif isinstance(ref, str):
                    # OpenAlex format - extract ID from URL
                    if ref.startswith('https://openalex.org/'):
                        refs.add(ref.split('/')[-1])
                        doc_ref_count += 1
            
            total_refs += doc_ref_count
            logger.debug(f"Document {i+1}: extracted {doc_ref_count} references")
        else:
            docs_without_refs += 1
    
    logger.info(f"Reference extraction completed:")
    logger.info(f"  - {docs_with_refs} docs with references, {docs_without_refs} docs without references")
    logger.info(f"  - {total_refs} total references, {len(refs)} unique references")
    logger.info(f"  - Average references per doc with refs: {total_refs/docs_with_refs:.1f}" if docs_with_refs > 0 else "  - No documents with references")
    
    return list(refs)


def extract_citing_papers(docs, limit_per_paper=10):
    """Extract papers that cite the given documents using OpenAlex API."""
    logger.info(f"Extracting citing papers from {len(docs)} documents (limit: {limit_per_paper} per paper)")
    
    citing_paper_ids = set()
    docs_with_citations = 0
    total_citations = 0
    api_errors = 0
    rate_limit_hits = 0
    
    # Check if we have a valid email for OpenAlex
    if not OPENALEX_EMAIL:
        logger.warning("No OpenAlex email configured. This may cause 403 errors.")
        logger.info("Set OPENALEX_EMAIL environment variable to avoid rate limiting.")
    else:
        logger.info(f"Using OpenAlex email for API requests: {OPENALEX_EMAIL}")
    
    for doc_idx, doc in enumerate(docs, 1):
        paper_id = doc.get('paperId')
        if not paper_id:
            logger.debug(f"Document {doc_idx}: No paperId found, skipping citation extraction")
            continue
        
        # Convert paper_id to string if it's not already
        paper_id = str(paper_id)
            
        # Ensure we have a full OpenAlex ID
        if not paper_id.startswith('https://openalex.org/'):
            paper_id = f"https://openalex.org/{paper_id}"
        
        logger.debug(f"Document {doc_idx}/{len(docs)}: Fetching citations for paper: {paper_id}")
            
        retries = 0
        success = False
        while retries < MAX_RETRIES and not success:
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
                
                logger.debug(f"Making API request to {url} with params: {params}")
                
                time.sleep(0.1)  # OpenAlex rate limiting (10 req/sec)
                r = requests.get(url, params=params, timeout=30)
                
                logger.debug(f"API response: status={r.status_code}")
                
                if r.status_code == 200:
                    data = r.json()
                    results = data.get('results', [])
                    if results:
                        docs_with_citations += 1
                        doc_citation_count = 0
                        for result in results:
                            citing_id = result.get('id', '').replace('https://openalex.org/', '')
                            if citing_id and citing_id != doc.get('paperId'):
                                citing_paper_ids.add(citing_id)
                                total_citations += 1
                                doc_citation_count += 1
                        logger.debug(f"Document {doc_idx}: Found {doc_citation_count} citing papers")
                    else:
                        logger.debug(f"Document {doc_idx}: No citing papers found")
                    success = True
                    
                elif r.status_code == 429:
                    rate_limit_hits += 1
                    delay = BACKOFF_BASE * 2**retries
                    logger.warning(f"OpenAlex API rate limited (attempt {retries+1}). Retrying in {delay}s...")
                    time.sleep(delay)
                    retries += 1
                    
                elif r.status_code == 403:
                    logger.error(f"OpenAlex API access forbidden (403). Check email configuration and API usage.")
                    logger.debug(f"Paper ID that caused 403: {paper_id}")
                    api_errors += 1
                    break  # Don't retry 403 errors
                    
                else:
                    logger.error(f"OpenAlex API error: HTTP {r.status_code}")
                    logger.debug(f"Response text: {r.text[:200]}...")
                    logger.debug(f"Paper ID that caused error: {paper_id}")
                    api_errors += 1
                    break  # Don't retry other HTTP errors
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout for document {doc_idx}, retrying...")
                retries += 1
            except Exception as e:
                logger.error(f"Unexpected error fetching citations for document {doc_idx}: {e}", exc_info=True)
                api_errors += 1
                break  # Non-retryable error
        
        if retries >= MAX_RETRIES and not success:
            logger.error(f"Max retries exceeded for document {doc_idx}")
            api_errors += 1
    
    logger.info(f"Citation extraction completed:")
    logger.info(f"  - {docs_with_citations} docs had citing papers")
    logger.info(f"  - {total_citations} total citing papers found") 
    logger.info(f"  - {len(citing_paper_ids)} unique citing papers")
    logger.info(f"  - {api_errors} API errors encountered")
    logger.info(f"  - {rate_limit_hits} rate limit hits")
    
    if docs_with_citations > 0:
        logger.info(f"  - Average citing papers per successful doc: {total_citations/docs_with_citations:.1f}")
    
    return list(citing_paper_ids)


def fetch_abstract(paper_id):
    """Fetch paper details from OpenAlex API using paper ID."""
    logger.debug(f"Fetching abstract for paper: {paper_id}")
    
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
        
        try:
            time.sleep(0.1)  # OpenAlex rate limiting
            r = requests.get(url, params=params, timeout=30)
            
            if r.status_code == 200:
                try:
                    d = r.json()
                except requests.exceptions.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON for paper {paper_id} (empty response)")
                    return None
                except Exception as e:
                    logger.error(f"Failed to parse JSON for paper {paper_id}: {e}")
                    return None
                    
                title = d.get("title") or d.get("display_name")
                
                # Convert abstract inverted index to plain text
                abstract_text = ""
                abstract_index = d.get('abstract_inverted_index', {})
                if abstract_index:
                    # Reconstruct abstract from inverted index
                    try:
                        max_pos = max(max(positions) for positions in abstract_index.values() if positions)
                        words = [""] * (max_pos + 1)
                        
                        for word, positions in abstract_index.items():
                            for pos in positions:
                                if pos < len(words):
                                    words[pos] = word
                        
                        abstract_text = " ".join(words).strip()
                        # Clean up extra spaces
                        abstract_text = re.sub(r'\s+', ' ', abstract_text)
                        
                    except Exception as e:
                        logger.error(f"Error reconstructing abstract for {paper_id}: {e}")
                        abstract_text = ""
                
                # Extract PDF URL
                pdf_url = d.get('primary_location', {}).get('pdf_url')
                
                # Log result
                if abstract_text:
                    logger.debug(f"Successfully fetched paper {paper_id}: title={'present' if title else 'missing'}, "
                               f"abstract={len(abstract_text)} chars")
                else:
                    logger.debug(f"Paper {paper_id}: title={'present' if title else 'missing'}, abstract=empty")
                
                return {"paperId": clean_id, "title": title, "abstract": abstract_text, "url": pdf_url}
                
            elif r.status_code == 429:
                delay = BACKOFF_BASE * 2**retries
                logger.warning(f"OpenAlex abstract fetch rate limited (paper {paper_id}). Retrying in {delay}s...")
                time.sleep(delay)
                retries += 1
                
            elif r.status_code == 404:
                logger.debug(f"Paper {paper_id} not found in OpenAlex")
                break  # Paper doesn't exist, no point retrying
                
            else:
                logger.warning(f"Failed to fetch paper {paper_id} from OpenAlex: HTTP {r.status_code}")
                if r.status_code == 403:
                    logger.warning("403 error may indicate API access issues or missing email configuration")
                break  # Non-retryable error
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching paper {paper_id}, retrying...")
            retries += 1
        except Exception as e:
            logger.error(f"Unexpected error fetching paper {paper_id}: {e}", exc_info=True)
            break
    
    if retries >= MAX_RETRIES:
        logger.warning(f"Max retries exceeded for paper {paper_id}")
    
    return None


def fetch_and_score_papers(paper_ids, plan_text, expansion_type, description):
    """Fetch abstracts for papers and score them against the plan."""
    logger.info(f"{description}: Starting to fetch and score {len(paper_ids)} papers")
    
    if not paper_ids:
        logger.warning(f"{description}: No papers to fetch. Skipping.")
        return []
    
    logger.info(f"{description}: Fetching abstracts for {len(paper_ids)} papers...")
    docs = []
    failed_fetches = 0
    empty_abstracts = 0
    null_abstracts = 0
    successful_fetches = 0
    
    for i, pid in enumerate(tqdm(paper_ids, desc=f"{description}: Fetching abstracts"), 1):
        try:
            d = fetch_abstract(pid)
            if d is None:
                failed_fetches += 1
                logger.debug(f"{description}: Failed to fetch paper {i}/{len(paper_ids)}: {pid}")
            elif not d.get('abstract'):
                if d.get('abstract') is None:
                    null_abstracts += 1
                else:
                    empty_abstracts += 1
                logger.debug(f"{description}: Paper {i}/{len(paper_ids)} has no abstract: {pid}")
            else:
                d['expansion_type'] = expansion_type
                docs.append(d)
                successful_fetches += 1
                if i % 10 == 0:  # Log progress every 10 papers
                    logger.debug(f"{description}: Successfully fetched {successful_fetches} papers so far")
        except Exception as e:
            failed_fetches += 1
            logger.error(f"{description}: Error fetching paper {pid}: {e}")
    
    logger.info(f"{description}: Fetching completed:")
    logger.info(f"  - Total papers requested: {len(paper_ids)}")
    logger.info(f"  - Successful API calls: {len(paper_ids) - failed_fetches}")
    logger.info(f"  - Failed API calls: {failed_fetches}")
    logger.info(f"  - Papers with null abstracts: {null_abstracts}")
    logger.info(f"  - Papers with empty abstracts: {empty_abstracts}")
    logger.info(f"  - Papers with valid abstracts: {len(docs)}")
    logger.info(f"  - Abstract availability rate: {len(docs)/len(paper_ids)*100:.1f}%")
    
    if not docs:
        logger.warning(f"{description}: No docs with valid abstracts found. Skipping scoring.")
        return []
    
    logger.info(f"{description}: Scoring {len(docs)} papers against research plan...")
    try:
        scored_docs = score_documents(plan_text, docs)
        high_docs, cutoff = filter_high_docs(scored_docs, SIMILARITY_QUANTILE)
        logger.info(f"{description}: Scoring completed:")
        logger.info(f"  - {len(high_docs)} docs above quantile cutoff ({SIMILARITY_QUANTILE})")
        logger.info(f"  - Score cutoff: {cutoff:.4f}")
        
        if high_docs:
            scores = [d.get('score', 0) for d in high_docs]
            logger.info(f"  - Score range: {min(scores):.4f} to {max(scores):.4f}")
        
        return high_docs
        
    except Exception as e:
        logger.error(f"{description}: Error during scoring: {e}", exc_info=True)
        logger.warning(f"{description}: Returning first {min(25, len(docs))} documents due to scoring error")
        return docs[:25]
