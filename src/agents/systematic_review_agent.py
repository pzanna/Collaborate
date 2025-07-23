"""
Systematic Review Agent for PRISMA-compliant literature reviews.

This agent specializes in conducting systematic literature reviews following
PRISMA 2020 guidelines, with support for screening, quality appraisal,
and evidence synthesis.
"""

import asyncio
import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .base_agent import BaseAgent, AgentStatus
from .literature_agent import LiteratureAgent
from ..mcp.protocols import ResearchAction
from ..config.config_manager import ConfigManager
from ..utils.error_handler import handle_errors
from ..utils.id_utils import generate_timestamped_id


class PRISMAStage(Enum):
    """PRISMA workflow stages."""
    INPUT_VALIDATION = "input_validation"
    QUERY_GENERATION = "query_generation"
    RETRIEVAL = "retrieval"
    DEDUPLICATION = "deduplication"
    TITLE_ABSTRACT_SCREENING = "title_abstract_screening"
    FULL_TEXT_SCREENING = "full_text_screening"
    QUALITY_APPRAISAL = "quality_appraisal"
    SYNTHESIS = "synthesis"
    REPORT_GENERATION = "report_generation"
    COMPLETE = "complete"


class ScreeningDecision(Enum):
    """Screening decision types."""
    INCLUDE = "include"
    EXCLUDE = "exclude"
    UNCERTAIN = "uncertain"


@dataclass
class StudyRecord:
    """Individual study record."""
    id: str
    title: str
    authors: List[str]
    year: Optional[int]
    doi: Optional[str]
    source: str
    abstract: Optional[str]
    full_text_path: Optional[str]
    content_hash: str
    license_info: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime


@dataclass
class ScreeningResult:
    """Result of screening process."""
    record_id: str
    stage: str  # 'title_abstract' or 'full_text'
    decision: ScreeningDecision
    reason_code: Optional[str]
    actor: str  # 'human' or 'ai'
    confidence_score: Optional[float]
    rationale: Optional[str]
    timestamp: datetime


@dataclass
class PRISMALog:
    """PRISMA flow diagram counters."""
    identified: int = 0
    duplicates_removed: int = 0
    screened_title_abstract: int = 0
    excluded_title_abstract: int = 0
    screened_full_text: int = 0
    excluded_full_text: int = 0
    included: int = 0
    exclusion_reasons: Optional[List[Dict[str, Any]]] = None
    
    def __post_init__(self):
        if self.exclusion_reasons is None:
            self.exclusion_reasons = []


