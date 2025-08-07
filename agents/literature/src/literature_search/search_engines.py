# --- search_engines.py ---

import os
import time
import json
import requests
import xml.etree.ElementTree as ET
import re
from dotenv import load_dotenv

# Load environment variables
# Look for .env file in parent directory (repository root)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# --- Primary Configuration ---
SIMILARITY_QUANTILE = 0.8
TOP_K_TERMS = 1     # How many top search terms to use.
MAX_RETRIES = 5     # Maximum number of retries for API calls
BACKOFF_BASE = 5    # Starting backoff time in seconds
SEARCH_LIMIT = 5    # Limit for search results per search term
YEAR_RANGE = (2000, 2025)   # Default year range for searches

# API Keys
NCBI_API_KEY = os.getenv('NCBI_API_KEY')
OPENALEX_EMAIL = os.getenv('OPENALEX_EMAIL')
CORE_API_KEY = os.getenv('CORE_API_KEY')


# --- API Query ---
def query_openalex(term, limit=SEARCH_LIMIT):
    """Query OpenAlex API for papers."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Validate search term
    if not term or not str(term).strip():
        logger.warning("Empty search term provided to OpenAlex query")
        return []
    
    term = str(term).strip()
    logger.debug(f"Querying OpenAlex for term: '{term}' (limit: {limit})")
    
    retries = 0
    while retries < MAX_RETRIES:
        url = "https://api.openalex.org/works"
        
        params = {
            'search': term,
            'filter': 'type:article',  # Only research articles
            'sort': 'relevance_score:desc',
            'per-page': str(limit),
            'page': '1'
        }
        
        # Only add mailto if we have a valid email
        if OPENALEX_EMAIL:
            params['mailto'] = OPENALEX_EMAIL
        else:
            logger.debug("No OPENALEX_EMAIL configured - this may cause rate limiting")
        
        try:
            time.sleep(0.1)  # OpenAlex allows 10 requests/second
            r = requests.get(url, params=params, timeout=30)
            
            if r.status_code == 200:
                try:
                    data = r.json()
                    results = data.get("results", [])
                    logger.debug(f"OpenAlex returned {len(results)} results for '{term}'")
                    
                    # Transform OpenAlex results to match expected format
                    transformed_results = []
                    for result in results:
                        # Convert abstract inverted index to plain text
                        abstract_text = ""
                        abstract_index = result.get('abstract_inverted_index', {})
                        if abstract_index:
                            try:
                                # Reconstruct abstract from inverted index
                                max_pos = max(max(positions) for positions in abstract_index.values() if positions)
                                words = [""] * (max_pos + 1)
                                
                                for word, positions in abstract_index.items():
                                    for pos in positions:
                                        if pos < len(words):
                                            words[pos] = word
                                
                                abstract_text = " ".join(words).strip()
                                # Clean up extra spaces
                                import re
                                abstract_text = re.sub(r'\s+', ' ', abstract_text)
                            except Exception as e:
                                logger.debug(f"Error reconstructing abstract: {e}")
                                abstract_text = ""
                        
                        # Extract authors
                        authors = []
                        for authorship in result.get('authorships', []):
                            author = authorship.get('author', {})
                            if author.get('display_name'):
                                authors.append({'name': author['display_name']})
                        
                        # Extract external IDs
                        ids = result.get('ids', {})
                        external_ids = {}
                        if ids.get('doi'):
                            external_ids['DOI'] = ids['doi']
                        if ids.get('pmid'):
                            external_ids['PMID'] = ids['pmid']
                        
                        transformed_result = {
                            'paperId': result.get('id', '').replace('https://openalex.org/', ''),
                            'title': result.get('title') or result.get('display_name', ''),
                            'abstract': abstract_text,
                            'authors': authors,
                            'year': result.get('publication_year'),
                            'externalIds': external_ids,
                            'references': result.get('referenced_works', []),  # OpenAlex provides references
                            'url': result.get('primary_location', {}).get('pdf_url')  # PDF URL from OpenAlex
                        }
                        transformed_results.append(transformed_result)
                    
                    logger.info(f"Successfully queried OpenAlex: {len(transformed_results)} papers for '{term}'")
                    return transformed_results
                    
                except Exception as e:
                    logger.error(f"Error parsing OpenAlex response for '{term}': {e}")
                    break
                    
            elif r.status_code == 429:
                delay = BACKOFF_BASE * 2**retries
                logger.warning(f"OpenAlex rate limited for '{term}'. Retrying in {delay}s...")
                time.sleep(delay)
                retries += 1
            elif r.status_code == 403:
                logger.error(f"OpenAlex API access forbidden (403) for '{term}'. Check email configuration.")
                if not OPENALEX_EMAIL:
                    logger.error("No OPENALEX_EMAIL configured. Set this environment variable to avoid 403 errors.")
                break
            else:
                logger.error(f"OpenAlex API error for '{term}': HTTP {r.status_code}")
                if r.text:
                    logger.debug(f"Response: {r.text[:200]}...")
                break
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout querying OpenAlex for '{term}', retrying...")
            retries += 1
        except Exception as e:
            logger.error(f"Unexpected error querying OpenAlex for '{term}': {e}")
            break
    
    logger.warning(f"Failed to query OpenAlex for term: '{term}' after {retries} retries")
    return []

def query_pubmed(term, limit=SEARCH_LIMIT):
    """Query PubMed API for papers."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Validate search term
    if not term or not str(term).strip():
        logger.warning("Empty search term provided to PubMed query")
        return []
    
    term = str(term).strip()
    logger.debug(f"Querying PubMed for term: '{term}' (limit: {limit})")
    
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
            else:
                logger.debug("No NCBI_API_KEY configured - using slower rate limits")
            
            time.sleep(1 if NCBI_API_KEY else 2)  # Faster rate limit with API key
            r = requests.get(search_url, params=search_params, timeout=30)
            
            if r.status_code == 200:
                search_data = r.json()
                id_list = search_data.get('esearchresult', {}).get('idlist', [])
                
                if not id_list:
                    logger.info(f"No PubMed results found for term: '{term}'")
                    return []
                
                logger.debug(f"Found {len(id_list)} PubMed IDs for '{term}'")
                
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
                r = requests.get(fetch_url, params=fetch_params, timeout=30)
                
                if r.status_code == 200:
                    papers = parse_pubmed_xml(r.text)
                    logger.info(f"Successfully queried PubMed: {len(papers)} papers for '{term}'")
                    return papers
                else:
                    logger.error(f"PubMed fetch failed with status {r.status_code}")
                    return []
                    
            elif r.status_code == 429:
                delay = BACKOFF_BASE * 2**retries
                logger.warning(f"PubMed rate limited for '{term}'. Retrying in {delay}s...")
                time.sleep(delay)
                retries += 1
            else:
                logger.error(f"PubMed API error for '{term}': HTTP {r.status_code}")
                break
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout querying PubMed for '{term}', retrying...")
            retries += 1
        except Exception as e:
            logger.error(f"Unexpected error querying PubMed for '{term}': {e}")
            break
            
    logger.warning(f"Failed to query PubMed for term: '{term}' after {retries} retries")
    return []

