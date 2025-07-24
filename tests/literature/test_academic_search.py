#!/usr/bin/env python3
"""
Simple test script for academic search functionality.

This script asks for a search query and tests the comprehensive_academic_search 
method in the LiteratureAgent, which searches PubMed, arXiv, and Semantic Scholar.

Author: Eunice AI System
Date: July 2025
"""

import asyncio
import os
import sys

def main():
    """Main function to run the academic search test."""
    SEARCH_RESULTS = 3
    
    print("Academic Search Test")
    print("=" * 50)
    
    # Get search query from user
    search_query = input("Enter your search query: ").strip()
    
    if not search_query:
        print("No search query provided. Using default: 'artificial intelligence'.")
        search_query = "artificial intelligence"
    
    print(f"\nSearching for: '{search_query}'")
    
    # Create and run the async test
    async def run_test():
        # Set up environment - SSL verification is now handled automatically
        # No need to disable SSL verification thanks to improved certificate handling
        
        # Add project root to sys.path
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        try:
            # Import required modules
            from src.config.config_manager import ConfigManager
            from src.agents.literature_agent import LiteratureAgent
            
            print("✓ Successfully imported required modules")
            print("✓ Initializing Literature Agent...")
            
            # Initialize the Literature Agent
            config_manager = ConfigManager()
            literature_agent = LiteratureAgent(config_manager)
            
            print("✓ Literature Agent initialized successfully")
            print("🔍 Running comprehensive academic search...")
            print("   This searches PubMed, arXiv, and Semantic Scholar...")
            
            # Call the comprehensive search function
            results_by_source = await literature_agent.comprehensive_academic_search(
                query=search_query,
                max_results_per_source=SEARCH_RESULTS,
                include_pubmed=True,
                include_arxiv=True,
                include_semantic_scholar=True,
                use_cache=True
            )
            
            # Display results
            print("\n" + "="*60)
            print("SEARCH RESULTS")
            print("="*60)
            
            total_results = 0
            sources_with_results = []
            
            for source, results in results_by_source.items():
                if results:
                    sources_with_results.append(source)
                    print(f"\n{source.upper()}: {len(results)} results\n")
                    total_results += len(results)
                    
                    # Show first few results from each source
                    for i, result in enumerate(results, 1):
                        title = result.get('title', 'No title')
                        print(f"  {i}. {title}")
                        
                        # Display authors
                        if result.get('authors'):
                            authors = result['authors']
                            if isinstance(authors, list):
                                author_names = []
                                for author in authors[:3]:
                                    if isinstance(author, dict):
                                        author_names.append(author.get('name', str(author)))
                                    else:
                                        author_names.append(str(author))
                                print(f"     Authors: {', '.join(author_names)}")
                            else:
                                print(f"     Authors: {authors}")
                        
                        # Display year
                        if result.get('year'):
                            print(f"     Year: {result['year']}")
                        
                        # Display abstract (truncated)
                        if result.get('abstract'):
                            abstract = result['abstract']
                            if len(abstract) > 150:
                                abstract = abstract[:150] + "..."
                            print(f"     Abstract: {abstract}")
                        
                        print()
                else:
                    print(f"\n{source.upper()}: 0 results")
            
            # Summary
            print(f"📊 SUMMARY:")
            print(f"   Total results found: {total_results}")
            print(f"   Sources with results: {', '.join(sources_with_results) if sources_with_results else 'None'}")
            print(f"   Sources searched: {', '.join(results_by_source.keys())}")
            
            # Cleanup
            await literature_agent._cleanup_agent()
            
            print("\n✅ Test completed successfully!")
            return True
            
        except ImportError as e:
            print(f"❌ Import error: {e}")
            print("Make sure all dependencies are installed.")
            print("Try running from the project root directory.")
            return False
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # Run the async test
    try:
        success = asyncio.run(run_test())
        if success:
            print("\n🎉 Academic search functionality is working correctly!")
        else:
            print("\n❌ Academic search test failed. Check the errors above.")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n❌ Failed to run test: {e}")

if __name__ == "__main__":
    main()
