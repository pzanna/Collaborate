#!/usr/bin/env python3
"""
Test script for the Academic Search API.

This script demonstrates how to use the comprehensive_academic_search API endpoint
both programmatically and via HTTP requests.

Author: Eunice AI System
Date: July 2025
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any

def add_project_to_path():
    """Add project root to Python path."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

def main():
    """Main function to test the Academic Search API."""
    
    print("Academic Search API Test")
    print("=" * 50)
    
    # Get search query from user
    search_query = input("Enter your search query: ").strip()
    
    if not search_query:
        print("No search query provided. Using default: 'artificial intelligence'.")
        search_query = "artificial intelligence"
    
    print(f"\nSearching for: '{search_query}'")
    
    # Test the API programmatically
    async def test_api_direct():
        """Test the API by calling the function directly."""
        add_project_to_path()
        
        try:
            from old_src.api.academic_search_api import comprehensive_academic_search, get_literature_agent
            from old_src.models.academic_search_models import AcademicSearchRequest
            
            print("✓ Successfully imported API modules")
            print("✓ Initializing Literature Agent...")
            
            # Get literature agent
            literature_agent = await get_literature_agent()
            
            print("✓ Literature Agent initialized successfully")
            print("🔍 Testing comprehensive academic search API...")
            
            # Create request
            request = AcademicSearchRequest(
                query=search_query,
                max_results_per_source=5,
                include_pubmed=True,
                include_arxiv=True,
                include_semantic_scholar=True,
                use_cache=True
            )
            
            # Call the API function
            response = await comprehensive_academic_search(request, literature_agent)
            
            # Display results
            print("\\n" + "="*60)
            print("API RESPONSE")
            print("="*60)
            
            print(f"Query: {response.query}")
            print(f"Total Results: {response.total_results}")
            print(f"Sources Searched: {', '.join(response.sources_searched)}")
            print(f"Sources with Results: {', '.join(response.sources_with_results)}")
            print(f"Cache Used: {response.cache_used}")
            print(f"Search Timestamp: {response.search_timestamp}")
            
            for source, papers in response.results_by_source.items():
                if papers:
                    print(f"\\n{source.upper()}: {len(papers)} results")
                    for i, paper in enumerate(papers[:3], 1):  # Show first 3 results
                        print(f"  {i}. {paper.title}")
                        if paper.metadata.get('authors'):
                            authors = paper.metadata['authors']
                            if isinstance(authors, list):
                                author_str = ', '.join(authors[:3])
                                if len(authors) > 3:
                                    author_str += ' et al.'
                                print(f"     Authors: {author_str}")
                        
                        if paper.metadata.get('publication_date'):
                            print(f"     Date: {paper.metadata['publication_date']}")
                        
                        if paper.metadata.get('citation_count'):
                            print(f"     Citations: {paper.metadata['citation_count']}")
                        
                        print(f"     URL: {paper.url}")
                        print()
                else:
                    print(f"\\n{source.upper()}: 0 results")
            
            print("\\n✅ API test completed successfully!")
            return True
            
        except ImportError as e:
            print(f"❌ Import error: {e}")
            print("Make sure all dependencies are installed.")
            return False
        except Exception as e:
            print(f"❌ API test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Test with HTTP client (optional)
    def test_api_http():
        """Test the API using HTTP requests (requires server to be running)."""
        try:
            import requests
            
            print("\\n" + "="*60)
            print("HTTP API TEST (Optional)")
            print("="*60)
            print("Testing HTTP API endpoint...")
            
            # API endpoint URL (adjust as needed)
            api_url = "http://localhost:8000/api/v2/academic/search"
            
            # Request payload
            payload = {
                "query": search_query,
                "max_results_per_source": 5,
                "include_pubmed": True,
                "include_arxiv": True,
                "include_semantic_scholar": True,
                "use_cache": True
            }
            
            # Make POST request
            response = requests.post(api_url, json=payload, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ HTTP API Success: {data['total_results']} total results")
                print(f"   Sources: {', '.join(data['sources_with_results'])}")
            else:
                print(f"❌ HTTP API Error: {response.status_code}")
                print(f"   Response: {response.text}")
            
        except ImportError:
            print("📝 Skipping HTTP test (requests library not available)")
        except Exception as e:
            if "Connection" in str(type(e).__name__):
                print("📝 Skipping HTTP test (API server not running)")
                print("   To test HTTP endpoint, start the FastAPI server first:")
                print("   uvicorn src.main:app --reload")
            else:
                print(f"❌ HTTP test failed: {e}")
    
    # Run the direct API test
    try:
        success = asyncio.run(test_api_direct())
        if success:
            print("\\n🎉 Academic Search API is working correctly!")
            
            # Optionally test HTTP endpoint
            print("\\nTesting HTTP endpoint (requires running server)...")
            test_api_http()
        else:
            print("\\n❌ Academic Search API test failed. Check the errors above.")
    except KeyboardInterrupt:
        print("\\n\\nTest interrupted by user.")
    except Exception as e:
        print(f"\\n❌ Failed to run API test: {e}")

def print_api_documentation():
    """Print API usage documentation."""
    docs = '''
    
📚 ACADEMIC SEARCH API DOCUMENTATION
====================================

The Academic Search API provides comprehensive search across multiple academic databases:
- PubMed (biomedical literature)
- arXiv (preprints and research papers)
- Semantic Scholar (multidisciplinary with AI-powered features)

🔗 ENDPOINTS:

1. POST /api/v2/academic/search
   - Full-featured search with JSON request body
   - Supports all parameters and options

2. GET /api/v2/academic/search?query=...
   - Simple search using URL parameters
   - Good for quick queries

3. GET /api/v2/academic/sources
   - Information about available sources

4. GET /api/v2/academic/health
   - Service health check

📋 REQUEST PARAMETERS:

- query (required): Search terms
- max_results_per_source (default: 10): Results per database
- include_pubmed (default: true): Include PubMed results
- include_arxiv (default: true): Include arXiv results  
- include_semantic_scholar (default: true): Include Semantic Scholar results
- use_cache (default: true): Use cached results for performance

📄 RESPONSE FORMAT:

{
  "query": "search terms",
  "total_results": 30,
  "sources_searched": ["pubmed", "arxiv", "semantic_scholar"],
  "sources_with_results": ["pubmed", "arxiv", "semantic_scholar"],
  "results_by_source": {
    "pubmed": [...],
    "arxiv": [...],
    "semantic_scholar": [...]
  },
  "search_timestamp": "2025-01-20T10:30:00Z",
  "cache_used": true
}

🚀 USAGE EXAMPLES:

Python (requests):
```python
import requests

response = requests.post("http://localhost:8000/api/v2/academic/search", json={
    "query": "machine learning neural networks",
    "max_results_per_source": 10
})
results = response.json()
```

cURL:
```bash
curl -X POST "http://localhost:8000/api/v2/academic/search" \\
     -H "Content-Type: application/json" \\
     -d '{"query": "quantum computing", "max_results_per_source": 5}'
```

Simple GET:
```
http://localhost:8000/api/v2/academic/search?query=artificial%20intelligence&max_results_per_source=5
```
'''
    print(docs)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--docs":
        print_api_documentation()
    else:
        main()
