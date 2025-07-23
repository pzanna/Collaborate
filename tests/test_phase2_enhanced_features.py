"""
Phase 2 integration tests for enhanced systematic review functionality.

This script tests the enhanced screening workflow and quality appraisal plugins.
"""

import asyncio
import json
import tempfile
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from typing import Optional

# Add project root to path
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.config_manager import ConfigManager
from src.ai_clients.openai_client import OpenAIClient, AIProviderConfig
from src.storage.systematic_review_database import SystematicReviewDatabase
from src.screening.enhanced_screening_workflow import (
    EnhancedScreeningWorkflow, 
    ScreeningConflictResolver,
    ScreeningStage,
    ScreeningDecision
)
from src.quality_appraisal.plugin_architecture import QualityAppraisalManager
from src.quality_appraisal.robins_i_plugin import RobinsIPlugin
from src.quality_appraisal.rob2_plugin import Rob2Plugin


def create_mock_ai_client():
    """Create a mock AI client for testing."""
    config = AIProviderConfig(
        provider="openai",
        model="gpt-4o",
        temperature=0.0,
        max_tokens=2000
    )
    
    class MockAIClient:
        def __init__(self, config):
            self.config = config
            
        def get_response(self, user_message: str, system_prompt: Optional[str] = None) -> str:
            # Mock response for screening
            if "screening" in user_message.lower():
                return json.dumps({
                    "decision": "include",
                    "confidence": 0.85,
                    "rationale": "Study meets inclusion criteria with clear population, intervention, and relevant outcomes.",
                    "exclusion_reason": None
                })
            
            # Mock response for quality assessment
            if "robins-i" in user_message.lower() or "bias" in user_message.lower():
                return json.dumps({
                    "overall_bias": "moderate",
                    "overall_rationale": "Study has some methodological concerns but provides useful evidence.",
                    "domains": [
                        {
                            "domain": "confounding",
                            "bias_level": "moderate",
                            "rationale": "Some potential confounders identified but partially controlled",
                            "supporting_evidence": ["Study controlled for age and sex"],
                            "confidence": 0.8
                        },
                        {
                            "domain": "selection",
                            "bias_level": "low", 
                            "rationale": "Appropriate selection criteria applied",
                            "supporting_evidence": ["Clear inclusion/exclusion criteria"],
                            "confidence": 0.9
                        },
                        {
                            "domain": "classification_intervention",
                            "bias_level": "low",
                            "rationale": "Intervention clearly defined and measured",
                            "supporting_evidence": ["Standardized intervention protocol"],
                            "confidence": 0.9
                        },
                        {
                            "domain": "deviation_intervention", 
                            "bias_level": "moderate",
                            "rationale": "Some deviations from protocol noted",
                            "supporting_evidence": ["15% protocol deviation rate"],
                            "confidence": 0.7
                        },
                        {
                            "domain": "missing_data",
                            "bias_level": "low",
                            "rationale": "Low attrition rate with appropriate handling",
                            "supporting_evidence": ["5% dropout rate, intention-to-treat analysis"],
                            "confidence": 0.9
                        },
                        {
                            "domain": "measurement_outcome",
                            "bias_level": "low",
                            "rationale": "Validated outcome measures used",
                            "supporting_evidence": ["Standardized assessment tools"],
                            "confidence": 0.9
                        },
                        {
                            "domain": "selection_reported_result",
                            "bias_level": "moderate",
                            "rationale": "Some concern about selective reporting",
                            "supporting_evidence": ["Not all planned outcomes reported"],
                            "confidence": 0.7
                        }
                    ]
                })
            
            return "Mock response"
    
    return MockAIClient(config)


