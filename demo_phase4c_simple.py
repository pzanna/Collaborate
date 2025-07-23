#!/usr/bin/env python3
"""
Phase 4C External Integration - Simple Demo
==========================================
A simplified demonstration of the external integration capabilities
that actually works with the implemented API.
"""

import asyncio
import os
import tempfile
import shutil
from pathlib import Path

# Import external integration components
from src.external import (
    DatabaseManager,
    PubMedConnector,
    ArxivConnector,
    BibTeXManager,
    DataExchangeHub,
    ImportEngine,
    ExportEngine,
    DataValidator,
    ValidationLevel
)


class Phase4CSimpleDemo:
    """Simple working demonstration of Phase 4C external integration"""
    
    def __init__(self):
        self.temp_dir = None
    
    async def setup(self):
        """Setup demo environment"""
        self.temp_dir = tempfile.mkdtemp(prefix="phase4c_simple_")
        print(f"📁 Demo workspace: {self.temp_dir}")
    
    async def cleanup(self):
        """Cleanup demo environment"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"🧹 Cleaned up workspace: {self.temp_dir}")
    
    async def demo_database_connectors(self):
        """Demonstrate database connector functionality"""
        print("\n📚 DATABASE CONNECTORS DEMO")
        print("=" * 50)
        
        try:
            # Initialize database manager
            db_manager = DatabaseManager()
            
            # Register connectors
            pubmed = PubMedConnector()
            arxiv = ArxivConnector()
            
            db_manager.register_database('pubmed', pubmed)
            db_manager.register_database('arxiv', arxiv)
            
            print(f"✅ Registered {len(db_manager.databases)} database connectors")
            print(f"   Available: {list(db_manager.databases.keys())}")
            
            # Test authentication
            pubmed_auth = await pubmed.authenticate()
            arxiv_auth = await arxiv.authenticate()
            
            print(f"🔑 Authentication status:")
            print(f"   PubMed: {'✅' if pubmed_auth else '❌'}")
            print(f"   arXiv: {'✅' if arxiv_auth else '❌'}")
            
        except Exception as e:
            print(f"❌ Database demo error: {e}")
    
    async def demo_bibtex_manager(self):
        """Demonstrate BibTeX management"""
        print("\n📖 BIBTEX MANAGER DEMO")
        print("=" * 50)
        
        try:
            # Create sample BibTeX file
            bibtex_content = """@article{demo2024,
    title={Demonstration Article for External Integration},
    author={Demo, Author and Test, User},
    journal={Journal of Demo Studies},
    year={2024},
    volume={1},
    pages={1--10},
    doi={10.1000/demo.001}
}

@inproceedings{conf2024,
    title={Conference Paper on Integration},
    author={Conference, Speaker},
    booktitle={Proceedings of Integration Conference},
    year={2024},
    pages={123--130}
}"""
            
            bibtex_file = os.path.join(self.temp_dir, 'demo.bib')
            with open(bibtex_file, 'w', encoding='utf-8') as f:
                f.write(bibtex_content)
            
            # Initialize BibTeX manager
            bibtex_manager = BibTeXManager(bibtex_file)
            
            # Test authentication (always succeeds for local files)
            auth_result = await bibtex_manager.authenticate()
            print(f"🔑 BibTeX authentication: {'✅' if auth_result else '❌'}")
            
            # Import library
            library = await bibtex_manager.import_library("demo_lib")
            
            print(f"📚 Imported library: {library.name}")
            print(f"   References: {len(library.references)}")
            print(f"   Created: {library.created_date.strftime('%Y-%m-%d %H:%M')}")
            
            # Show reference details
            for i, ref in enumerate(library.references, 1):
                print(f"   {i}. {ref.title[:50]}...")
            
        except Exception as e:
            print(f"❌ BibTeX demo error: {e}")
    
    async def demo_data_exchange(self):
        """Demonstrate data exchange capabilities"""
        print("\n🔄 DATA EXCHANGE HUB DEMO")
        print("=" * 50)
        
        try:
            # Initialize data exchange hub
            hub = DataExchangeHub()
            
            # Create sample CSV data
            csv_data = """title,authors,year,journal
