"""
Configuration schema and validation for systematic literature reviews.

This module extends the existing Eunice configuration system to support
systematic review specific settings and parameters.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml


@dataclass
class SourceConfig:
    """Configuration for literature search sources."""

    name: str
    enabled: bool = True
    max_results: int = 1000
    api_key_name: Optional[str] = None
    rate_limit: Optional[int] = None  # requests per minute
    retry_attempts: int = 3
    timeout: int = 30
    custom_parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreeningConfig:
    """Configuration for screening workflow."""

    confidence_threshold: float = 0.7
    require_human_review: bool = True
    enable_dual_screening: bool = False
    exclusion_reasons: List[str] = field(
        default_factory=lambda: [
            "WRONG_POPULATION",
            "WRONG_INTERVENTION",
            "WRONG_COMPARATOR",
            "WRONG_OUTCOME",
            "WRONG_STUDY_DESIGN",
            "NOT_PEER_REVIEWED",
            "LANGUAGE_RESTRICTION",
            "INSUFFICIENT_DATA",
            "FULL_TEXT_UNAVAILABLE",
        ]
    )
    ai_model: str = "gpt - 4o"
    batch_size: int = 10


@dataclass
class QualityAppraisalConfig:
    """Configuration for quality / bias appraisal."""

    enabled_plugins: List[str] = field(default_factory=lambda: ["robins - i", "rob2"])
    require_human_validation: bool = True
    confidence_threshold: float = 0.8
    ai_assistance: bool = True
    parallel_assessment: bool = False


@dataclass
class SynthesisConfig:
    """Configuration for evidence synthesis."""

    default_method: str = "narrative"  # narrative, thematic, meta - aggregation
    enable_contradiction_detection: bool = True
    confidence_grading: bool = True
    evidence_table_format: str = "markdown"  # markdown, csv, json
    include_forest_plots: bool = False


@dataclass
class OutputConfig:
    """Configuration for output generation."""

    citation_style: str = "vancouver"
    produce_pdf: bool = True
    include_appendices: bool = True
    generate_flow_diagram: bool = True
    accessibility_compliance: bool = True  # WCAG 2.1 AA
    output_directory: str = "outputs"


@dataclass
class SecurityConfig:
    """Configuration for security and compliance."""

    sanitize_pdfs: bool = True
    redact_pii: bool = True
    content_filtering: bool = True
    audit_logging: bool = True
    encryption_at_rest: bool = True
    gdpr_compliance: bool = True


@dataclass
class WorkflowConfig:
    """Configuration for workflow orchestration."""

    checkpoints: List[str] = field(
        default_factory=lambda: ["after_query_generation", "after_screening", "before_publication"]
    )
    enable_resumption: bool = True
    auto_save_interval: int = 300  # seconds
    parallel_processing: bool = True
    max_concurrent_tasks: int = 5


@dataclass
class LLMConfig:
    """Configuration for LLM usage."""

    model: str = "gpt - 4o"
    temperature: float = 0.0
    seed: int = 42
    max_tokens: int = 4096
    deterministic_mode: bool = False
    cache_responses: bool = True
    cost_tracking: bool = True


@dataclass
class SystematicReviewConfig:
    """Complete systematic review configuration."""

    sources: List[SourceConfig] = field(default_factory=list)
    screening: ScreeningConfig = field(default_factory=ScreeningConfig)
    quality_appraisal: QualityAppraisalConfig = field(default_factory=QualityAppraisalConfig)
    synthesis: SynthesisConfig = field(default_factory=SynthesisConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)

    def __post_init__(self):
        """Initialize default sources if none provided."""
        if not self.sources:
            self.sources = self._get_default_sources()

    def _get_default_sources(self) -> List[SourceConfig]:
        """Get default source configurations."""
        return [
            SourceConfig(name="pubmed", enabled=True, max_results=5000, api_key_name="pubmed_api_key", rate_limit=10),
            SourceConfig(name="semantic_scholar", enabled=True, max_results=2000, rate_limit=100),
            SourceConfig(name="crossref", enabled=True, max_results=3000, rate_limit=50),
            SourceConfig(name="openalex", enabled=False, max_results=2000, rate_limit=10),
            SourceConfig(name="arxiv", enabled=False, max_results=1000, rate_limit=3),
        ]


class SystematicReviewConfigManager:
    """Manager for systematic review configuration."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path) if config_path else None
        self.config = self._load_config()

    def _load_config(self) -> SystematicReviewConfig:
        """Load configuration from file or create defaults."""
        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    if self.config_path.suffix.lower() in [".yaml", ".yml"]:
                        config_data = yaml.safe_load(f)
                    else:
                        config_data = json.load(f)

                return self._parse_config_data(config_data)
            except Exception as e:
                print(f"Error loading config from {self.config_path}: {e}")
                print("Using default configuration")

        return SystematicReviewConfig()

    def _parse_config_data(self, config_data: Dict[str, Any]) -> SystematicReviewConfig:
        """Parse configuration data into structured config."""
        # Parse sources
        sources = []
        for source_data in config_data.get("sources", []):
            if isinstance(source_data, dict):
                sources.append(SourceConfig(**source_data))
            elif isinstance(source_data, str):
                sources.append(SourceConfig(name=source_data))

        # Parse other sections
        screening_data = config_data.get("screening", {})
        screening = ScreeningConfig(**screening_data)

        quality_data = config_data.get("quality_appraisal", {})
        quality_appraisal = QualityAppraisalConfig(**quality_data)

        synthesis_data = config_data.get("synthesis", {})
        synthesis = SynthesisConfig(**synthesis_data)

        output_data = config_data.get("output", {})
        output = OutputConfig(**output_data)

        security_data = config_data.get("security", {})
        security = SecurityConfig(**security_data)

        workflow_data = config_data.get("workflow", {})
        workflow = WorkflowConfig(**workflow_data)

        llm_data = config_data.get("llm", {})
        llm = LLMConfig(**llm_data)

        return SystematicReviewConfig(
            sources=sources,
            screening=screening,
            quality_appraisal=quality_appraisal,
            synthesis=synthesis,
            output=output,
            security=security,
            workflow=workflow,
            llm=llm,
        )

    def save_config(self, config_path: Optional[Union[str, Path]] = None) -> None:
        """
        Save configuration to file.

        Args:
            config_path: Optional path to save config (defaults to loaded path)
        """
        save_path = Path(config_path) if config_path else self.config_path
        if not save_path:
            raise ValueError("No config path specified")

        config_dict = self._config_to_dict()

        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w") as f:
            if save_path.suffix.lower() in [".yaml", ".yml"]:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            else:
                json.dump(config_dict, f, indent=2)

    def _config_to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "sources": [
                {
                    "name": s.name,
                    "enabled": s.enabled,
                    "max_results": s.max_results,
                    "api_key_name": s.api_key_name,
                    "rate_limit": s.rate_limit,
                    "retry_attempts": s.retry_attempts,
                    "timeout": s.timeout,
                    "custom_parameters": s.custom_parameters,
                }
                for s in self.config.sources
            ],
            "screening": {
                "confidence_threshold": self.config.screening.confidence_threshold,
                "require_human_review": self.config.screening.require_human_review,
                "enable_dual_screening": self.config.screening.enable_dual_screening,
                "exclusion_reasons": self.config.screening.exclusion_reasons,
                "ai_model": self.config.screening.ai_model,
                "batch_size": self.config.screening.batch_size,
            },
            "quality_appraisal": {
                "enabled_plugins": self.config.quality_appraisal.enabled_plugins,
                "require_human_validation": self.config.quality_appraisal.require_human_validation,
                "confidence_threshold": self.config.quality_appraisal.confidence_threshold,
                "ai_assistance": self.config.quality_appraisal.ai_assistance,
                "parallel_assessment": self.config.quality_appraisal.parallel_assessment,
            },
            "synthesis": {
                "default_method": self.config.synthesis.default_method,
                "enable_contradiction_detection": self.config.synthesis.enable_contradiction_detection,
                "confidence_grading": self.config.synthesis.confidence_grading,
                "evidence_table_format": self.config.synthesis.evidence_table_format,
                "include_forest_plots": self.config.synthesis.include_forest_plots,
            },
            "output": {
                "citation_style": self.config.output.citation_style,
                "produce_pdf": self.config.output.produce_pdf,
                "include_appendices": self.config.output.include_appendices,
                "generate_flow_diagram": self.config.output.generate_flow_diagram,
                "accessibility_compliance": self.config.output.accessibility_compliance,
                "output_directory": self.config.output.output_directory,
            },
            "security": {
                "sanitize_pdfs": self.config.security.sanitize_pdfs,
                "redact_pii": self.config.security.redact_pii,
                "content_filtering": self.config.security.content_filtering,
                "audit_logging": self.config.security.audit_logging,
                "encryption_at_rest": self.config.security.encryption_at_rest,
                "gdpr_compliance": self.config.security.gdpr_compliance,
            },
            "workflow": {
                "checkpoints": self.config.workflow.checkpoints,
                "enable_resumption": self.config.workflow.enable_resumption,
                "auto_save_interval": self.config.workflow.auto_save_interval,
                "parallel_processing": self.config.workflow.parallel_processing,
                "max_concurrent_tasks": self.config.workflow.max_concurrent_tasks,
            },
            "llm": {
                "model": self.config.llm.model,
                "temperature": self.config.llm.temperature,
                "seed": self.config.llm.seed,
                "max_tokens": self.config.llm.max_tokens,
                "deterministic_mode": self.config.llm.deterministic_mode,
                "cache_responses": self.config.llm.cache_responses,
                "cost_tracking": self.config.llm.cost_tracking,
            },
        }

    def validate_config(self) -> List[str]:
        """
        Validate configuration and return list of issues.

        Returns:
            List of validation error messages
        """
        errors = []

        # Validate sources
        if not self.config.sources:
            errors.append("No sources configured")

        for source in self.config.sources:
            if not source.name:
                errors.append("Source missing name")
            if source.max_results <= 0:
                errors.append(f"Source {source.name} has invalid max_results")

        # Validate screening
        if not (0.0 <= self.config.screening.confidence_threshold <= 1.0):
            errors.append("Screening confidence threshold must be between 0.0 and 1.0")

        # Validate quality appraisal
        if not (0.0 <= self.config.quality_appraisal.confidence_threshold <= 1.0):
            errors.append("Quality appraisal confidence threshold must be between 0.0 and 1.0")

        # Validate synthesis
        valid_methods = ["narrative", "thematic", "meta - aggregation"]
        if self.config.synthesis.default_method not in valid_methods:
            errors.append(f"Invalid synthesis method. Must be one of: {valid_methods}")

        # Validate output
        valid_formats = ["markdown", "csv", "json"]
        if self.config.synthesis.evidence_table_format not in valid_formats:
            errors.append(f"Invalid evidence table format. Must be one of: {valid_formats}")

        # Validate LLM
        if not (0.0 <= self.config.llm.temperature <= 2.0):
            errors.append("LLM temperature must be between 0.0 and 2.0")

        if self.config.llm.max_tokens <= 0:
            errors.append("LLM max_tokens must be positive")

        return errors

    def get_source_config(self, source_name: str) -> Optional[SourceConfig]:
        """Get configuration for a specific source."""
        for source in self.config.sources:
            if source.name == source_name:
                return source
        return None

    def is_source_enabled(self, source_name: str) -> bool:
        """Check if a source is enabled."""
        source = self.get_source_config(source_name)
        return source is not None and source.enabled