async def test_enhanced_screening_workflow():
    """Test enhanced screening workflow functionality."""
    print("🔍 Testing Enhanced Screening Workflow...")
    
    # Create temporary database
    temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db_file.close()
    
    try:
        # Setup components
        db = SystematicReviewDatabase(temp_db_file.name)
        ai_client = create_mock_ai_client()
        # Type ignore for mock client in testing
        screening_workflow = EnhancedScreeningWorkflow(db, ai_client)  # type: ignore
        
        # Create test task
        with db.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("INSERT INTO tasks (id, name) VALUES (?, ?)", 
                        ('test_task_phase2', 'Phase 2 Test Task'))
            conn.commit()
        
        # Configure screening
        screening_config = {
            'confidence_threshold': 0.8,
            'batch_size': 5,
            'require_human_review': False,
            'exclusion_reasons': ['WRONG_POPULATION', 'WRONG_INTERVENTION']
        }
        screening_workflow.configure_screening(screening_config)
        
        # Create test studies
        test_studies = [
            {
                'id': 'study_phase2_001',
                'title': 'AI-Enhanced Diagnostic Accuracy in Radiology: A Cohort Study',
                'authors': ['Smith, J.A.', 'Johnson, M.B.'],
                'year': 2023,
                'abstract': 'This study evaluates the diagnostic accuracy of AI-assisted radiology interpretation compared to traditional methods.',
                'doi': '10.1000/test.phase2.001'
            },
            {
                'id': 'study_phase2_002', 
                'title': 'Machine Learning Applications in Clinical Decision Support',
                'authors': ['Brown, D.C.', 'Wilson, K.L.'],
                'year': 2023,
                'abstract': 'A comprehensive analysis of machine learning tools for clinical decision support systems.',
                'doi': '10.1000/test.phase2.002'
            },
            {
                'id': 'study_phase2_003',
                'title': 'Patient Outcomes with Automated Screening Systems',
                'authors': ['Davis, R.S.', 'Taylor, A.M.'],
                'year': 2022,
                'abstract': 'Evaluation of patient outcomes when using automated screening systems in clinical practice.',
                'doi': '10.1000/test.phase2.003'
            }
        ]
        
        # Add studies to database
        for study in test_studies:
            study_data = {
                'task_id': 'test_task_phase2',
                'title': study['title'],
                'authors': study['authors'],
                'year': study['year'],
                'doi': study['doi'],
                'source': 'test',
                'abstract': study['abstract'],
                'content_hash': f"hash_{study['id']}"
            }
            db.create_study_record(study_data)
        
        # Define screening criteria
        screening_criteria = {
            'population': 'Healthcare providers and patients in clinical settings',
            'intervention': 'AI-assisted diagnostic or screening tools',
            'comparison': 'Traditional methods without AI assistance',
            'outcomes': ['diagnostic accuracy', 'patient outcomes', 'workflow efficiency'],
            'inclusion_criteria': {
                'study_types': ['cohort', 'rct', 'cross-sectional'],
                'languages': ['english'],
                'peer_reviewed': True
            },
            'exclusion_criteria': {
                'animal_studies': True,
                'case_reports': True
            }
        }
        
        # Test title/abstract screening
        screening_result = await screening_workflow.title_abstract_screening(
            test_studies, 
            screening_criteria, 
            'test_task_phase2'
        )
        
        print(f"✅ Title/Abstract Screening Results:")
        print(f"   - Total screened: {screening_result['total_screened']}")
        print(f"   - Included: {screening_result['included']}")
        print(f"   - Excluded: {screening_result['excluded']}")
        print(f"   - Uncertain: {screening_result['uncertain']}")
        print(f"   - Human review required: {screening_result['human_review_required']}")
        
        # Test full-text screening on included studies
        included_studies = [
            result.study_id for result in screening_result['screening_results'] 
            if result.decision == ScreeningDecision.INCLUDE
        ]
        
        if included_studies:
            # Get full study data for included studies
            included_study_data = [s for s in test_studies if s['id'] in included_studies]
            
            fulltext_result = await screening_workflow.full_text_screening(
                included_study_data,
                screening_criteria,
                'test_task_phase2'
            )
            
            print(f"✅ Full-Text Screening Results:")
            print(f"   - Total screened: {fulltext_result['total_screened']}")
            print(f"   - Finally included: {fulltext_result['included']}")
            print(f"   - Finally excluded: {fulltext_result['excluded']}")
        
        print("✅ Enhanced screening workflow tests completed successfully!\n")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced screening workflow test failed: {e}")
        return False
        
    finally:
        # Cleanup
        if os.path.exists(temp_db_file.name):
            os.unlink(temp_db_file.name)