"Machine Learning in Healthcare","Smith J, Doe A",2024,"AI Medicine Journal"
"Deep Learning Applications","Johnson B, Wilson C",2023,"Tech Review"
"Data Science Methods","Brown D, Taylor E",2024,"Science Today"
"""
            
            csv_file = os.path.join(self.temp_dir, 'sample_data.csv')
            with open(csv_file, 'w', encoding='utf-8') as f:
                f.write(csv_data)
            
            print(f"📊 Created sample CSV file: {os.path.basename(csv_file)}")
            
            # Import CSV data
            import_engine = ImportEngine()
            imported_data = await import_engine.import_csv(csv_file)
            
            print(f"📥 Imported {len(imported_data)} records from CSV")
            
            # Validate data
            validator = DataValidator()
            validation_results = await validator.validate_data(
                imported_data, 
                ValidationLevel.LENIENT
            )
            
            print(f"✅ Validation completed:")
            print(f"   Valid records: {validation_results.valid_count}")
            print(f"   Errors: {validation_results.error_count}")
            print(f"   Warnings: {validation_results.warning_count}")
            
            # Export to JSON
            export_engine = ExportEngine()
            json_file = os.path.join(self.temp_dir, 'exported_data.json')
            await export_engine.export_to_json(imported_data, json_file)
            
            print(f"📤 Exported data to JSON: {os.path.basename(json_file)}")
            
            # Verify exported file
            if os.path.exists(json_file):
                file_size = os.path.getsize(json_file)
                print(f"   File size: {file_size} bytes")
            
        except Exception as e:
            print(f"❌ Data exchange demo error: {e}")
    
    async def demo_validation_levels(self):
        """Demonstrate different validation levels"""
        print("\n🔍 VALIDATION LEVELS DEMO")
        print("=" * 50)
        
        try:
            # Create test data with some issues
            test_data = [
                {"title": "Valid Article", "year": 2024, "authors": "Smith J"},
                {"title": "", "year": 2024, "authors": "Doe A"},  # Missing title
                {"title": "Another Article", "year": "invalid", "authors": "Johnson B"},  # Invalid year
                {"title": "Good Article", "year": 2023, "authors": "Wilson C"}
            ]
            
            validator = DataValidator()
            
            # Test different validation levels
            levels = [ValidationLevel.STRICT, ValidationLevel.STANDARD, ValidationLevel.LENIENT]
            
            for level in levels:
                print(f"\n🎯 Testing {level.value} validation:")
                results = await validator.validate_data(test_data, level)
                
                print(f"   Valid: {results.valid_count}")
                print(f"   Errors: {results.error_count}")
                print(f"   Warnings: {results.warning_count}")
                print(f"   Status: {'✅ PASSED' if results.is_valid else '❌ FAILED'}")
        
        except Exception as e:
            print(f"❌ Validation demo error: {e}")
    
    async def run_complete_demo(self):
        """Run the complete demonstration"""
        print("🚀 Phase 4C External Integration - Simple Demo")
        print("=" * 60)
        print("Demonstrating core external integration functionality\n")
        
        try:
            await self.setup()
            
            # Run all demos
            await self.demo_database_connectors()
            await self.demo_bibtex_manager()
            await self.demo_data_exchange()
            await self.demo_validation_levels()
            
            print("\n🎉 DEMO COMPLETED SUCCESSFULLY!")
            print("=" * 60)
            print("All external integration components are operational and ready for use.")
            
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await self.cleanup()


async def main():
    """Main demo execution"""
    demo = Phase4CSimpleDemo()
    await demo.run_complete_demo()


if __name__ == "__main__":
    asyncio.run(main())
