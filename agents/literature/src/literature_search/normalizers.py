"""
Record normalization functionality for standardizing data from different sources.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RecordNormalizer:
    """Normalizes records from different academic sources to a common schema."""
    
    def normalize_records(self, records: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
        """
        Normalize records from a specific source to common schema.
        
        Args:
            records: Raw records from source
            source: Source identifier
            
        Returns:
            List of normalized records
        """
        normalized = []
        
        for record in records:
            try:
                normalized_record = {
                    'source': source,
                    'title': self._extract_field(record, ['title', 'Title']),
                    'authors': self._extract_authors(record),
                    'abstract': self._extract_field(record, ['abstract', 'Abstract', 'summary']),
                    'doi': self._extract_field(record, ['doi', 'DOI', 'externalIds.DOI']),
                    'pmid': self._extract_field(record, ['pmid', 'PMID', 'externalIds.PubMed']),
                    'arxiv_id': self._extract_field(record, ['arxiv_id', 'id']),
                    'year': self._extract_year(record),
                    'journal': self._extract_field(record, ['journal', 'venue', 'Journal', 'container-title']),
                    'url': self._extract_field(record, ['url', 'URL', 'link']),
                    'citation_count': self._extract_field(record, ['citationCount', 'citations', 'is-referenced-by-count']),
                    'publication_type': self._extract_field(record, ['type', 'publication_type']),
                    'mesh_terms': record.get('mesh_terms', []) if source == 'pubmed' else [],
                    'categories': record.get('categories', []) if source == 'arxiv' else [],
                    'raw_data': record,  # Store original data
                    'retrieval_timestamp': datetime.now().isoformat()
                }
                normalized.append(normalized_record)
                
            except Exception as e:
                logger.warning(f"Error normalizing record from {source}: {str(e)}")
                continue
        
        return normalized
    
    def _extract_field(self, record: Dict[str, Any], field_names: List[str]) -> Optional[str]:
        """Extract field value using multiple possible field names."""
        for field_name in field_names:
            if '.' in field_name:
                # Handle nested fields
                value = record
                for part in field_name.split('.'):
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        value = None
                        break
                if value:
                    # Handle lists by taking the first element or joining
                    if isinstance(value, list):
                        if len(value) > 0:
                            return str(value[0]) if value[0] else None
                        else:
                            return None
                    return str(value)
            else:
                if field_name in record and record[field_name]:
                    value = record[field_name]
                    # Handle lists by taking the first element or joining
                    if isinstance(value, list):
                        if len(value) > 0:
                            return str(value[0]) if value[0] else None
                        else:
                            return None
                    return str(value)
        return None
    
    def _extract_authors(self, record: Dict[str, Any]) -> List[str]:
        """Extract and normalize author information."""
        authors = []
        
        # Try different author field formats
        author_fields = ['authors', 'Authors', 'author', 'Author']
        
        for field in author_fields:
            if field in record and record[field]:
                author_data = record[field]
                
                if isinstance(author_data, list):
                    for author in author_data:
                        if isinstance(author, dict):
                            # Handle different author formats
                            name = None
                            if 'name' in author:
                                name = author['name']
                            elif 'given' in author and 'family' in author:
                                # CrossRef format
                                name = f"{author.get('given', '')} {author.get('family', '')}"
                            elif 'firstName' in author and 'lastName' in author:
                                # Other formats
                                name = f"{author.get('firstName', '')} {author.get('lastName', '')}"
                            elif 'forename' in author and 'lastname' in author:
                                # PubMed format
                                name = f"{author.get('forename', '')} {author.get('lastname', '')}"
                            
                            if name and name.strip():
                                authors.append(name.strip())
                        elif isinstance(author, str):
                            authors.append(author)
                elif isinstance(author_data, str):
                    # Parse string of authors
                    authors.extend([a.strip() for a in author_data.split(',') if a.strip()])
                
                if authors:
                    break
        
        return authors
    
    def _extract_year(self, record: Dict[str, Any]) -> Optional[int]:
        """Extract publication year."""
        year_fields = ['year', 'Year', 'publicationDate', 'date', 'published']
        
        for field in year_fields:
            if field in record and record[field]:
                year_value = record[field]
                
                if isinstance(year_value, int):
                    return year_value
                elif isinstance(year_value, str):
                    # Try to extract year from date strings
                    year_match = re.search(r'\b(19|20)\d{2}\b', year_value)
                    if year_match:
                        return int(year_match.group())
        
        # Handle CrossRef date arrays
        if 'published-print' in record:
            date_parts = record['published-print'].get('date-parts', [])
            if date_parts and len(date_parts[0]) > 0:
                return int(date_parts[0][0])
        
        if 'published-online' in record:
            date_parts = record['published-online'].get('date-parts', [])
            if date_parts and len(date_parts[0]) > 0:
                return int(date_parts[0][0])
        
        if 'created' in record:
            date_parts = record['created'].get('date-parts', [])
            if date_parts and len(date_parts[0]) > 0:
                return int(date_parts[0][0])
        
        return None
