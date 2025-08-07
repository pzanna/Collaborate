"""
XML and data parsers for various academic database responses.
"""

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ArxivParser:
    """Parser for arXiv XML responses."""
    
    def parse_xml(self, xml_content: str) -> List[Dict[str, Any]]:
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
                            authors.append(name.text.strip())
                    
                    # Extract arXiv ID from id
                    entry_id = entry.find('atom:id', ns)
                    arxiv_id = None
                    if entry_id is not None and entry_id.text:
                        # Extract ID from URL like http://arxiv.org/abs/2301.12345v1
                        match = re.search(r'abs/([0-9]+\.[0-9]+)', entry_id.text)
                        if match:
                            arxiv_id = match.group(1)
                    
                    # Extract categories
                    categories = []
                    for category in entry.findall('atom:category', ns):
                        term = category.get('term')
                        if term:
                            categories.append(term)
                    
                    record = {
                        'title': title.text.strip() if title is not None and title.text else None,
                        'abstract': summary.text.strip() if summary is not None and summary.text else None,
                        'authors': authors,
                        'published': published.text if published is not None else None,
                        'arxiv_id': arxiv_id,
                        'url': entry_id.text if entry_id is not None else None,
                        'categories': categories
                    }
                    entries.append(record)
                    
                except Exception as e:
                    logger.warning(f"Error parsing arXiv entry: {e}")
                    continue
            
            return entries
            
        except Exception as e:
            logger.error(f"Error parsing arXiv XML: {e}")
            return []


class PubmedParser:
    """Parser for PubMed XML responses."""
    
    def parse_xml(self, xml_content: str) -> List[Dict[str, Any]]:
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
                    
                    # Extract keywords/MeSH terms
                    mesh_terms = []
                    for mesh in article.findall('.//MeshHeading/DescriptorName'):
                        if mesh.text:
                            mesh_terms.append(mesh.text)
                    
                    record = {
                        'title': title_elem.text if title_elem is not None and title_elem.text else None,
                        'abstract': abstract_elem.text if abstract_elem is not None and abstract_elem.text else None,
                        'authors': authors,
                        'pmid': pmid_elem.text if pmid_elem is not None and pmid_elem.text else None,
                        'year': year_elem.text if year_elem is not None and year_elem.text else None,
                        'journal': journal_elem.text if journal_elem is not None and journal_elem.text else None,
                        'doi': doi_elem.text if doi_elem is not None and doi_elem.text else None,
                        'mesh_terms': mesh_terms
                    }
                    entries.append(record)
                    
                except Exception as e:
                    logger.warning(f"Error parsing PubMed entry: {e}")
                    continue
            
            return entries
            
        except Exception as e:
            logger.error(f"Error parsing PubMed XML: {e}")
            return []
