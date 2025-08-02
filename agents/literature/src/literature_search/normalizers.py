"""
Record normalization functionality for standardizing data from different sources.
"""

import logging
import re
import uuid
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
            List of normalized records (excluding those with empty abstracts)
        """
        normalized = []
        
        for record in records:
            try:
                # Extract external ID (pmid or arxiv_id)
                external_id = self._extract_external_id(record, source)
                
                # Generate PDF URL based on the external ID and source
                pdf_url = self._generate_pdf_url(record, source, external_id)
                
                # Extract abstract and check if it's empty
                abstract = self._extract_field(record, ['abstract', 'Abstract', 'summary'])
                
                # Filter out records with empty abstracts
                if not abstract or not abstract.strip():
                    logger.debug(f"Skipping record from {source} with empty abstract: {self._extract_field(record, ['title', 'Title'])}")
                    continue
                
                normalized_record = {
                    'internal_id': str(uuid.uuid4()),  # Generate unique internal ID
                    'source': source,
                    'title': self._extract_field(record, ['title', 'Title']),
                    'authors': self._extract_authors(record),
                    'abstract': abstract,
                    'doi': self._extract_field(record, ['doi', 'DOI', 'externalIds.DOI']),
                    'external_id': external_id,
                    'year': self._extract_year(record),
                    'journal': self._extract_field(record, ['journal', 'venue', 'Journal', 'container-title']),
                    'url': pdf_url or self._extract_field(record, ['url', 'URL', 'link']),
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
    
    def filter_records_with_abstracts(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out records that have empty or missing abstracts.
        
        Args:
            records: List of normalized records
            
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
    
    def _extract_external_id(self, record: Dict[str, Any], source: str) -> Optional[str]:
        """Extract external ID based on source type."""
        if source == 'pubmed':
            pmid = self._extract_field(record, ['pmid', 'PMID', 'externalIds.PubMed'])
            if pmid:
                return f"pmid:{pmid}"
        elif source == 'arxiv':
            arxiv_id = self._extract_field(record, ['arxiv_id', 'id'])
            if arxiv_id:
                # Clean arXiv ID - extract just the ID part if it's a full URL
                if 'arxiv.org/abs/' in str(arxiv_id):
                    arxiv_id = str(arxiv_id).split('abs/')[-1]
                # Remove version number if present (e.g., 2301.12345v1 -> 2301.12345)
                if 'v' in str(arxiv_id):
                    arxiv_id = str(arxiv_id).split('v')[0]
                return f"arxiv:{arxiv_id}"
        elif source == 'semantic_scholar':
            # Check for DOI, PMID, or arXiv ID in external IDs
            if 'externalIds' in record:
                ext_ids = record['externalIds']
                if ext_ids.get('PubMed'):
                    return f"pmid:{ext_ids['PubMed']}"
                elif ext_ids.get('ArXiv'):
                    arxiv_id = ext_ids['ArXiv']
                    # Clean arXiv ID
                    if 'v' in str(arxiv_id):
                        arxiv_id = str(arxiv_id).split('v')[0]
                    return f"arxiv:{arxiv_id}"
        elif source == 'crossref':
            # CrossRef primarily uses DOI, but check for other external IDs
            pmid = self._extract_field(record, ['pmid', 'PMID'])
            if pmid:
                return f"pmid:{pmid}"
        elif source == 'core':
            # CORE uses its own id system
            core_id = self._extract_field(record, ['id', 'coreId'])
            if core_id:
                return f"core:{core_id}"
            
        return None
    
    def _generate_pdf_url(self, record: Dict[str, Any], source: str, external_id: Optional[str]) -> Optional[str]:
        """Generate PDF download URL based on source and external ID."""
        # First, check for source-specific PDF URLs
        if source == 'semantic_scholar':
            # Check if Semantic Scholar provides a PDF URL
            if 'openAccessPdf' in record and record['openAccessPdf']:
                if isinstance(record['openAccessPdf'], dict):
                    pdf_url = record['openAccessPdf'].get('url')
                    if pdf_url:
                        return pdf_url
                elif isinstance(record['openAccessPdf'], str):
                    return record['openAccessPdf']
        elif source == 'crossref':
            # Check for open access PDF URL
            if 'link' in record:
                for link in record['link']:
                    if link.get('content-type') == 'application/pdf':
                        return link.get('URL')
        elif source == 'core':
            # CORE provides downloadUrl for PDF access
            download_url = self._extract_field(record, ['downloadUrl', 'fullTextUrl', 'pdf_url'])
            if download_url:
                return download_url
        
        # Then fall back to external_id-based URLs
        if not external_id:
            return None
            
        if external_id.startswith('arxiv:'):
            arxiv_id = external_id[6:]  # Remove 'arxiv:' prefix
            return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        elif external_id.startswith('pmid:'):
            pmid = external_id[5:]  # Remove 'pmid:' prefix
            # Try to get PMC ID for PDF access
            pmc_id = record.get('pmc_id') or record.get('PMC')
            if pmc_id:
                # Clean PMC ID
                if pmc_id.startswith('PMC'):
                    pmc_id = pmc_id[3:]
                return f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/"
            else:
                # Fallback to PubMed page (not PDF, but accessible)
                return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        elif external_id.startswith('core:'):
            core_id = external_id[5:]  # Remove 'core:' prefix
            # For CORE, check if record has a DOI first (more reliable)
            doi = record.get('doi') or record.get('DOI')
            if doi:
                return f"https://doi.org/{doi}"
            # Otherwise use CORE direct access URL
            return f"https://core.ac.uk/download/{core_id}.pdf"
        
        # Final fallback to generic URL fields
        if source == 'semantic_scholar' and 'url' in record:
            return record['url']
        elif source == 'crossref':
            # Check DOI-based PDF access
            doi = record.get('DOI')
            if doi:
                return f"https://doi.org/{doi}"
        elif source == 'core':
            # CORE fallback - try to construct URL from any available identifier
            doi = record.get('doi')
            if doi:
                return f"https://doi.org/{doi}"
            # Or fallback to CORE page
            core_id = record.get('id')
            if core_id:
                return f"https://core.ac.uk/works/{core_id}"
                
        return None
