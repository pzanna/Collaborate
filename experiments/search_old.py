# --- search.py ---

import os
import time
import json
import requests
import numpy as np
import spacy
import xml.etree.ElementTree as ET
import re
from tqdm import tqdm
from sentence_transformers import SentenceTransformer, util
from urllib.parse import urlencode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

nlp = spacy.load("en_core_web_sm")

# --- Configuration ---
SIMILARITY_QUANTILE = 0.85
TOP_K_TERMS = 1
MAX_RETRIES = 5
BACKOFF_BASE = 5
SEARCH_LIMIT = 5
YEAR_RANGE = (2010, 2025)  # Adjust as needed

# API Keys
NCBI_API_KEY = os.getenv('NCBI_API_KEY')
CORE_API_KEY = os.getenv('CORE_API_KEY')

# Print API key status
print(f"NCBI API Key: {'✓ Found' if NCBI_API_KEY else '✗ Not found'}")
print(f"CORE API Key: {'✓ Found' if CORE_API_KEY else '✗ Not found'}")

# --- Embedding Model ---
model = SentenceTransformer("sentence-transformers/all-MiniLM-L12-v2")

# --- Term Extraction ---
def extract_phrases(text):
    phrases = set()
    for chunk in nlp(text).noun_chunks:
        phrase = chunk.text.strip().lower()
        if 1 <= len(phrase.split()) <= 4:
            phrases.add(phrase)
    return list(phrases)

def rank_phrases(plan, phrases, top_k):
    plan_emb = model.encode(plan, convert_to_tensor=True)
    phrase_embs = model.encode(phrases, convert_to_tensor=True)
    scores = util.cos_sim(plan_emb, phrase_embs)[0].cpu().numpy()
    return sorted(zip(phrases, scores), key=lambda x: x[1], reverse=True)[:top_k]

# --- API Query ---
def query_semantic_scholar(term, limit=SEARCH_LIMIT):
    retries = 0
    while retries < MAX_RETRIES:
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={term}&limit={limit}&year={YEAR_RANGE[0]}-{YEAR_RANGE[1]}&fieldsOfStudy=Biology&fields=title,abstract,authors,externalIds,year,references"
        r = requests.get(url)
        if r.status_code == 200:
            return r.json().get("data", [])
        elif r.status_code == 429:
            delay = BACKOFF_BASE * 2**retries
            print(f"Rate limited. Retrying in {delay}s...")
            time.sleep(delay)
            retries += 1
        else:
            break
    print(f"Failed to query for term: {term}")
    return []

def query_pubmed(term, limit=SEARCH_LIMIT):
    """Query PubMed API for papers."""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            # First, search for IDs
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            
            # Add year filter to the search term
            year_filter = f" AND {YEAR_RANGE[0]}:{YEAR_RANGE[1]}[dp]"
            search_term = term + year_filter
            
            search_params = {
                'db': 'pubmed',
                'term': search_term,
                'retmax': limit,
                'retmode': 'json'
            }
            
            # Add API key if available
            if NCBI_API_KEY:
                search_params['api_key'] = NCBI_API_KEY
            
            time.sleep(1 if NCBI_API_KEY else 2)  # Faster rate limit with API key
            r = requests.get(search_url, params=search_params)
            
            if r.status_code == 200:
                search_data = r.json()
                id_list = search_data.get('esearchresult', {}).get('idlist', [])
                
                if not id_list:
                    return []
                
                # Fetch details for the IDs
                fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
                fetch_params = {
                    'db': 'pubmed',
                    'id': ','.join(id_list),
                    'retmode': 'xml'
                }
                
                # Add API key if available
                if NCBI_API_KEY:
                    fetch_params['api_key'] = NCBI_API_KEY
                
                time.sleep(1 if NCBI_API_KEY else 2)  # Faster rate limit with API key
                r = requests.get(fetch_url, params=fetch_params)
                
                if r.status_code == 200:
                    return parse_pubmed_xml(r.text)
                else:
                    print(f"PubMed fetch failed with status {r.status_code}")
                    return []
                    
            elif r.status_code == 429:
                delay = BACKOFF_BASE * 2**retries
                print(f"PubMed rate limited. Retrying in {delay}s...")
                time.sleep(delay)
                retries += 1
            else:
                break
                
        except Exception as e:
            print(f"Error querying PubMed: {e}")
            break
            
    print(f"Failed to query PubMed for term: {term}")
    return []

