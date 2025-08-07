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
        Deduplicate records using DOI, external_id, internal_id, or title/author/year heuristics.
        
        Args:
            records: List of normalized records
            
        Returns:
            List of unique records
        """
        seen_dois = set()
        seen_external_ids = set()
        seen_internal_ids = set()
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
            
            # Check external_id (pmid: or arxiv: prefixed)
            external_id = record.get('external_id')
            if not is_duplicate and external_id:
                if external_id in seen_external_ids:
                    is_duplicate = True
                else:
                    seen_external_ids.add(external_id)
            
            # Check internal_id (UUID-based)
            internal_id = record.get('internal_id')
            if not is_duplicate and internal_id:
                if internal_id in seen_internal_ids:
                    is_duplicate = True
                else:
                    seen_internal_ids.add(internal_id)
            
            # Check title/author/year hash if no unique identifiers
            if not is_duplicate and not doi and not external_id and not internal_id:
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
    
    def filter_records_with_abstracts(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out records that have empty or missing abstracts.
        
        Args:
            records: List of records to filter
            
        Returns:
            List of records with non-empty abstracts
        """
        filtered_records = []
        
        for record in records:
            abstract = record.get('abstract', '')
            if abstract and abstract.strip():
                filtered_records.append(record)
            else:
                logger.debug(f"Filtering out record with empty abstract: {record.get('title', 'Unknown title')}")
        
        logger.info(f"Filtered {len(records) - len(filtered_records)} records with empty abstracts. "
                   f"Remaining: {len(filtered_records)} records")
        
        return filtered_records