def create_default_config_file(config_path: Union[str, Path]) -> None:
    """
    Create a default systematic review configuration file.

    Args:
        config_path: Path where to create the config file
    """
    config_manager = SystematicReviewConfigManager()
    config_manager.save_config(config_path)
    print(f"Created default systematic review config at: {config_path}")


if __name__ == "__main__":
    # Test configuration management
    import os
    import tempfile

    # Create a test config
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        test_config = """
sources:
  - name: pubmed
    enabled: true
    max_results: 5000
  - name: semantic_scholar
    enabled: true
    max_results: 2000
screening:
  confidence_threshold: 0.8
  require_human_review: true
llm:
  model: gpt - 4o
  temperature: 0.0
  seed: 42
output:
  citation_style: vancouver
  produce_pdf: true
"""
        f.write(test_config)
        temp_path = f.name

    try:
        # Test loading config
        config_manager = SystematicReviewConfigManager(temp_path)

        print("Loaded Configuration:")
        print(f"Sources: {len(config_manager.config.sources)}")
        for source in config_manager.config.sources:
            print(f"  - {source.name}: enabled={source.enabled}, max_results={source.max_results}")

        print(f"Screening confidence threshold: {config_manager.config.screening.confidence_threshold}")
        print(f"LLM model: {config_manager.config.llm.model}")
        print(f"Output citation style: {config_manager.config.output.citation_style}")

        # Test validation
        errors = config_manager.validate_config()
        print(f"\nValidation errors: {len(errors)}")
        for error in errors:
            print(f"  - {error}")

        # Test source queries
        print(f"\nPubMed enabled: {config_manager.is_source_enabled('pubmed')}")
        print(f"ArXiv enabled: {config_manager.is_source_enabled('arxiv')}")

    finally:
        # Clean up
        os.unlink(temp_path)