def query_arxiv(term, limit=SEARCH_LIMIT):
    """Query arXiv API for papers."""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            url = "http://export.arxiv.org/api/query"
            
            # Build search query
            query_parts = term.split()
            if len(query_parts) > 1:
                search_query = f'all:"{term}"'
            else:
                search_query = f'all:{term}'
            
            params = {
                'search_query': search_query,
                'start': 0,
                'max_results': limit,
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            time.sleep(5)  # arXiv rate limit
            r = requests.get(url, params=params)
            
            if r.status_code == 200:
                return parse_arxiv_xml(r.text)
            elif r.status_code == 429:
                delay = BACKOFF_BASE * 2**retries
                print(f"arXiv rate limited. Retrying in {delay}s...")
                time.sleep(delay)
                retries += 1
            else:
                break
                
        except Exception as e:
            print(f"Error querying arXiv: {e}")
            break
            
    print(f"Failed to query arXiv for term: {term}")
    return []

# --- XML Parsers ---
def parse_pubmed_xml(xml_content):
    """Parse PubMed XML response."""
    try:
        root = ET.fromstring(xml_content)
        entries = []
        
        for article in root.findall('.//PubmedArticle'):
            try:
                # Extract basic information
                title_elem = article.find('.//ArticleTitle')
                abstract_elem = article.find('.//AbstractText')
                pmid_elem = article.find('.//PMID')
                
                # Extract authors
                authors = []
                for author in article.findall('.//Author'):
                    lastname = author.find('LastName')
                    forename = author.find('ForeName')
                    if lastname is not None and forename is not None:
                        if lastname.text and forename.text:
                            authors.append(f"{forename.text} {lastname.text}")
                
                # Extract publication year
                year_elem = article.find('.//PubDate/Year')
                
                # Extract journal
                journal_elem = article.find('.//Journal/Title')
                
                # Extract DOI
                doi_elem = article.find('.//ArticleId[@IdType="doi"]')
                
                record = {
                    'title': title_elem.text if title_elem is not None and title_elem.text else None,
                    'abstract': abstract_elem.text if abstract_elem is not None and abstract_elem.text else None,
                    'authors': [{'name': name} for name in authors],
                    'pmid': pmid_elem.text if pmid_elem is not None and pmid_elem.text else None,
                    'year': int(year_elem.text) if year_elem is not None and year_elem.text else None,
                    'journal': journal_elem.text if journal_elem is not None and journal_elem.text else None,
                    'externalIds': {'DOI': doi_elem.text} if doi_elem is not None and doi_elem.text else {},
                    'references': []  # PubMed doesn't include references in basic fetch
                }
                entries.append(record)
                
            except Exception as e:
                print(f"Error parsing PubMed entry: {e}")
                continue
        
        return entries
        
    except Exception as e:
        print(f"Error parsing PubMed XML: {e}")
        return []

def parse_arxiv_xml(xml_content):
    """Parse arXiv XML response."""
    try:
        root = ET.fromstring(xml_content)
        entries = []
        
        # arXiv uses Atom namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        for entry in root.findall('atom:entry', ns):
            try:
                title = entry.find('atom:title', ns)
                summary = entry.find('atom:summary', ns)
                published = entry.find('atom:published', ns)
                
                authors = []
                for author in entry.findall('atom:author', ns):
                    name = author.find('atom:name', ns)
                    if name is not None and name.text:
                        authors.append({'name': name.text.strip()})
                
                # Extract arXiv ID from id
                entry_id = entry.find('atom:id', ns)
                arxiv_id = None
                if entry_id is not None and entry_id.text:
                    # Extract ID from URL like http://arxiv.org/abs/2301.12345v1
                    match = re.search(r'abs/([0-9]+\.[0-9]+)', entry_id.text)
                    if match:
                        arxiv_id = match.group(1)
                
                # Extract year from published date
                year = None
                if published is not None and published.text:
                    try:
                        year = int(published.text[:4])
                    except:
                        pass
                
                record = {
                    'title': title.text.strip() if title is not None and title.text else None,
                    'abstract': summary.text.strip() if summary is not None and summary.text else None,
                    'authors': authors,
                    'year': year,
                    'arxiv_id': arxiv_id,
                    'externalIds': {'ArXiv': arxiv_id} if arxiv_id else {},
                    'references': []  # arXiv doesn't include references
                }
                entries.append(record)
                
            except Exception as e:
                print(f"Error parsing arXiv entry: {e}")
                continue
        
        return entries
        
    except Exception as e:
        print(f"Error parsing arXiv XML: {e}")
        return []

# --- Document Scoring ---
def score_documents(plan, docs):
    missing_title = sum(1 for doc in docs if not doc.get('title'))
    missing_abstract = sum(1 for doc in docs if doc.get('abstract') is None)
    if missing_title or missing_abstract:
        print(f"[WARN] {missing_title} docs missing title, {missing_abstract} docs missing abstract.")
    texts = [
        (str(doc.get('title')) if doc.get('title') else "") + ". " + (str(doc.get('abstract')) if doc.get('abstract') else "")
        for doc in docs
    ]
    plan_emb = model.encode(plan, convert_to_tensor=True)
    doc_embs = model.encode(texts, convert_to_tensor=True)
    scores = util.cos_sim(plan_emb, doc_embs)[0].cpu().numpy()
    for doc, score in zip(docs, scores):
        doc['score'] = float(score)
    print(f"Scored {len(docs)} documents - {docs}")
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
                rid = ref.get('paperId')
                if rid:
                    refs.add(rid)
        else:
            docs_without_refs += 1
    print(f"Reference extraction: {docs_with_refs} docs with refs, {docs_without_refs} docs without refs")
    return list(refs)

def extract_citing_papers(docs, limit_per_paper=10):
    """Extract papers that cite the given documents."""
    citing_paper_ids = set()
    docs_with_citations = 0
    total_citations = 0
    
    for doc in docs:
        paper_id = doc.get('paperId')
        if not paper_id:
            continue
            
        retries = 0
        while retries < MAX_RETRIES:
            try:
                # Query Semantic Scholar for papers that cite this one
                url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations"
                params = {
                    'fields': 'paperId,title',
                    'limit': limit_per_paper
                }
                
                time.sleep(1)  # Rate limiting
                r = requests.get(url, params=params)
                
                if r.status_code == 200:
                    data = r.json()
                    citations = data.get('data', [])
                    if citations:
                        docs_with_citations += 1
                        for citation in citations:
                            citing_paper = citation.get('citingPaper', {})
                            citing_id = citing_paper.get('paperId')
                            if citing_id:
                                citing_paper_ids.add(citing_id)
                                total_citations += 1
                    break  # Success, exit retry loop
                elif r.status_code == 429:
                    delay = BACKOFF_BASE * 2**retries
                    print(f"Citations API rate limited. Retrying in {delay}s...")
                    time.sleep(delay)
                    retries += 1
                else:
                    print(f"Failed to get citations for paper {paper_id}: HTTP {r.status_code}")
                    break  # Non-retryable error
                    
            except Exception as e:
                print(f"Error fetching citations for paper {paper_id}: {e}")
                break  # Non-retryable error
        
        if retries >= MAX_RETRIES:
            print(f"Max retries exceeded for citations of paper {paper_id}")
    
    print(f"Citation extraction: {docs_with_citations} docs had citing papers, {total_citations} total citing papers found")
    return list(citing_paper_ids)

def fetch_abstract(paper_id):
    retries = 0
    while retries < MAX_RETRIES:
        url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}?fields=title,abstract"
        r = requests.get(url)
        
        if r.status_code == 200:
            d = r.json()
            title = d.get("title")
            abstract = d.get("abstract", "")
            # print abstract
            if abstract:
                print (f"Fetched paper {paper_id} successfully - Name: {title}, Abstract: {abstract}")
            # Debug logging
            else:
                print(f"[DEBUG] Paper {paper_id}: title={'Present' if title else 'Missing'}, abstract={'Empty' if abstract == '' else 'None' if abstract is None else 'Present'}")
            
            return {"paperId": paper_id, "title": title, "abstract": abstract}
        elif r.status_code == 429:
            delay = BACKOFF_BASE * 2**retries
            print(f"Abstract fetch rate limited. Retrying in {delay}s...")
            time.sleep(delay)
            retries += 1
        else:
            print(f"[DEBUG] Failed to fetch paper {paper_id}: HTTP {r.status_code}")
            break  # Non-retryable error
    
    if retries >= MAX_RETRIES:
        print(f"[DEBUG] Max retries exceeded for paper {paper_id}")
    
    return None