class SystematicReviewAgent(BaseAgent):
    """
    Systematic Review Agent for PRISMA-compliant literature reviews.
    
    This agent orchestrates the complete systematic review workflow:
    1. Research plan validation
    2. Search strategy development
    3. Multi-source retrieval
    4. Deduplication and clustering
    5. Two-stage screening
    6. Quality/bias appraisal
    7. Evidence synthesis
    8. PRISMA report generation
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the Systematic Review Agent.
        
        Args:
            config_manager: Configuration manager instance
        """
        super().__init__("systematic_review", config_manager)
        
        # Initialize literature agent for retrieval
        self.literature_agent = LiteratureAgent(config_manager)
        
        # Systematic review configuration
        self.review_config = {}
        if hasattr(self.config, 'config'):
            config_dict = self.config.config.__dict__ if hasattr(self.config.config, '__dict__') else {}
            self.review_config = config_dict.get('systematic_review', {})
        self.screening_config = self.review_config.get('screening', {})
        self.confidence_threshold = self.screening_config.get('confidence_threshold', 0.7)
        self.require_human_review = self.screening_config.get('require_human_review', True)
        
        # Exclusion reason vocabulary
        self.exclusion_reasons = {
            'WRONG_POPULATION': 'Wrong population/participants',
            'WRONG_INTERVENTION': 'Wrong intervention',
            'WRONG_COMPARATOR': 'Wrong comparator',
            'WRONG_OUTCOME': 'Wrong outcome measures',
            'WRONG_STUDY_DESIGN': 'Wrong study design',
            'NOT_PEER_REVIEWED': 'Not peer reviewed',
            'LANGUAGE_RESTRICTION': 'Language restriction',
            'INSUFFICIENT_DATA': 'Insufficient data',
            'DUPLICATE': 'Duplicate study',
            'FULL_TEXT_UNAVAILABLE': 'Full text unavailable'
        }
        
        self.logger.info("SystematicReviewAgent initialized")
    
    def _get_capabilities(self) -> List[str]:
        """Get systematic review agent capabilities."""
        return [
            'systematic_review_workflow',
            'validate_research_plan',
            'execute_search_strategy',
            'deduplicate_and_cluster',
            'title_abstract_screening',
            'full_text_screening',
            'quality_appraisal',
            'evidence_synthesis',
            'generate_prisma_report'
        ]
    
    async def _initialize_agent(self) -> None:
        """Initialize systematic review agent resources."""
        # Initialize literature agent
        await self.literature_agent.initialize()
        self.logger.info("Systematic Review Agent initialized")
    
    async def _cleanup_agent(self) -> None:
        """Clean up systematic review agent resources."""
        if self.literature_agent:
            if hasattr(self.literature_agent, 'cleanup'):
                await self.literature_agent.cleanup()
            elif hasattr(self.literature_agent, '_cleanup_agent'):
                await self.literature_agent._cleanup_agent()
        self.logger.info("Systematic Review Agent cleanup completed")
    
    async def _process_task_impl(self, task: ResearchAction) -> Dict[str, Any]:
        """
        Process systematic review tasks.
        
        Args:
            task: Research action to process
            
        Returns:
            Dict containing task results
        """
        action = task.action
        payload = task.payload
        
        if action == 'systematic_review_workflow':
            return await self.systematic_review_workflow(
                payload.get('research_plan', {}),
                payload.get('task_id', task.task_id),
                payload.get('user_id', 'unknown')
            )
        elif action == 'validate_research_plan':
            return await self._validate_research_plan(payload.get('research_plan', {}))
        elif action == 'execute_search_strategy':
            return await self._execute_search_strategy(payload.get('research_plan', {}))
        elif action == 'deduplicate_and_cluster':
            return await self._deduplicate_and_cluster(payload.get('search_results', []))
        elif action == 'title_abstract_screening':
            return await self._title_abstract_screening(
                payload.get('studies', []),
                payload.get('criteria', {})
            )
        elif action == 'full_text_screening':
            return await self._full_text_screening(
                payload.get('studies', []),
                payload.get('criteria', {})
            )
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def systematic_review_workflow(self, research_plan: Dict[str, Any], 
                                       task_id: str, user_id: str) -> Dict[str, Any]:
        """
        Execute complete systematic review workflow following PRISMA guidelines.
        
        Args:
            research_plan: Research plan with PICO/PECO criteria
            task_id: Task identifier
            user_id: User identifier
            
        Returns:
            Dict containing complete systematic review results
        """
        self.logger.info(f"Starting systematic review workflow for task {task_id}")
        
        workflow_results = {
            'task_id': task_id,
            'user_id': user_id,
            'started_at': datetime.now().isoformat(),
            'current_stage': PRISMAStage.INPUT_VALIDATION.value,
            'prisma_log': PRISMALog(),
            'results': {}
        }
        
        try:
            
            # Stage 1: Input validation (FR-1)
            self.logger.info("Stage 1: Validating research plan")
            validation_result = await self._validate_research_plan(research_plan)
            workflow_results['results']['validation'] = validation_result
            workflow_results['current_stage'] = PRISMAStage.QUERY_GENERATION.value
            
            if not validation_result['valid']:
                workflow_results['status'] = 'failed'
                workflow_results['error'] = 'Research plan validation failed'
                return workflow_results
            
            # Stage 2: Search strategy execution (FR-2)
            self.logger.info("Stage 2: Executing search strategy")
            search_results = await self._execute_search_strategy(validation_result['validated_plan'])
            workflow_results['results']['search'] = search_results
            workflow_results['prisma_log'].identified = len(search_results.get('all_results', []))
            workflow_results['current_stage'] = PRISMAStage.DEDUPLICATION.value
            
            # Stage 3: Deduplication and clustering (FR-2.6, FR-2.7)
            self.logger.info("Stage 3: Deduplication and clustering")
            dedup_results = await self._deduplicate_and_cluster(search_results.get('all_results', []))
            workflow_results['results']['deduplication'] = dedup_results
            workflow_results['prisma_log'].duplicates_removed = dedup_results.get('duplicates_removed', 0)
            workflow_results['current_stage'] = PRISMAStage.TITLE_ABSTRACT_SCREENING.value
            
            # Stage 4: Title/Abstract screening (FR-3)
            self.logger.info("Stage 4: Title/Abstract screening")
            screening_criteria = validation_result['validated_plan'].get('inclusion_criteria', {})
            ta_screening_results = await self._title_abstract_screening(
                dedup_results.get('unique_studies', []),
                screening_criteria
            )
            workflow_results['results']['title_abstract_screening'] = ta_screening_results
            workflow_results['prisma_log'].screened_title_abstract = len(dedup_results.get('unique_studies', []))
            workflow_results['prisma_log'].excluded_title_abstract = ta_screening_results.get('excluded_count', 0)
            workflow_results['current_stage'] = PRISMAStage.FULL_TEXT_SCREENING.value
            
            # Stage 5: Full text screening (FR-3)
            self.logger.info("Stage 5: Full text screening")
            included_studies = ta_screening_results.get('included_studies', [])
            ft_screening_results = await self._full_text_screening(included_studies, screening_criteria)
            workflow_results['results']['full_text_screening'] = ft_screening_results
            workflow_results['prisma_log'].screened_full_text = len(included_studies)
            workflow_results['prisma_log'].excluded_full_text = ft_screening_results.get('excluded_count', 0)
            workflow_results['prisma_log'].included = ft_screening_results.get('included_count', 0)
            workflow_results['current_stage'] = PRISMAStage.COMPLETE.value
            
            # Collect exclusion reasons
            ta_reasons = ta_screening_results.get('exclusion_reasons', [])
            ft_reasons = ft_screening_results.get('exclusion_reasons', [])
            workflow_results['prisma_log'].exclusion_reasons = ta_reasons + ft_reasons
            
            workflow_results['status'] = 'completed'
            workflow_results['completed_at'] = datetime.now().isoformat()
            
            self.logger.info(f"Systematic review workflow completed for task {task_id}")
            return workflow_results
            
        except Exception as e:
            self.logger.error(f"Systematic review workflow failed: {e}")
            workflow_results['status'] = 'failed'
            workflow_results['error'] = str(e)
            workflow_results['failed_at'] = datetime.now().isoformat()
            return workflow_results
    
    @handle_errors(context="research_plan_validation")
    async def _validate_research_plan(self, research_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate research plan according to PICO/PECO criteria (FR-1).
        
        Args:
            research_plan: Research plan to validate
            
        Returns:
            Dict containing validation results and validated plan
        """
        required_fields = ['objective', 'population', 'outcomes']
        missing_fields = []
        
        for field in required_fields:
            if field not in research_plan or not research_plan[field]:
                missing_fields.append(field)
        
        if missing_fields:
            return {
                'valid': False,
                'missing_fields': missing_fields,
                'message': f"Missing required fields: {', '.join(missing_fields)}"
            }
        
        # Create validated plan with defaults
        validated_plan = {
            'objective': research_plan['objective'],
            'population': research_plan['population'],
            'intervention': research_plan.get('intervention', ''),
            'comparison': research_plan.get('comparison', ''),
            'outcomes': research_plan['outcomes'],
            'timeframe': research_plan.get('timeframe', ''),
            'inclusion_criteria': research_plan.get('inclusion_criteria', {}),
            'exclusion_criteria': research_plan.get('exclusion_criteria', {}),
            'search_terms': research_plan.get('search_terms', []),
            'plan_hash': self._calculate_plan_hash(research_plan)
        }
        
        return {
            'valid': True,
            'validated_plan': validated_plan,
            'message': 'Research plan validated successfully'
        }
    
    async def _execute_search_strategy(self, research_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute multi-source search strategy (FR-2).
        
        Args:
            research_plan: Validated research plan
            
        Returns:
            Dict containing search results from all sources
        """
        search_query = self._build_search_query(research_plan)
        
        # Configure sources based on review config
        sources_config = self.review_config.get('sources', [
            {'name': 'pubmed', 'enabled': True, 'max_results': 1000},
            {'name': 'semantic_scholar', 'enabled': True, 'max_results': 500}
        ])
        
        all_results = []
        source_results = {}
        
        for source_config in sources_config:
            if not source_config.get('enabled', True):
                continue
                
            source_name = source_config['name']
            max_results = source_config.get('max_results', 500)
            
            try:
                self.logger.info(f"Searching {source_name} with query: {search_query}")
                
                if source_name == 'pubmed':
                    results = await self.literature_agent._search_pubmed(search_query, max_results)
                elif source_name == 'semantic_scholar':
                    results = await self.literature_agent._search_semantic_scholar(search_query, max_results)
                else:
                    # Fallback to general academic search
                    search_result = await self.literature_agent._search_academic_papers({
                        'query': search_query,
                        'max_results': max_results
                    })
                    results = search_result.get('results', [])
                
                # Convert results to StudyRecord format
                study_records = self._convert_to_study_records(results, source_name)
                source_results[source_name] = {
                    'count': len(study_records),
                    'studies': study_records
                }
                all_results.extend(study_records)
                
                self.logger.info(f"Retrieved {len(study_records)} studies from {source_name}")
                
            except Exception as e:
                self.logger.error(f"Search failed for {source_name}: {e}")
                source_results[source_name] = {
                    'count': 0,
                    'studies': [],
                    'error': str(e)
                }
        
        return {
            'search_query': search_query,
            'total_retrieved': len(all_results),
            'source_results': source_results,
            'all_results': all_results
        }
    
    async def _deduplicate_and_cluster(self, studies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Remove duplicates and cluster related studies (FR-2.6, FR-2.7).
        
        Args:
            studies: List of study records
            
        Returns:
            Dict containing deduplicated studies and cluster information
        """
        if not studies:
            return {
                'unique_studies': [],
                'duplicates_removed': 0,
                'clusters': []
            }
        
        # Track duplicates by DOI, title similarity, and content hash
        seen_dois = set()
        seen_hashes = set()
        title_cache = {}
        unique_studies = []
        duplicates = []
        
        for study in studies:
            is_duplicate = False
            
            # Check DOI duplicates
            doi = study.get('doi') or study.get('metadata', {}).get('doi')
            if doi:
                if doi in seen_dois:
                    duplicates.append(study)
                    is_duplicate = True
                else:
                    seen_dois.add(doi)
            
            # Check content hash duplicates
            if not is_duplicate:
                content_hash = study.get('content_hash')
                if not content_hash:
                    content_hash = self._calculate_content_hash(study)
                    study['content_hash'] = content_hash
                
                if content_hash in seen_hashes:
                    duplicates.append(study)
                    is_duplicate = True
                else:
                    seen_hashes.add(content_hash)
            
            # Check title similarity (basic implementation)
            if not is_duplicate:
                title = study.get('title', '').lower().strip()
                if title:
                    # Simple exact title match (could be enhanced with fuzzy matching)
                    if title in title_cache:
                        duplicates.append(study)
                        is_duplicate = True
                    else:
                        title_cache[title] = study
            
            if not is_duplicate:
                unique_studies.append(study)
        
        # Basic clustering by author groups (simplified implementation)
        clusters = self._cluster_studies(unique_studies)
        
        return {
            'unique_studies': unique_studies,
            'duplicates_removed': len(duplicates),
            'duplicates': duplicates,
            'clusters': clusters
        }
    
    async def _title_abstract_screening(self, studies: List[Dict[str, Any]], 
                                      criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform title/abstract screening using LLM assistance (FR-3).
        
        Args:
            studies: List of studies to screen
            criteria: Inclusion/exclusion criteria
            
        Returns:
            Dict containing screening results
        """
        if not studies:
            return {
                'included_studies': [],
                'excluded_studies': [],
                'included_count': 0,
                'excluded_count': 0,
                'exclusion_reasons': []
            }
        
        included_studies = []
        excluded_studies = []
        exclusion_reasons = []
        
        for study in studies:
            try:
                # Create screening prompt
                screening_prompt = self._create_screening_prompt(study, criteria, 'title_abstract')
                
                # Get AI decision (simplified - would use actual AI client)
                ai_response = await self._get_ai_screening_decision(screening_prompt)
                
                decision = ai_response.get('decision', ScreeningDecision.UNCERTAIN)
                confidence = ai_response.get('confidence', 0.0)
                rationale = ai_response.get('rationale', '')
                
                # Create screening result
                screening_result = ScreeningResult(
                    record_id=study.get('id', ''),
                    stage='title_abstract',
                    decision=decision,
                    reason_code=ai_response.get('reason_code'),
                    actor='ai',
                    confidence_score=confidence,
                    rationale=rationale,
                    timestamp=datetime.now()
                )
                
                # Apply confidence threshold
                if confidence < self.confidence_threshold and self.require_human_review:
                    # Mark for human review (simplified implementation)
                    screening_result.actor = 'human_required'
                
                if decision == ScreeningDecision.INCLUDE:
                    study['screening_result'] = screening_result
                    included_studies.append(study)
                else:
                    study['screening_result'] = screening_result
                    excluded_studies.append(study)
                    if screening_result.reason_code:
                        exclusion_reasons.append({
                            'code': screening_result.reason_code,
                            'count': 1
                        })
                
            except Exception as e:
                self.logger.error(f"Screening failed for study {study.get('id', 'unknown')}: {e}")
                # Default to exclude if screening fails
                excluded_studies.append(study)
        
        # Aggregate exclusion reasons
        reason_counts = {}
        for reason in exclusion_reasons:
            code = reason['code']
            reason_counts[code] = reason_counts.get(code, 0) + reason['count']
        
        aggregated_reasons = [{'code': code, 'count': count} 
                            for code, count in reason_counts.items()]
        
        return {
            'included_studies': included_studies,
            'excluded_studies': excluded_studies,
            'included_count': len(included_studies),
            'excluded_count': len(excluded_studies),
            'exclusion_reasons': aggregated_reasons
        }
    
    async def _full_text_screening(self, studies: List[Dict[str, Any]], 
                                 criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform full text screening (FR-3).
        
        Args:
            studies: List of studies that passed title/abstract screening
            criteria: Inclusion/exclusion criteria
            
        Returns:
            Dict containing full text screening results
        """
        # Similar to title/abstract screening but with full text analysis
        # For now, implementing simplified version
        
        included_studies = []
        excluded_studies = []
        exclusion_reasons = []
        
        for study in studies:
            try:
                # For demonstration, include 80% of studies
                # In real implementation, would analyze full text
                import random
                if random.random() > 0.2:  # 80% inclusion rate
                    included_studies.append(study)
                else:
                    excluded_studies.append(study)
                    exclusion_reasons.append({
                        'code': 'INSUFFICIENT_DATA',
                        'count': 1
                    })
                    
            except Exception as e:
                self.logger.error(f"Full text screening failed for study {study.get('id', 'unknown')}: {e}")
                excluded_studies.append(study)
        
        return {
            'included_studies': included_studies,
            'excluded_studies': excluded_studies,
            'included_count': len(included_studies),
            'excluded_count': len(excluded_studies),
            'exclusion_reasons': exclusion_reasons
        }
    
    def _build_search_query(self, research_plan: Dict[str, Any]) -> str:
        """Build search query from research plan."""
        objective = research_plan.get('objective', '')
        population = research_plan.get('population', '')
        intervention = research_plan.get('intervention', '')
        outcomes = research_plan.get('outcomes', [])
        
        # Simple query construction (could be enhanced with Boolean logic)
        query_parts = [objective]
        if population:
            query_parts.append(population)
        if intervention:
            query_parts.append(intervention)
        if outcomes:
            query_parts.extend(outcomes[:2])  # Limit to first 2 outcomes
        
        return ' '.join(query_parts)
    
    def _convert_to_study_records(self, results: List[Dict[str, Any]], 
                                source: str) -> List[Dict[str, Any]]:
        """Convert search results to standardized study records."""
        study_records = []
        
        for result in results:
            # Extract metadata
            metadata = result.get('metadata', {})
            
            study_record = {
                'id': generate_timestamped_id('study'),
                'title': result.get('title', 'Untitled'),
                'authors': self._extract_authors(result),
                'year': self._extract_year(result),
                'doi': result.get('doi') or metadata.get('doi'),
                'source': source,
                'abstract': self._extract_abstract(result),
                'full_text_path': None,  # Would be populated if full text retrieved
                'content_hash': self._calculate_content_hash(result),
                'license_info': None,
                'metadata': metadata,
                'created_at': datetime.now()
            }
            
            study_records.append(study_record)
        
        return study_records
    
    def _extract_authors(self, result: Dict[str, Any]) -> List[str]:
        """Extract author list from result."""
        authors = []
        
        # Check different author field formats
        if 'authors' in result:
            if isinstance(result['authors'], list):
                authors = result['authors']
            elif isinstance(result['authors'], str):
                authors = [result['authors']]
        
        metadata = result.get('metadata', {})
        if not authors and 'authors' in metadata:
            if isinstance(metadata['authors'], list):
                authors = metadata['authors']
            elif isinstance(metadata['authors'], str):
                authors = [metadata['authors']]
        
        return authors
    
    def _extract_year(self, result: Dict[str, Any]) -> Optional[int]:
        """Extract publication year from result."""
        # Check multiple possible year fields
        year_fields = ['year', 'publication_year', 'pubdate']
        
        for field in year_fields:
            if field in result:
                try:
                    year_value = result[field]
                    if isinstance(year_value, int):
                        return year_value
                    elif isinstance(year_value, str):
                        # Try to extract year from string
                        import re
                        year_match = re.search(r'\b(19|20)\d{2}\b', year_value)
                        if year_match:
                            return int(year_match.group())
                except:
                    pass
        
        # Check metadata
        metadata = result.get('metadata', {})
        for field in year_fields:
            if field in metadata:
                try:
                    year_value = metadata[field]
                    if isinstance(year_value, int):
                        return year_value
                    elif isinstance(year_value, str):
                        import re
                        year_match = re.search(r'\b(19|20)\d{2}\b', year_value)
                        if year_match:
                            return int(year_match.group())
                except:
                    pass
        
        return None
    
    def _extract_abstract(self, result: Dict[str, Any]) -> Optional[str]:
        """Extract abstract from result."""
        abstract = result.get('abstract')
        if not abstract:
            # Check content field for abstract
            content = result.get('content', '')
            if 'Abstract:' in content:
                abstract_start = content.find('Abstract:') + 9
                abstract_end = content.find('|', abstract_start)
                if abstract_end == -1:
                    abstract_end = len(content)
                abstract = content[abstract_start:abstract_end].strip()
        
        return abstract
    
    def _calculate_content_hash(self, content: Dict[str, Any]) -> str:
        """Calculate SHA-256 hash of study content."""
        # Create normalized content string for hashing
        normalized_content = {
            'title': content.get('title', '').lower().strip(),
            'authors': sorted([a.lower().strip() for a in self._extract_authors(content)]),
            'year': self._extract_year(content)
        }
        
        content_str = json.dumps(normalized_content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def _calculate_plan_hash(self, research_plan: Dict[str, Any]) -> str:
        """Calculate SHA-256 hash of research plan."""
        plan_str = json.dumps(research_plan, sort_keys=True)
        return hashlib.sha256(plan_str.encode()).hexdigest()
    
    def _cluster_studies(self, studies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Basic study clustering by author overlap."""
        # Simplified clustering implementation
        clusters = []
        clustered_studies = set()
        
        for i, study in enumerate(studies):
            if i in clustered_studies:
                continue
                
            cluster = {
                'cluster_id': generate_timestamped_id('cluster'),
                'primary_study': study,
                'related_studies': []
            }
            
            study_authors = set(study.get('authors', []))
            
            for j, other_study in enumerate(studies[i+1:], i+1):
                if j in clustered_studies:
                    continue
                    
                other_authors = set(other_study.get('authors', []))
                
                # Check for author overlap (simplified clustering)
                if study_authors & other_authors:  # Any common authors
                    cluster['related_studies'].append(other_study)
                    clustered_studies.add(j)
            
            if cluster['related_studies']:  # Only add clusters with related studies
                clusters.append(cluster)
                clustered_studies.add(i)
        
        return clusters
    
    def _create_screening_prompt(self, study: Dict[str, Any], 
                               criteria: Dict[str, Any], stage: str) -> str:
        """Create prompt for LLM-assisted screening."""
        title = study.get('title', 'No title')
        abstract = study.get('abstract', 'No abstract available')
        authors = ', '.join(study.get('authors', []))
        
        prompt = f"""
You are conducting a systematic literature review screening at the {stage} stage.

Study Information:
Title: {title}
Authors: {authors}
Abstract: {abstract}

Inclusion Criteria:
{json.dumps(criteria.get('inclusion', {}), indent=2)}

Exclusion Criteria:
{json.dumps(criteria.get('exclusion', {}), indent=2)}

Please evaluate this study and provide:
1. Decision: include, exclude, or uncertain
2. Confidence: 0.0-1.0 confidence score
3. Reason code: if excluding, use one of {list(self.exclusion_reasons.keys())}
4. Rationale: brief explanation for the decision

Respond in JSON format:
{{
    "decision": "include|exclude|uncertain",
    "confidence": 0.0-1.0,
    "reason_code": "CODE" (if excluding),
    "rationale": "explanation"
}}
"""
        return prompt
    
    async def _get_ai_screening_decision(self, prompt: str) -> Dict[str, Any]:
        """Get AI screening decision (simplified implementation)."""
        # Placeholder implementation - would use actual AI client
        # For now, return mock decision
        import random
        
        decisions = [ScreeningDecision.INCLUDE, ScreeningDecision.EXCLUDE]
        decision = random.choice(decisions)
        
        return {
            'decision': decision,
            'confidence': random.uniform(0.6, 0.95),
            'reason_code': random.choice(list(self.exclusion_reasons.keys())) if decision == ScreeningDecision.EXCLUDE else None,
            'rationale': f'Based on {prompt[:50]}... analysis'
        }


if __name__ == "__main__":
    import sys
    import os
    
    # Add the project root to the Python path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, project_root)
    
    async def main():
        """Test the systematic review agent."""
        from src.config.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        agent = SystematicReviewAgent(config_manager)
        
        try:
            await agent.initialize()
            
            # Test research plan
            research_plan = {
                'objective': 'Effectiveness of AI in medical diagnosis',
                'population': 'Healthcare providers and patients',
                'intervention': 'AI-assisted diagnostic tools',
                'comparison': 'Traditional diagnostic methods',
                'outcomes': ['diagnostic accuracy', 'time to diagnosis', 'cost effectiveness'],
                'timeframe': '2020-2025'
            }
            
            # Run systematic review workflow
            result = await agent.systematic_review_workflow(
                research_plan, 'test_task_001', 'test_user'
            )
            
            print("Systematic Review Results:")
            print(json.dumps(result, indent=2, default=str))
            
        finally:
            if hasattr(agent, '_cleanup_agent'):
                await agent._cleanup_agent()
    
    asyncio.run(main())