def query_arxiv(term, limit=SEARCH_LIMIT):
    """Query arXiv API for papers."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Validate search term
    if not term or not str(term).strip():
        logger.warning("Empty search term provided to arXiv query")
        return []
    
    term = str(term).strip()
    logger.debug(f"Querying arXiv for term: '{term}' (limit: {limit})")
    
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
            
            logger.debug(f"arXiv search parameters: {params}")
            
            time.sleep(5)  # arXiv rate limit
            r = requests.get(url, params=params, timeout=30)
            
            if r.status_code == 200:
                papers = parse_arxiv_xml(r.text)
                logger.info(f"Successfully queried arXiv: {len(papers)} papers for '{term}'")
                return papers
            elif r.status_code == 429:
                delay = BACKOFF_BASE * 2**retries
                logger.warning(f"arXiv rate limited for '{term}'. Retrying in {delay}s...")
                time.sleep(delay)
                retries += 1
            else:
                logger.error(f"arXiv API error for '{term}': HTTP {r.status_code}")
                break
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout querying arXiv for '{term}', retrying...")
            retries += 1
        except Exception as e:
            logger.error(f"Unexpected error querying arXiv for '{term}': {e}")
            break
            
    logger.warning(f"Failed to query arXiv for term: '{term}' after {retries} retries")
    return []

def query_core(term, limit=SEARCH_LIMIT):
    """Search CORE API."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Validate search term
    if not term or not str(term).strip():
        logger.warning("Empty search term provided to CORE query")
        return []
    
    term = str(term).strip()
    logger.debug(f"Querying CORE for term: '{term}' (limit: {limit})")
    
    retries = 0
    while retries < MAX_RETRIES:
        try:
            url = "https://api.core.ac.uk/v3/search/works"

            # Simplify the query - remove complex syntax that's causing issues
            params = {
                'q': term,  # Use simple term without complex syntax
                'limit': limit,
            }
            
            # Add API key as query parameter if available
            if CORE_API_KEY:
                params['apiKey'] = CORE_API_KEY
            else:
                logger.debug("No CORE_API_KEY configured - using anonymous access")

            logger.debug(f"CORE search parameters: {params}")
            
            r = requests.get(url, params=params, timeout=30)

            if r.status_code == 200:
                papers = parse_core_json(r.text)
                logger.info(f"Successfully queried CORE: {len(papers)} papers for '{term}'")
                return papers
            elif r.status_code == 429:
                delay = BACKOFF_BASE * 2**retries
                logger.warning(f"CORE rate limited for '{term}'. Retrying in {delay}s...")
                time.sleep(delay)
                retries += 1
            else:
                logger.error(f"CORE API error for '{term}': HTTP {r.status_code}")
                break
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout querying CORE for '{term}', retrying...")
            retries += 1
        except Exception as e:
            logger.error(f"Unexpected error querying CORE for '{term}': {e}")
            break

    logger.warning(f"Failed to query CORE for term: '{term}' after {retries} retries")
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
                    'references': [],  # PubMed doesn't include references in basic fetch
                    'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid_elem.text}/" if pmid_elem is not None and pmid_elem.text else None
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
                    'references': [],  # arXiv doesn't include references
                    'url': f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None
                }
                entries.append(record)
                
            except Exception as e:
                print(f"Error parsing arXiv entry: {e}")
                continue
        
        return entries
        
    except Exception as e:
        print(f"Error parsing arXiv XML: {e}")
        return []