# --- Main Pipeline ---
def main():

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
    if not plan_text.strip():
        print("[WARN] Plan text is empty after combining sections. Exiting.")
        return

    print("Extracting candidate terms...")
    candidates = extract_phrases(plan_text)
    print(f"Extracted {len(candidates)} candidate terms.")
    if not candidates:
        print("[WARN] No candidate terms extracted. Exiting.")
        return

    ranked = rank_phrases(plan_text, candidates, TOP_K_TERMS)
    top_terms = [term for term, _ in ranked]
    print(f"Top {TOP_K_TERMS} terms: {top_terms}")
    if not top_terms:
        print("[WARN] No top terms after ranking. Exiting.")
        return

    print("Querying initial papers from all databases...")
    all_docs = []
    for term in top_terms:
        print(f"Searching for term: '{term}'")
        
        # Search Semantic Scholar
        ss_papers = query_semantic_scholar(term)
        print(f"  Semantic Scholar: {len(ss_papers)} papers found.")
        for paper in ss_papers:
            paper['source'] = 'semantic_scholar'
        all_docs.extend(ss_papers)
        
        # Search PubMed
        pm_papers = query_pubmed(term)
        print(f"  PubMed: {len(pm_papers)} papers found.")
        for paper in pm_papers:
            paper['source'] = 'pubmed'
        all_docs.extend(pm_papers)
        
        # Search arXiv
        ar_papers = query_arxiv(term)
        print(f"  arXiv: {len(ar_papers)} papers found.")
        for paper in ar_papers:
            paper['source'] = 'arxiv'
        all_docs.extend(ar_papers)
        
    print(f"Total papers found across all databases: {len(all_docs)}")
    if not all_docs:
        print("[WARN] No papers found for any top term across all databases. Exiting.")
        return

    # Remove duplicates based on title similarity
    print("Removing duplicates...")
    deduplicated_docs = []
    seen_titles = set()
    
    for doc in all_docs:
        title = doc.get('title', '')
        if title and isinstance(title, str):
            # Normalize title for comparison
            normalized_title = re.sub(r'[^\w\s]', '', title.lower()).strip()
            if normalized_title not in seen_titles:
                seen_titles.add(normalized_title)
                deduplicated_docs.append(doc)
    
    all_docs = deduplicated_docs
    print(f"After deduplication: {len(all_docs)} unique papers")

    print(f"Scoring {len(all_docs)} documents...")
    all_docs = score_documents(plan_text, all_docs)
    high_docs, cutoff = filter_high_docs(all_docs, SIMILARITY_QUANTILE)
    print(f"Docs above quantile cutoff ({SIMILARITY_QUANTILE}): {len(high_docs)} (cutoff={cutoff:.3f})")
    if not high_docs:
        print("[WARN] No high scoring docs after filtering. Exiting.")
        return

    print(f"Top score cutoff: {cutoff:.3f}. Expanding via references and citations...")
    
    # Extract references (papers cited by high-scoring papers)
    print("Extracting references...")
    paper_ids = extract_references(high_docs)
    print(f"Extracted {len(paper_ids)} unique reference paper IDs.")
    
    # Extract citing papers (papers that cite high-scoring papers)
    print("Extracting citing papers...")
    citing_paper_ids = extract_citing_papers(high_docs, limit_per_paper=10)
    print(f"Extracted {len(citing_paper_ids)} unique citing paper IDs.")
    
    # Combine references and citations, removing duplicates
    all_expansion_ids = list(set(paper_ids + citing_paper_ids))
    print(f"Total unique papers for expansion: {len(all_expansion_ids)} (references + citations)")
    
    if not all_expansion_ids:
        print("[WARN] No references or citations found to expand. Skipping expansion.")
        new_docs = []
    else:
        new_docs = []
        failed_fetches = 0
        empty_abstracts = 0
        null_abstracts = 0
        
        for pid in tqdm(all_expansion_ids, desc="Fetching abstracts for references and citations"):
            d = fetch_abstract(pid)
            if d is None:
                failed_fetches += 1
            elif not d.get('abstract'):
                if d.get('abstract') is None:
                    null_abstracts += 1
                else:
                    empty_abstracts += 1
            else:
                d['expansion_type'] = 'reference' if pid in paper_ids else 'citation'
                if pid in paper_ids and pid in citing_paper_ids:
                    d['expansion_type'] = 'both'
                new_docs.append(d)
        
        print(f"Fetched {len(new_docs)} abstracts with non-empty content.")
        print(f"Data quality summary:")
        print(f"  - Successful fetches: {len(all_expansion_ids) - failed_fetches}")
        print(f"  - Failed API calls: {failed_fetches}")
        print(f"  - Null abstracts: {null_abstracts}")
        print(f"  - Empty abstracts: {empty_abstracts}")
        print(f"  - Valid abstracts: {len(new_docs)}")
        print(f"  - Abstract availability rate: {len(new_docs)/len(all_expansion_ids)*100:.1f}%")

    if not new_docs:
        print("[WARN] No new reference or citation docs found. Skipping final scoring.")
        final_docs = []
    else:
        print(f"Scoring {len(new_docs)} reference and citation abstracts...")
        scored_refs = score_documents(plan_text, new_docs)
        final_docs, final_cutoff = filter_high_docs(scored_refs, SIMILARITY_QUANTILE)
        print(f"Final docs above quantile cutoff ({SIMILARITY_QUANTILE}): {len(final_docs)} (cutoff={final_cutoff:.3f})")

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


if __name__ == "__main__":
    main()