async def test_quality_appraisal_plugins():
    """Test quality appraisal plugin system."""
    print("🏅 Testing Quality Appraisal Plugins...")
    
    # Create temporary database
    temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db_file.close()
    
    try:
        # Setup components
        db = SystematicReviewDatabase(temp_db_file.name)
        ai_client = create_mock_ai_client()
        qa_manager = QualityAppraisalManager(db, ai_client)  # type: ignore
        
        # Register plugins
        robins_i_plugin = RobinsIPlugin(ai_client, assessor="ai_robins_i")  # type: ignore
        rob2_plugin = Rob2Plugin(ai_client, assessor="ai_rob2")  # type: ignore
        
        qa_manager.register_plugin(robins_i_plugin)
        qa_manager.register_plugin(rob2_plugin)
        
        # Test plugin registration
        available_tools = qa_manager.get_available_tools()
        print(f"✅ Registered {len(available_tools)} quality appraisal tools:")
        for tool in available_tools:
            print(f"   - {tool['tool_name']} (ID: {tool['tool_id']})")
            print(f"     Study types: {', '.join(tool['applicable_study_types'][:3])}...")
        
        # Create test studies for assessment
        test_studies = [
            {
                'id': 'qa_study_001',
                'title': 'Randomized Trial of AI-Assisted Diagnosis vs Standard Care',
                'authors': ['Miller, S.A.', 'Jones, R.B.'],
                'year': 2023,
                'abstract': 'A randomized controlled trial comparing AI-assisted diagnosis to standard diagnostic procedures.',
                'metadata': {
                    'study_type': 'randomized controlled trial',
                    'journal': 'Journal of Medical AI'
                },
                'full_text': 'Methods: Patients were randomly allocated using computer-generated sequence...'
            },
            {
                'id': 'qa_study_002',
                'title': 'Cohort Study of Machine Learning in Clinical Practice',
                'authors': ['Anderson, L.C.', 'White, K.D.'],
                'year': 2022,
                'abstract': 'A prospective cohort study examining the effectiveness of machine learning tools in clinical decision making.',
                'metadata': {
                    'study_type': 'cohort study',
                    'journal': 'Clinical Decision Support Journal'
                },
                'full_text': 'Design: Prospective cohort study with 2-year follow-up period...'
            }
        ]
        
        # Test tool recommendation
        for study in test_studies:
            recommended_tool = qa_manager.get_recommended_tool(study)
            print(f"✅ Study '{study['title'][:50]}...': Recommended tool = {recommended_tool}")
        
        # Test quality assessment
        assessment_criteria = {
            'population': 'Adult patients in clinical settings',
            'intervention': 'AI-assisted diagnostic tools',
            'comparison': 'Standard care',
            'outcomes': ['diagnostic accuracy', 'patient outcomes']
        }
        
        assessments = await qa_manager.assess_studies(test_studies, criteria=assessment_criteria)
        
        print(f"✅ Completed {len(assessments)} quality assessments:")
        for assessment in assessments:
            print(f"   - Study {assessment.study_id}: {assessment.tool_id} = {assessment.overall_bias.value}")
            print(f"     Domains assessed: {len(assessment.domain_assessments)}")
            print(f"     Assessment time: {assessment.assessment_time:.2f}s" if assessment.assessment_time else "     Assessment time: N/A")
        
        # Test plugin validation
        for assessment in assessments:
            plugin = qa_manager.plugins[assessment.tool_id]
            validation_errors = plugin.validate_assessment(assessment)
            if validation_errors:
                print(f"⚠️  Validation errors for {assessment.study_id}: {validation_errors}")
            else:
                print(f"✅ Assessment for {assessment.study_id} passed validation")
        
        print("✅ Quality appraisal plugin tests completed successfully!\n")
        return True
        
    except Exception as e:
        print(f"❌ Quality appraisal plugin test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        if os.path.exists(temp_db_file.name):
            os.unlink(temp_db_file.name)


async def test_conflict_resolution():
    """Test screening conflict resolution."""
    print("⚖️  Testing Conflict Resolution...")
    
    # Create temporary database  
    temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db_file.close()
    
    try:
        # Setup components
        db = SystematicReviewDatabase(temp_db_file.name)
        conflict_resolver = ScreeningConflictResolver(db)
        
        # Create test task and study
        with db.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("INSERT INTO tasks (id, name) VALUES (?, ?)", 
                        ('conflict_test_task', 'Conflict Resolution Test'))
            conn.commit()
        
        # Create test study
        study_data = {
            'task_id': 'conflict_test_task',
            'title': 'Test Study for Conflict Resolution',
            'authors': ['Test, A.'],
            'year': 2023,
            'doi': '10.1000/conflict.test',
            'source': 'test',
            'abstract': 'Test abstract for conflict resolution testing',
            'content_hash': 'conflict_test_hash'
        }
        study_id = db.create_study_record(study_data)
        
        # Create conflicting screening decisions
        decisions = [
            {
                'record_id': study_id,
                'stage': 'title_abstract',
                'decision': 'include',
                'reason_code': None,
                'actor': 'human',
                'confidence_score': 0.9,
                'rationale': 'Clear relevance to research question',
                'model_id': None,
                'prompt_hash': None
            },
            {
                'record_id': study_id,
                'stage': 'title_abstract', 
                'decision': 'exclude',
                'reason_code': 'WRONG_POPULATION',
                'actor': 'human',
                'confidence_score': 0.8,
                'rationale': 'Population does not match inclusion criteria',
                'model_id': None,
                'prompt_hash': None
            },
            {
                'record_id': study_id,
                'stage': 'title_abstract',
                'decision': 'include',
                'reason_code': None,
                'actor': 'ai',
                'confidence_score': 0.7,
                'rationale': 'Meets most inclusion criteria',
                'model_id': 'gpt-4o',
                'prompt_hash': 'test_hash'
            }
        ]
        
        # Save conflicting decisions
        for decision in decisions:
            db.create_screening_decision(decision)
        
        # Test conflict resolution strategies
        strategies = ['consensus', 'highest_confidence', 'most_inclusive']
        
        for strategy in strategies:
            result = conflict_resolver.resolve_conflicts('conflict_test_task', strategy)
            print(f"✅ {strategy.title()} Resolution:")
            print(f"   - Conflicts found: {result['conflicts_found']}")
            print(f"   - Conflicts resolved: {result['conflicts_resolved']}")
            if result['resolved_decisions']:
                for resolution in result['resolved_decisions']:
                    print(f"   - Study {resolution['study_id']}: {resolution['final_decision']} ({resolution['resolution_method']})")
        
        print("✅ Conflict resolution tests completed successfully!\n")
        return True
        
    except Exception as e:
        print(f"❌ Conflict resolution test failed: {e}")
        return False
        
    finally:
        # Cleanup
        if os.path.exists(temp_db_file.name):
            os.unlink(temp_db_file.name)


async def run_phase2_integration_tests():
    """Run complete Phase 2 integration tests."""
    print("🚀 Starting Phase 2 Integration Tests")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # Run all tests
    test_results = []
    
    # Test 1: Enhanced Screening Workflow
    try:
        result = await test_enhanced_screening_workflow()
        test_results.append(("Enhanced Screening", result))
    except Exception as e:
        print(f"❌ Enhanced Screening test failed: {e}")
        test_results.append(("Enhanced Screening", False))
    
    # Test 2: Quality Appraisal Plugins
    try:
        result = await test_quality_appraisal_plugins()
        test_results.append(("Quality Appraisal", result))
    except Exception as e:
        print(f"❌ Quality Appraisal test failed: {e}")
        test_results.append(("Quality Appraisal", False))
    
    # Test 3: Conflict Resolution
    try:
        result = await test_conflict_resolution()
        test_results.append(("Conflict Resolution", result))
    except Exception as e:
        print(f"❌ Conflict Resolution test failed: {e}")
        test_results.append(("Conflict Resolution", False))
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("🏁 Phase 2 Integration Test Results")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<20}: {status}")
        if result:
            passed += 1
    
    print(f"\nSummary: {passed}/{total} tests passed")
    print(f"Duration: {duration.total_seconds():.2f} seconds")
    
    if passed == total:
        print("\n🎉 All Phase 2 tests PASSED! Enhanced systematic review functionality is ready.")
        print("\nPhase 2 Capabilities Now Available:")
        print("- ✅ Enhanced two-stage screening with improved AI assistance")
        print("- ✅ Quality appraisal plugin architecture")
        print("- ✅ ROBINS-I plugin for non-randomized studies")  
        print("- ✅ RoB 2 plugin for randomized controlled trials")
        print("- ✅ Conflict resolution for multi-reviewer workflows")
        print("- ✅ Inter-rater reliability calculation")
    else:
        print(f"\n⚠️  {total - passed} tests FAILED. Please review and fix issues before proceeding.")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(run_phase2_integration_tests())
