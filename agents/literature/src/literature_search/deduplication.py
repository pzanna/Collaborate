"""
Record deduplication functionality for removing duplicate literature records.
"""

import hashlib
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class RecordDeduplicator:
    """Handles deduplication of literature records across multiple sources."""
    
    def deduplicate_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate records using DOI, PMID, arXiv ID, or title/author/year heuristics.
        
        Args:
            records: List of normalized records
            
        Returns:
            List of unique records
        """
        seen_dois = set()
        seen_pmids = set()
        seen_arxiv_ids = set()
        seen_hashes = set()
        unique_records = []
        
        for record in records:
            is_duplicate = False
            
            # Check DOI first (most reliable)
            doi = record.get('doi')
            if doi:
                if doi in seen_dois:
                    is_duplicate = True
                else:
                    seen_dois.add(doi)
            
            # Check PMID
            pmid = record.get('pmid')
            if not is_duplicate and pmid:
                if pmid in seen_pmids:
                    is_duplicate = True
                else:
                    seen_pmids.add(pmid)
            
            # Check arXiv ID
            arxiv_id = record.get('arxiv_id')
            if not is_duplicate and arxiv_id:
                if arxiv_id in seen_arxiv_ids:
                    is_duplicate = True
                else:
                    seen_arxiv_ids.add(arxiv_id)
            
            # Check title/author/year hash if no unique identifiers
            if not is_duplicate and not doi and not pmid and not arxiv_id:
                content_hash = self._generate_content_hash(record)
                if content_hash in seen_hashes:
                    is_duplicate = True
                else:
                    seen_hashes.add(content_hash)
            
            if not is_duplicate:
                unique_records.append(record)
        
        return unique_records
    
    def deduplicate_source_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates within a single source's results."""
        seen_identifiers = set()
        unique_results = []
        
        for result in results:
            # Create a unique identifier for this result
            identifier = None
            
            # Try DOI first (most reliable)
            if 'doi' in result and result['doi']:
                identifier = f"doi:{result['doi']}"
            # Try arXiv ID
            elif 'id' in result and result['id'] and 'arxiv' in str(result['id']).lower():
                identifier = f"arxiv:{result['id']}"
            # Try paper ID (for Semantic Scholar)
            elif 'paperId' in result and result['paperId']:
                identifier = f"paperId:{result['paperId']}"
            # Fall back to title-based identification
            elif 'title' in result and result['title']:
                title_value = result['title']
                # Handle lists by taking the first element
                if isinstance(title_value, list):
                    title_value = title_value[0] if len(title_value) > 0 and title_value[0] else ""
                identifier = f"title:{str(title_value).lower().strip()}"
            
            if identifier and identifier not in seen_identifiers:
                seen_identifiers.add(identifier)
                unique_results.append(result)
            elif not identifier:
                # If we can't create an identifier, include it anyway
                unique_results.append(result)
        
        return unique_results
    
    def _generate_content_hash(self, record: Dict[str, Any]) -> str:
        """Generate hash for title/author/year deduplication."""
        title = (record.get('title') or '').lower().strip()
        authors = record.get('authors', [])
        year = record.get('year')
        
        # Create normalized string for hashing
        author_string = ', '.join(sorted([a.lower().strip() for a in authors]))
        content_string = f"{title}|{author_string}|{year}"
        
        return hashlib.md5(content_string.encode(), usedforsecurity=False).hexdigest()