def parse_core_json(json_content):
    """Parse CORE API JSON response."""
    try:
        data = json.loads(json_content)
        entries = []
        
        # CORE API v3 returns results in 'results' array
        results = data.get('results', [])
        
        for result in results:
            try:
                # Extract basic information
                title = result.get('title')
                abstract = result.get('abstract')
                
                # Extract authors
                authors = []
                for author in result.get('authors', []):
                    if isinstance(author, dict):
                        name = author.get('name')
                        if name:
                            authors.append({'name': name})
                    elif isinstance(author, str):
                        authors.append({'name': author})
                
                # Extract publication year
                year = result.get('yearPublished')
                if isinstance(year, str):
                    try:
                        year = int(year)
                    except:
                        year = None
                
                # Extract DOI and other IDs
                external_ids = {}
                doi = result.get('doi')
                if doi:
                    external_ids['DOI'] = doi
                
                # Extract URLs
                download_url = result.get('downloadUrl')
                
                record = {
                    'paperId': result.get('id'),
                    'title': title,
                    'abstract': abstract,
                    'authors': authors,
                    'year': year,
                    'externalIds': external_ids,
                    'references': [],  # CORE doesn't include references in basic search
                    'url': download_url
                }
                entries.append(record)
                
            except Exception as e:
                print(f"Error parsing CORE entry: {e}")
                continue
        
        return entries
        
    except Exception as e:
        print(f"Error parsing CORE JSON: {e}")
        return []


# Export all search engine functions for easy importing
__all__ = [
    'query_openalex',
    'query_pubmed', 
    'query_arxiv',
    'query_core',
    'parse_pubmed_xml',
    'parse_arxiv_xml',
    'parse_core_json',
    # Configuration constants
    'SIMILARITY_QUANTILE',
    'TOP_K_TERMS',
    'MAX_RETRIES',
    'BACKOFF_BASE',
    'SEARCH_LIMIT',
    'YEAR_RANGE',
    'NCBI_API_KEY',
    'OPENALEX_EMAIL',
    'CORE_API_KEY'
]