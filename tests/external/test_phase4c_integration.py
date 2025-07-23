"""
Phase 4C Integration Tests: External Integration Module

Comprehensive test suite for validating external integration functionality including:
- Database connectors (PubMed, arXiv, Cochrane)
- Citation managers (Zotero, BibTeX)
- Research tools (R integration, PROSPERO, GRADE Pro)
- Data import/export hub with format conversion
- End-to-end integration workflows

Author: Eunice AI System
Date: July 2025
"""

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from typing import Dict, List, Any

import pytest

# Import the external integration modules
from src.external import (
    DatabaseManager, PubMedConnector, ArxivConnector,
    ZoteroIntegration, BibTeXManager,
    RIntegration, ProsperoRegistration, GradeProIntegration,
    DataExchangeHub, DataFormat, ExchangeFormat, ValidationLevel,
    ImportResult, ExportResult
)


class TestPhase4CIntegration(unittest.IsolatedAsyncioTestCase):
    """Test suite for Phase 4C external integration functionality"""

    async def asyncSetUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp(prefix="test_phase4c_")
        
        # Sample test data
        self.sample_studies = [
            {
                'id': 'study_001',
                'title': 'AI Applications in Systematic Reviews',
                'authors': ['Smith, J.', 'Doe, A.'],
                'publication_year': 2023,
                'journal': 'Journal of Evidence-Based Medicine',
                'doi': '10.1000/jem.001',
                'abstract': 'This study examines the use of AI in systematic reviews...',
                'keywords': ['artificial intelligence', 'systematic review', 'automation']
            },
            {
                'id': 'study_002', 
                'title': 'Machine Learning for Meta-Analysis',
                'authors': ['Johnson, B.', 'Brown, C.'],
                'publication_year': 2024,
                'journal': 'AI in Healthcare Review',
                'doi': '10.1000/aihr.002',
                'abstract': 'We present novel ML approaches for meta-analysis...',
                'keywords': ['machine learning', 'meta-analysis', 'healthcare']
            }
        ]
        
        self.sample_csv = """id,title,authors,year,journal,doi
study_001,"AI Applications in Systematic Reviews","Smith J; Doe A",2023,Journal of Evidence-Based Medicine,10.1000/jem.001
study_002,"Machine Learning for Meta-Analysis","Johnson B; Brown C",2024,AI in Healthcare Review,10.1000/aihr.002"""

        self.sample_ris = """TY  - JOUR
TI  - AI Applications in Systematic Reviews
AU  - Smith, J.
AU  - Doe, A.
PY  - 2023
JO  - Journal of Evidence-Based Medicine
DO  - 10.1000/jem.001
ER  - 

TY  - JOUR
TI  - Machine Learning for Meta-Analysis
AU  - Johnson, B.
AU  - Brown, C.
PY  - 2024
JO  - AI in Healthcare Review
DO  - 10.1000/aihr.002
ER  - """

    async def asyncTearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # Database Connector Tests
    async def test_database_manager_initialization(self):
        """Test database manager initialization and configuration"""
        
        db_manager = DatabaseManager()
        
        # Test connector registration
        pubmed = PubMedConnector()
        arxiv = ArxivConnector()
        
        db_manager.register_database('pubmed', pubmed)
        db_manager.register_database('arxiv', arxiv)
        
        self.assertEqual(len(db_manager.databases), 2)
        self.assertIn('pubmed', db_manager.databases)
        self.assertIn('arxiv', db_manager.databases)

    @patch('aiohttp.ClientSession.get')
    async def test_pubmed_connector_search(self, mock_get):
        """Test PubMed connector search functionality"""
        
        # Mock PubMed API response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text.return_value = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345678</PMID>
                    <Article>
                        <ArticleTitle>Test Article Title</ArticleTitle>
                        <AuthorList>
                            <Author><LastName>Smith</LastName><ForeName>John</ForeName></Author>
                        </AuthorList>
                        <Journal>
                            <Title>Test Journal</Title>
                            <JournalIssue>
                                <PubDate><Year>2023</Year></PubDate>
                            </JournalIssue>
                        </Journal>
                        <Abstract><AbstractText>Test abstract content</AbstractText></Abstract>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>"""
        
        mock_get.return_value.__aenter__.return_value = mock_response
        
        pubmed = PubMedConnector()
        results = await pubmed.search("systematic review", max_results=10)
        
        self.assertIsNotNone(results)
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]['pmid'], '12345678')
        self.assertEqual(results[0]['title'], 'Test Article Title')

    @patch('aiohttp.ClientSession.get')
    async def test_arxiv_connector_search(self, mock_get):
        """Test arXiv connector search functionality"""
        
        # Mock arXiv API response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text.return_value = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <id>http://arxiv.org/abs/2301.00001v1</id>
                <title>Test arXiv Paper</title>
                <author><name>Jane Doe</name></author>
                <published>2023-01-01T00:00:00Z</published>
                <summary>Test abstract for arXiv paper</summary>
                <category term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
            </entry>
        </feed>"""
        
        mock_get.return_value.__aenter__.return_value = mock_response
        
        arxiv = ArxivConnector()
        results = await arxiv.search("machine learning", max_results=5)
        
        self.assertIsNotNone(results)
        self.assertGreater(len(results), 0)
        self.assertIn('2301.00001', results[0]['arxiv_id'])
        self.assertEqual(results[0]['title'], 'Test arXiv Paper')

    # Citation Manager Tests
    @patch('requests.post')
    @patch('requests.get')
    async def test_zotero_integration(self, mock_get, mock_post):
        """Test Zotero integration functionality"""
        
        # Mock Zotero API responses
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'access_token': 'test_token'}
        
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                'key': 'ITEM001',
                'data': {
                    'title': 'Test Reference',
                    'creators': [{'firstName': 'John', 'lastName': 'Smith'}],
                    'date': '2023',
                    'publicationTitle': 'Test Journal'
                }
            }
        ]
        
        zotero = ZoteroIntegration()
        
        # Test authentication
        auth_result = await zotero.authenticate('test_user', 'test_key')
        self.assertTrue(auth_result)
        
        # Test collection retrieval
        references = await zotero.get_collection_items('test_collection')
        self.assertIsNotNone(references)
        self.assertGreater(len(references), 0)

    async def test_bibtex_manager(self):
        """Test BibTeX file management functionality"""
        
        sample_bibtex = """@article{smith2023ai,
    title={AI Applications in Systematic Reviews},
    author={Smith, John and Doe, Alice},
    journal={Journal of Evidence-Based Medicine},
    year={2023},
    doi={10.1000/jem.001}
}

@article{johnson2024ml,
    title={Machine Learning for Meta-Analysis},
    author={Johnson, Bob and Brown, Carol},
    journal={AI in Healthcare Review},
    year={2024},
    doi={10.1000/aihr.002}
}"""
        
        # Create temporary BibTeX file
        bibtex_file = os.path.join(self.temp_dir, 'test.bib')
        with open(bibtex_file, 'w') as f:
            f.write(sample_bibtex)
        
        bibtex_manager = BibTeXManager()
        references = await bibtex_manager.parse_file(bibtex_file)
        
        self.assertEqual(len(references), 2)
        self.assertEqual(references[0]['title'], 'AI Applications in Systematic Reviews')
        self.assertEqual(references[1]['year'], '2024')

    # Research Tools Tests
    @patch('subprocess.run')
    async def test_r_integration(self, mock_subprocess):
        """Test R statistical software integration"""
        
        # Mock R subprocess execution
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = """
        [1] "Meta-analysis results:"
        [1] "Effect size: 0.75 (95% CI: 0.45, 1.05)"
        [1] "Heterogeneity: I2 = 45%"
        """
        
        r_integration = RIntegration()
        
        # Test R availability check
        is_available = await r_integration.check_availability()
        # Should be mocked as available
        self.assertTrue(is_available)
        
        # Test meta-analysis script generation
        study_data = [
            {'effect_size': 0.8, 'se': 0.2, 'study_id': 'study1'},
            {'effect_size': 0.7, 'se': 0.15, 'study_id': 'study2'}
        ]
        
        script = await r_integration.generate_meta_analysis_script(study_data)
        self.assertIn('metafor', script)
        self.assertIn('rma', script)

    async def test_prospero_registration(self):
        """Test PROSPERO protocol registration framework"""
        
        prospero = ProsperoRegistration()
        
        protocol_data = {
            'title': 'AI in Systematic Reviews: A Comprehensive Analysis',
            'authors': ['Smith, J.', 'Doe, A.'],
            'review_question': 'What is the effectiveness of AI tools in systematic reviews?',
            'search_strategy': 'Comprehensive search of multiple databases',
            'inclusion_criteria': ['RCTs', 'Systematic reviews', 'Published 2020-2024'],
            'exclusion_criteria': ['Conference abstracts', 'Non-English'],
            'outcomes': ['Primary: Review efficiency', 'Secondary: Quality measures']
        }
        
        registration_form = await prospero.prepare_registration(protocol_data)
        
        self.assertIn('title', registration_form)
        self.assertIn('review_question', registration_form)
        self.assertEqual(registration_form['title'], protocol_data['title'])

    async def test_grade_pro_integration(self):
        """Test GRADE Pro evidence assessment integration"""
        
        grade_pro = GradeProIntegration()
        
        evidence_data = {
            'outcome': 'Treatment effectiveness',
            'study_design': 'RCT',
            'risk_of_bias': 'low',
            'inconsistency': 'moderate',
            'indirectness': 'low',
            'imprecision': 'low',
            'publication_bias': 'low'
        }
        
        assessment = await grade_pro.assess_quality(evidence_data)
        
        self.assertIn('overall_quality', assessment)
        self.assertIn('rationale', assessment)
        self.assertIn(assessment['overall_quality'], ['very_low', 'low', 'moderate', 'high'])

    # Data Exchange Hub Tests
    async def test_data_hub_csv_import(self):
        """Test CSV data import functionality"""
        
        hub = DataExchangeHub(ValidationLevel.MODERATE)
        
        import_result = await hub.import_engine.import_data(
            self.sample_csv,
            DataFormat.CSV,
            ExchangeFormat.STUDY_METADATA
        )
        
        self.assertTrue(import_result.success)
        self.assertEqual(import_result.records_imported, 2)
        self.assertIn('studies', import_result.imported_data)
        self.assertEqual(len(import_result.imported_data['studies']), 2)

    async def test_data_hub_ris_import(self):
        """Test RIS format import functionality"""
        
        hub = DataExchangeHub(ValidationLevel.MODERATE)
        
        import_result = await hub.import_engine.import_data(
            self.sample_ris,
            DataFormat.RIS,
            ExchangeFormat.REFERENCE_LIBRARY
        )
        
        self.assertTrue(import_result.success)
        self.assertEqual(import_result.records_imported, 2)
        self.assertIn('references', import_result.imported_data)

    async def test_data_hub_json_export(self):
        """Test JSON data export functionality"""
        
        hub = DataExchangeHub()
        
        data = {'studies': self.sample_studies}
        
        export_result = await hub.export_engine.export_data(
            data,
            DataFormat.JSON
        )
        
        self.assertTrue(export_result.success)
        self.assertEqual(export_result.records_exported, 2)
        self.assertIsNotNone(export_result.output_data)
        
        # Validate JSON structure
        exported_json = json.loads(export_result.output_data)
        self.assertIn('studies', exported_json)
        self.assertEqual(len(exported_json['studies']), 2)

    async def test_data_hub_format_conversion(self):
        """Test format conversion functionality"""
        
        hub = DataExchangeHub()
        
        # Convert CSV to RIS
        ris_output = await hub.convert_format(
            self.sample_csv,
            DataFormat.CSV,
            DataFormat.RIS
        )
        
        self.assertIsNotNone(ris_output)
        self.assertIn('TY  - JOUR', ris_output)
        self.assertIn('ER  - ', ris_output)

    async def test_data_validation_levels(self):
        """Test different validation strictness levels"""
        
        # Create data with validation issues
        problematic_csv = """id,title,authors,year
study1,,Smith J,invalid_year
study2,Good Title,Doe A,2023"""
        
        # Strict validation
        hub_strict = DataExchangeHub(ValidationLevel.STRICT)
        strict_result = await hub_strict.import_engine.import_data(
            problematic_csv,
            DataFormat.CSV,
            ExchangeFormat.STUDY_METADATA
        )
        
        self.assertFalse(strict_result.success)
        self.assertGreater(strict_result.validation_result.error_count, 0)
        
        # Lenient validation
        hub_lenient = DataExchangeHub(ValidationLevel.LENIENT)
        lenient_result = await hub_lenient.import_engine.import_data(
            problematic_csv,
            DataFormat.CSV,
            ExchangeFormat.STUDY_METADATA
        )
        
        # Should have fewer errors with lenient validation
        self.assertLessEqual(
            lenient_result.validation_result.error_count,
            strict_result.validation_result.error_count
        )

    # End-to-End Integration Tests
    async def test_end_to_end_workflow(self):
        """Test complete external integration workflow"""
        
        # 1. Initialize all components
        db_manager = DatabaseManager()
        pubmed = PubMedConnector()
        db_manager.register_database('pubmed', pubmed)
        
        zotero = ZoteroIntegration()
        bibtex_manager = BibTeXManager()
        
        r_integration = RIntegration()
        prospero = ProsperoRegistration()
        
        hub = DataExchangeHub()
        
        # 2. Mock external API calls
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.text.return_value = """<?xml version="1.0"?>
            <PubmedArticleSet>
                <PubmedArticle>
                    <MedlineCitation>
                        <PMID>12345678</PMID>
                        <Article>
                            <ArticleTitle>AI in Systematic Reviews</ArticleTitle>
                            <AuthorList>
                                <Author><LastName>Smith</LastName><ForeName>John</ForeName></Author>
                            </AuthorList>
                            <Journal><Title>Test Journal</Title></Journal>
                        </Article>
                    </MedlineCitation>
                </PubmedArticle>
            </PubmedArticleSet>"""
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # 3. Simulate search and data collection
            search_results = await pubmed.search("systematic review AI", max_results=5)
            self.assertIsNotNone(search_results)
            
            # 4. Import data through hub
            import_result = await hub.import_engine.import_data(
                self.sample_csv,
                DataFormat.CSV,
                ExchangeFormat.STUDY_METADATA
            )
            self.assertTrue(import_result.success)
            
            # 5. Export in different formats
            json_export = await hub.export_engine.export_data(
                import_result.imported_data,
                DataFormat.JSON
            )
            self.assertTrue(json_export.success)
            
            ris_export = await hub.export_engine.export_data(
                import_result.imported_data,
                DataFormat.RIS
            )
            self.assertTrue(ris_export.success)
        
        # 6. Generate PROSPERO registration
        protocol_data = {
            'title': 'AI in Systematic Reviews: A Comprehensive Analysis',
            'authors': ['Smith, J.'],
            'review_question': 'Effectiveness of AI tools in systematic reviews?'
        }
        
        registration_form = await prospero.prepare_registration(protocol_data)
        self.assertIn('title', registration_form)

    async def test_error_handling_and_recovery(self):
        """Test error handling and graceful degradation"""
        
        # Test database connection errors
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            pubmed = PubMedConnector()
            results = await pubmed.search("test query", max_results=5)
            # Should return empty list on error
            self.assertEqual(len(results), 0)
        
        # Test invalid data import
        hub = DataExchangeHub()
        invalid_csv = "invalid,csv,data\nwith,incomplete"
        
        import_result = await hub.import_engine.import_data(
            invalid_csv,
            DataFormat.CSV,
            ExchangeFormat.STUDY_METADATA
        )
        
        # Should handle gracefully
        self.assertIsNotNone(import_result)
        self.assertIsInstance(import_result.error_log, list)

    async def test_performance_with_large_datasets(self):
        """Test performance with larger datasets"""
        
        # Generate larger test dataset
        large_csv_rows = ["id,title,authors,year,journal"]
        for i in range(100):
            large_csv_rows.append(f"study_{i:03d},Title {i},Author {i},{2020+i%5},Journal {i%10}")
        
        large_csv = "\n".join(large_csv_rows)
        
        hub = DataExchangeHub()
        
        start_time = datetime.now()
        import_result = await hub.import_engine.import_data(
            large_csv,
            DataFormat.CSV,
            ExchangeFormat.STUDY_METADATA
        )
        processing_time = (datetime.now() - start_time).total_seconds()
        
        self.assertTrue(import_result.success)
        self.assertEqual(import_result.records_imported, 100)
        self.assertLess(processing_time, 10.0)  # Should complete within 10 seconds

    async def test_concurrent_operations(self):
        """Test concurrent external operations"""
        
        hub = DataExchangeHub()
        
        # Create multiple import tasks
        tasks = []
        for i in range(3):
            task = hub.import_engine.import_data(
                self.sample_csv,
                DataFormat.CSV,
                ExchangeFormat.STUDY_METADATA
            )
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        for result in results:
            self.assertTrue(result.success)
            self.assertEqual(result.records_imported, 2)


# Integration test runner
if __name__ == '__main__':
    async def run_phase4c_tests():
        """Run Phase 4C integration tests"""
        
        print("🧪 Running Phase 4C External Integration Tests...")
        print("=" * 60)
        
        # Create test suite
        suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase4CIntegration)
        
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
        
        success = len(result.failures) == 0 and len(result.errors) == 0
        
        if success:
            print("\n✅ All Phase 4C integration tests passed!")
            print("🎉 External integration module is ready for production use.")
        else:
            print("\n❌ Some tests failed. Please review and fix issues.")
        
        return success
    
    # Run the tests
    asyncio.run(run_phase4c_tests())
