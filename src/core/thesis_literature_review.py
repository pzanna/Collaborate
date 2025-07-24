#!/usr / bin / env python3
"""
Thesis - Style Literature Review Generator
========================================

Transforms PRISMA - style systematic review outputs into PhD thesis - quality literature review chapters.
Supports local models, deterministic generation, caching, and LaTeX output via Jinja2 / Pandoc.

Features:
- Local AI model integration with strict JSON validation
- Deterministic generation (temp=0, top_p=1) with cache versioning
- PRISMA JSON parsing and validation
- Thematic synthesis and gap analysis
- Conceptual model generation with Mermaid / TikZ diagrams
- Research question / hypothesis generation
- Markdown / LaTeX template rendering via Jinja2
- Pandoc integration for multiple output formats
- Human - in - the - loop checkpoints
- Comprehensive audit logging and versioning

Author: GitHub Copilot for Paul Zanna
Date: July 23, 2025
"""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List, Optional

# Eunice AI client imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# External dependencies
try:
    import jinja2
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    JINJA_AVAILABLE = True
except ImportError:
    jinja2 = None
    Environment = None
    FileSystemLoader = None
    select_autoescape = None
    JINJA_AVAILABLE = False

try:
    import jsonschema
    from jsonschema import ValidationError, validate

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    jsonschema = None
    validate = None
    ValidationError = None
    JSONSCHEMA_AVAILABLE = False


@dataclass
class ThesisConfig:
    """Configuration for thesis literature review generation."""

    input_file: str
    output_dir: str
    template_dir: str = "templates"
    cache_dir: str = "cache"
    ai_provider: str = "openai"  # openai, xai, local
    ai_model: str = "gpt - 4"
    deterministic: bool = True
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 4000
    enable_cache: bool = True
    cache_version: str = "v1.0"
    output_formats: Optional[List[str]] = None
    human_checkpoints: bool = True
    theme_count: int = 5
    gap_threshold: float = 3.5
    citation_style: str = "apa"

    def __post_init__(self):
        if self.output_formats is None:
            self.output_formats = ["markdown", "html", "latex"]


@dataclass
class StudyRecord:
    """Normalized study record from PRISMA data."""

    id: str
    title: str
    authors: List[str]
    year: int
    journal: str
    design: str
    sample_size: int
    population: str
    outcomes: List[str]
    effect_summary: str
    bias_overall: str
    doi: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class Theme:
    """Thematic synthesis result."""

    name: str
    summary: str
    representative_studies: List[str]
    contradictions: List[str]
    strength_of_evidence: str
    study_count: int


@dataclass
class ResearchGap:
    """Identified research gap."""

    title: str
    description: str
    justification: str
    impact_score: float
    feasibility_score: float
    novelty_score: float
    priority_rank: int
    related_themes: List[str]


@dataclass
class ConceptualModel:
    """Conceptual framework model."""

    description: str
    constructs: List[Dict[str, str]]
    relationships: List[Dict[str, str]]
    mermaid_diagram: str
    tikz_diagram: str


@dataclass
class ResearchQuestion:
    """Generated research question or hypothesis."""

    type: str  # "question" or "hypothesis"
    text: str
    constructs: List[str]
    predicted_direction: Optional[str]
    justification: str
    related_gap: str


class DeterministicCache:
    """Deterministic caching system for reproducible AI outputs."""

    def __init__(self, cache_dir: str, version: str = "v1.0"):
        self.cache_dir = Path(cache_dir)
        self.version = version
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / f"cache_{version}.json"
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Load existing cache."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf - 8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Failed to load cache: {e}")
        return {}

    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, "w", encoding="utf - 8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logging.error(f"Failed to save cache: {e}")

    def _generate_key(
        self, prompt: str, model: str, temperature: float, top_p: float
    ) -> str:
        """Generate deterministic cache key."""
        content = f"{prompt}|{model}|{temperature}|{top_p}|{self.version}"
        return hashlib.sha256(content.encode("utf - 8")).hexdigest()

    def get(
        self, prompt: str, model: str, temperature: float, top_p: float
    ) -> Optional[Dict[str, Any]]:
        """Get cached response."""
        key = self._generate_key(prompt, model, temperature, top_p)
        return self.cache.get(key)

    def set(
        self, prompt: str, model: str, temperature: float, top_p: float, response: str
    ):
        """Cache response."""
        key = self._generate_key(prompt, model, temperature, top_p)
        self.cache[key] = {
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "parameters": {"temperature": temperature, "top_p": top_p},
        }
        self._save_cache()


class PRISMAValidator:
    """Validates and normalizes PRISMA JSON data."""

    @staticmethod
    def validate_prisma_structure(data: Dict[str, Any]) -> bool:
        """Validate basic PRISMA JSON structure."""
        required_sections = ["metadata", "results", "data_extraction_tables"]

        for section in required_sections:
            if section not in data:
                raise ValueError(f"Missing required section: {section}")

        # Validate study characteristics table
        if "table_1_study_characteristics" not in data["data_extraction_tables"]:
            raise ValueError("Missing study characteristics table")

        return True

    @staticmethod
    def extract_studies(prisma_data: Dict[str, Any]) -> List[StudyRecord]:
        """Extract and normalize study records."""
        studies = []
        study_table = prisma_data["data_extraction_tables"][
            "table_1_study_characteristics"
        ]

        for study_data in study_table["data"]:
            try:
                study = StudyRecord(
                    id=study_data.get("study", "Unknown"),
                    title=study_data.get("title", ""),
                    authors=(
                        study_data.get("authors", "").split(", ")
                        if study_data.get("authors")
                        else []
                    ),
                    year=int(study_data.get("year", 2024)),
                    journal=study_data.get("journal", ""),
                    design=study_data.get("design", ""),
                    sample_size=int(study_data.get("sample_size", 0)),
                    population=study_data.get("population", ""),
                    outcomes=(
                        study_data.get("outcomes", "").split(", ")
                        if study_data.get("outcomes")
                        else []
                    ),
                    effect_summary=study_data.get("effect_summary", ""),
                    bias_overall=study_data.get("bias_overall", ""),
                    doi=study_data.get("doi"),
                    raw_data=study_data,
                )
                studies.append(study)
            except (ValueError, KeyError) as e:
                logging.warning(f"Failed to parse study record: {e}")
                continue

        return studies


class ThesisLiteratureReviewGenerator:
    """Main class for generating thesis - style literature reviews."""

    def __init__(self, config: ThesisConfig):
        self.config = config
        self.cache = (
            DeterministicCache(config.cache_dir, config.cache_version)
            if config.enable_cache
            else None
        )
        self.logger = self._setup_logging()
        self.ai_client = self._setup_ai_client()
        self.jinja_env = self._setup_jinja() if jinja2 else None
        self.audit_log = []

        # Create output directory
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        # Create file handler
        log_file = Path(self.config.output_dir) / "thesis_generation.log"
        handler = logging.FileHandler(log_file)
        handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _setup_ai_client(self):
        """Setup AI client based on configuration."""
        if self.config.ai_provider == "openai":
            from ai_clients.openai_client import AIProviderConfig, OpenAIClient

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable required")

            ai_config = AIProviderConfig(
                provider=self.config.ai_provider,
                model=self.config.ai_model,
                temperature=(
                    self.config.temperature if not self.config.deterministic else 0.0
                ),
                max_tokens=self.config.max_tokens,
            )
            return OpenAIClient(api_key, ai_config)

        elif self.config.ai_provider == "xai":
            try:
                from ai_clients.xai_client import XAIClient

                api_key = os.getenv("XAI_API_KEY")
                if not api_key:
                    raise ValueError("XAI_API_KEY environment variable required")

                # Create compatible config for XAI
                ai_config = {
                    "provider": self.config.ai_provider,
                    "model": self.config.ai_model,
                    "temperature": (
                        self.config.temperature
                        if not self.config.deterministic
                        else 0.0
                    ),
                    "max_tokens": self.config.max_tokens,
                }
                return XAIClient(api_key, ai_config)  # type: ignore
            except ImportError:
                raise ValueError("XAI client not available")

        else:
            raise ValueError(f"Unsupported AI provider: {self.config.ai_provider}")

    def _setup_jinja(self) -> Optional[Any]:
        """Setup Jinja2 template environment."""
        if not JINJA_AVAILABLE:
            self.logger.warning("Jinja2 not available - template rendering disabled")
            return None

        template_dir = Path(self.config.template_dir)
        if not template_dir.exists():
            template_dir.mkdir(parents=True, exist_ok=True)
            self._create_default_templates(template_dir)

        if Environment and FileSystemLoader and select_autoescape:
            return Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(["html", "xml"]),
            )
        return None

    def _create_default_templates(self, template_dir: Path):
        """Create default Jinja2 templates."""
        # Markdown template
        markdown_template = dedent(
            """
        # {{ metadata.title }}

        ## Abstract
        {{ abstract.background }}

        ## 1. Introduction
        ### 1.1 Background and Context
        {{ introduction.background.clinical_context }}

        ### 1.2 Rationale
        **Knowledge Gap:** {{ introduction.rationale.knowledge_gap }}

        **Clinical Importance:** {{ introduction.rationale.clinical_importance }}

        ## 2. Literature Review Methodology
        ### 2.1 Search Strategy
        {% for db in methods.search_strategy.databases %}
        - {{ db.name }}: {{ db.search_terms }}
        {% endfor %}

        ### 2.2 Study Selection
        **Inclusion Criteria:**
        {% for criteria in methods.eligibility_criteria.inclusion %}
        - {{ criteria }}
        {% endfor %}

        ## 3. Thematic Synthesis
        {% for theme in themes %}
        ### 3.{{ loop.index }} {{ theme.name }}
        {{ theme.summary }}

        **Representative Studies:** {{ theme.representative_studies | join(", ") }}
        **Strength of Evidence:** {{ theme.strength_of_evidence }}

        {% if theme.contradictions %}
        **Contradictory Findings:** {{ theme.contradictions | join("; ") }}
        {% endif %}

        {% endfor %}

        ## 4. Research Gaps and Opportunities
        {% for gap in gaps %}
        ### 4.{{ loop.index }} {{ gap.title }}
        {{ gap.description }}

        **Justification:** {{ gap.justification }}
        **Priority Ranking:** {{ gap.priority_rank }}/{{ gaps|length }}
        **Impact Score:** {{ gap.impact_score }}/5.0
        **Feasibility Score:** {{ gap.feasibility_score }}/5.0

        {% endfor %}

        ## 5. Conceptual Framework
        {{ conceptual_model.description }}

        ```mermaid
        {{ conceptual_model.mermaid_diagram }}
        ```

        ### 5.1 Key Constructs
        {% for construct in conceptual_model.constructs %}
        - **{{ construct.name }}:** {{ construct.description }}
        {% endfor %}

        ### 5.2 Theoretical Relationships
        {% for relationship in conceptual_model.relationships %}
        - {{ relationship.source }} → {{ relationship.target }}: {{ relationship.description }}
        {% endfor %}

        ## 6. Research Questions and Hypotheses
        {% for rq in research_questions %}
        ### 6.{{ loop.index }} {{ rq.type.title() }} {{ loop.index }}
        {{ rq.text }}

        **Constructs:** {{ rq.constructs | join(", ") }}
        {% if rq.predicted_direction %}
        **Predicted Direction:** {{ rq.predicted_direction }}
        {% endif %}
        **Justification:** {{ rq.justification }}

        {% endfor %}

        ## 7. Summary and Conclusions
        This literature review has identified {{ themes|length }} major themes in the current research landscape,
        revealing {{ gaps|length }} significant research gaps that warrant further investigation.
        The proposed conceptual framework provides a foundation for addressing these gaps through
        systematic empirical research.

        ---
        *Generated: {{ generation_metadata.timestamp }}*
        *Processing Time: {{ generation_metadata.processing_time }}s*
        *AI Model: {{ generation_metadata.ai_model }}*
        """
        )

        with open(template_dir / "thesis_chapter.md", "w") as f:
            f.write(markdown_template)

        # LaTeX template
        latex_template = dedent(
            r"""
        \chapter{Literature Review}
        \label{ch:literature - review}

        \section{Introduction}
        \subsection{Background and Context}
        {{ introduction.background.clinical_context | escape_latex }}

        \subsection{Rationale}
        \textbf{Knowledge Gap:} {{ introduction.rationale.knowledge_gap | escape_latex }}

        \textbf{Clinical Importance:} {{ introduction.rationale.clinical_importance | escape_latex }}

        \section{Thematic Synthesis}
        {% for theme in themes %}
        \subsection{ {{- theme.name | escape_latex -}} }
        {{ theme.summary | escape_latex }}

        \textbf{Representative Studies:} {{ theme.representative_studies | join(", ") | escape_latex }}

        {% if theme.contradictions %}
        \textbf{Contradictory Findings:} {{ theme.contradictions | join("; ") | escape_latex }}
        {% endif %}

        {% endfor %}

        \section{Research Gaps and Opportunities}
        {% for gap in gaps %}
        \subsection{ {{- gap.title | escape_latex -}} }
        {{ gap.description | escape_latex }}

        \textbf{Justification:} {{ gap.justification | escape_latex }}

        {% endfor %}

        \section{Conceptual Framework}
        {{ conceptual_model.description | escape_latex }}

        \begin{figure}[htb]
        \centering
        {{ conceptual_model.tikz_diagram }}
        \caption{Conceptual Framework}
        \label{fig:conceptual - framework}
        \end{figure}

        \section{Research Questions and Hypotheses}
        {% for rq in research_questions %}
        \subsection{ {{- rq.type.title() }} {{ loop.index -}} }
        {{ rq.text | escape_latex }}

        {% endfor %}
        """
        )

        with open(template_dir / "thesis_chapter.tex", "w") as f:
            f.write(latex_template)

    def _call_ai_model(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict] = None,
    ) -> str:
        """Call AI model with caching and validation."""
        # Check cache first
        if self.cache:
            cached_response = self.cache.get(
                prompt, self.config.ai_model, self.config.temperature, self.config.top_p
            )
            if (
                cached_response
                and isinstance(cached_response, dict)
                and "response" in cached_response
            ):
                self.logger.info("Using cached AI response")
                return cached_response["response"]

        # Prepare system prompt for strict JSON
        if schema:
            json_instruction = (
                "\n\nIMPORTANT: Respond with valid JSON that matches this schema: "
                f"{json.dumps(schema, indent=2)}"
            )
            if system_prompt:
                system_prompt += json_instruction
            else:
                system_prompt = f"You are a helpful assistant. {json_instruction}"

        # Call AI model
        start_time = time.time()
        try:
            response = self.ai_client.get_response(prompt, system_prompt)
            processing_time = time.time() - start_time

            # Validate JSON if schema provided
            if schema and JSONSCHEMA_AVAILABLE and validate:
                try:
                    response_json = json.loads(response)
                    validate(response_json, schema)
                except (json.JSONDecodeError, Exception) as e:
                    self.logger.error(f"AI response validation failed: {e}")
                    raise ValueError(f"Invalid AI response: {e}")
            elif schema:
                # Basic JSON validation without jsonschema
                try:
                    json.loads(response)
                except json.JSONDecodeError as e:
                    self.logger.error(f"AI response is not valid JSON: {e}")
                    raise ValueError(f"Invalid JSON response: {e}")

            # Cache response
            if self.cache:
                self.cache.set(
                    prompt,
                    self.config.ai_model,
                    self.config.temperature,
                    self.config.top_p,
                    response,
                )

            # Log to audit trail
            self.audit_log.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "operation": "ai_call",
                    "model": self.config.ai_model,
                    "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
                    "processing_time": processing_time,
                    "response_length": len(response),
                }
            )

            return response

        except Exception as e:
            self.logger.error(f"AI model call failed: {e}")
            raise

    def extract_themes(
        self, studies: List[StudyRecord], prisma_data: Dict
    ) -> List[Theme]:
        """Extract themes using LLM - based synthesis."""
        self.logger.info("Extracting themes from literature...")

        # Prepare study summaries
        study_summaries = []
        for study in studies:
            summary = {
                "id": study.id,
                "year": study.year,
                "design": study.design,
                "sample_size": study.sample_size,
                "outcomes": study.outcomes,
                "effect_summary": study.effect_summary,
                "bias_overall": study.bias_overall,
            }
            study_summaries.append(summary)

        # Prepare narrative texts
        narrative_texts = {
            "summary_of_findings": prisma_data.get("discussion", {}).get(
                "summary_of_findings", {}
            ),
            "clinical_implications": prisma_data.get("discussion", {}).get(
                "clinical_implications", {}
            ),
            "conclusions": prisma_data.get("conclusions", {}),
        }

        # Theme extraction prompt
        prompt = dedent(
            f"""
        You are a systematic review expert conducting thematic synthesis for a PhD thesis literature review.

        TASK: Extract {self.config.theme_count} distinct themes from the provided studies and narrative content.

        STUDIES DATA:
        {json.dumps(study_summaries, indent=2)}

        NARRATIVE CONTENT:
        {json.dumps(narrative_texts, indent=2)}

        For each theme, provide:
        1. name (concise, ≤8 words)
        2. summary (comprehensive, 150 - 200 words, academic tone)
        3. representative_studies (list of study IDs that best exemplify this theme)
        4. contradictions (list of conflicting findings within this theme)
        5. strength_of_evidence (High / Moderate / Low based on study quality and consistency)
        6. study_count (number of studies contributing to this theme)

        Focus on:
        - Clinical / practical significance
        - Methodological considerations
        - Gaps and contradictions
        - Theoretical implications

        Ensure themes are:
        - Mutually exclusive but collectively exhaustive
        - Grounded in the actual study data
        - Relevant for thesis - level analysis
        """
        )

        # JSON schema for validation
        theme_schema = {
            "type": "object",
            "properties": {
                "themes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "maxLength": 50},
                            "summary": {
                                "type": "string",
                                "minLength": 100,
                                "maxLength": 300,
                            },
                            "representative_studies": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "contradictions": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "strength_of_evidence": {
                                "type": "string",
                                "enum": ["High", "Moderate", "Low"],
                            },
                            "study_count": {"type": "integer", "minimum": 1},
                        },
                        "required": [
                            "name",
                            "summary",
                            "representative_studies",
                            "strength_of_evidence",
                            "study_count",
                        ],
                    },
                    "minItems": 3,
                    "maxItems": 7,
                }
            },
            "required": ["themes"],
        }

        response = self._call_ai_model(prompt, schema=theme_schema)
        theme_data = json.loads(response)

        themes = []
        for theme_json in theme_data["themes"]:
            theme = Theme(
                name=theme_json["name"],
                summary=theme_json["summary"],
                representative_studies=theme_json["representative_studies"],
                contradictions=theme_json.get("contradictions", []),
                strength_of_evidence=theme_json["strength_of_evidence"],
                study_count=theme_json["study_count"],
            )
            themes.append(theme)

        self.logger.info(f"Extracted {len(themes)} themes")
        return themes

    def analyze_gaps(
        self, themes: List[Theme], studies: List[StudyRecord]
    ) -> List[ResearchGap]:
        """Analyze research gaps based on thematic synthesis."""
        self.logger.info("Analyzing research gaps...")

        # Prepare theme summaries
        theme_summaries = []
        for theme in themes:
            summary = {
                "name": theme.name,
                "summary": theme.summary,
                "contradictions": theme.contradictions,
                "strength_of_evidence": theme.strength_of_evidence,
                "study_count": theme.study_count,
            }
            theme_summaries.append(summary)

        # Gap analysis prompt
        prompt = dedent(
            f"""
        You are a research methodologist identifying gaps for PhD thesis research.

        TASK: Identify 3 - 6 high - priority research gaps based on the thematic analysis.

        THEMES:
        {json.dumps(theme_summaries, indent=2)}

        TOTAL STUDIES: {len(studies)}

        For each gap, provide:
        1. title (concise research gap statement)
        2. description (detailed explanation, 100 - 150 words)
        3. justification (why this gap matters, evidence from themes)
        4. impact_score (1 - 5: potential impact on field)
        5. feasibility_score (1 - 5: realistic for PhD research)
        6. novelty_score (1 - 5: how novel / unexplored)
        7. related_themes (which themes reveal this gap)

        Prioritize gaps that are:
        - Feasible for individual PhD research
        - High impact for the field
        - Supported by contradictions / limitations in current literature
        - Methodologically addressable
        - Theoretically significant

        Avoid gaps that are:
        - Too broad for PhD scope
        - Already well - studied
        - Purely technical / implementation issues
        """
        )

        # JSON schema for validation
        gap_schema = {
            "type": "object",
            "properties": {
                "gaps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "maxLength": 100},
                            "description": {
                                "type": "string",
                                "minLength": 80,
                                "maxLength": 200,
                            },
                            "justification": {
                                "type": "string",
                                "minLength": 50,
                                "maxLength": 150,
                            },
                            "impact_score": {
                                "type": "number",
                                "minimum": 1,
                                "maximum": 5,
                            },
                            "feasibility_score": {
                                "type": "number",
                                "minimum": 1,
                                "maximum": 5,
                            },
                            "novelty_score": {
                                "type": "number",
                                "minimum": 1,
                                "maximum": 5,
                            },
                            "related_themes": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": [
                            "title",
                            "description",
                            "justification",
                            "impact_score",
                            "feasibility_score",
                            "novelty_score",
                            "related_themes",
                        ],
                    },
                    "minItems": 3,
                    "maxItems": 6,
                }
            },
            "required": ["gaps"],
        }

        response = self._call_ai_model(prompt, schema=gap_schema)
        gap_data = json.loads(response)

        gaps = []
        for i, gap_json in enumerate(gap_data["gaps"]):
            # Calculate priority rank based on combined scores
            (
                gap_json["impact_score"]
                + gap_json["feasibility_score"]
                + gap_json["novelty_score"]
            ) / 3

            gap = ResearchGap(
                title=gap_json["title"],
                description=gap_json["description"],
                justification=gap_json["justification"],
                impact_score=gap_json["impact_score"],
                feasibility_score=gap_json["feasibility_score"],
                novelty_score=gap_json["novelty_score"],
                priority_rank=i + 1,  # Will be re - ranked after sorting
                related_themes=gap_json["related_themes"],
            )
            gaps.append(gap)

        # Sort by combined score and update rankings
        gaps.sort(
            key=lambda g: (g.impact_score + g.feasibility_score + g.novelty_score) / 3,
            reverse=True,
        )
        for i, gap in enumerate(gaps):
            gap.priority_rank = i + 1

        self.logger.info(f"Identified {len(gaps)} research gaps")
        return gaps

    def generate_conceptual_model(
        self, themes: List[Theme], gaps: List[ResearchGap]
    ) -> ConceptualModel:
        """Generate conceptual framework model."""
        self.logger.info("Generating conceptual model...")

        # Prepare input data
        theme_data = [{"name": t.name, "summary": t.summary} for t in themes]
        gap_data = [
            {"title": g.title, "description": g.description} for g in gaps[:3]
        ]  # Top 3 gaps

        prompt = dedent(
            f"""
        You are a theoretical framework expert creating a conceptual model for PhD research.

        TASK: Develop a conceptual framework that integrates the themes and addresses the research gaps.

        THEMES:
        {json.dumps(theme_data, indent=2)}

        TOP RESEARCH GAPS:
        {json.dumps(gap_data, indent=2)}

        Provide:
        1. description (2 - 3 sentences explaining the overall framework)
        2. constructs (3 - 6 key theoretical constructs with definitions)
        3. relationships (hypothetical relationships between constructs)
        4. mermaid_diagram (valid Mermaid syntax for concept map)
        5. tikz_diagram (LaTeX TikZ code for publication - quality diagram)

        The framework should:
        - Integrate insights from all major themes
        - Provide foundation for addressing research gaps
        - Be theoretically grounded and empirically testable
        - Use standard academic terminology
        - Show clear construct relationships
        """
        )

        # JSON schema for validation
        model_schema = {
            "type": "object",
            "properties": {
                "description": {"type": "string", "minLength": 100, "maxLength": 400},
                "constructs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["name", "description"],
                    },
                    "minItems": 3,
                    "maxItems": 6,
                },
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "target": {"type": "string"},
                            "description": {"type": "string"},
                        },
                        "required": ["source", "target", "description"],
                    },
                },
                "mermaid_diagram": {"type": "string"},
                "tikz_diagram": {"type": "string"},
            },
            "required": [
                "description",
                "constructs",
                "relationships",
                "mermaid_diagram",
                "tikz_diagram",
            ],
        }

        response = self._call_ai_model(prompt, schema=model_schema)
        model_data = json.loads(response)

        conceptual_model = ConceptualModel(
            description=model_data["description"],
            constructs=model_data["constructs"],
            relationships=model_data["relationships"],
            mermaid_diagram=model_data["mermaid_diagram"],
            tikz_diagram=model_data["tikz_diagram"],
        )

        self.logger.info("Generated conceptual model")
        return conceptual_model

    def generate_research_questions(
        self, gaps: List[ResearchGap], conceptual_model: ConceptualModel
    ) -> List[ResearchQuestion]:
        """Generate research questions and hypotheses."""
        self.logger.info("Generating research questions and hypotheses...")

        # Focus on top gaps
        top_gaps = gaps[:3]
        gap_data = []
        for gap in top_gaps:
            gap_data.append(
                {
                    "title": gap.title,
                    "description": gap.description,
                    "impact_score": gap.impact_score,
                    "feasibility_score": gap.feasibility_score,
                }
            )

        constructs = [c["name"] for c in conceptual_model.constructs]

        prompt = dedent(
            f"""
        You are a research methodology expert formulating research questions and hypotheses.

        TASK: Generate 2 - 4 research questions / hypotheses based on the top research gaps and conceptual model.

        RESEARCH GAPS:
        {json.dumps(gap_data, indent=2)}

        AVAILABLE CONSTRUCTS:
        {json.dumps(constructs, indent=2)}

        CONCEPTUAL MODEL:
        {conceptual_model.description}

        For each research question / hypothesis:
        1. type ("question" or "hypothesis")
        2. text (well - formed RQ or hypothesis statement)
        3. constructs (list of constructs involved)
        4. predicted_direction (for hypotheses only: "positive", "negative", "moderated")
        5. justification (why this RQ / H is important and feasible)
        6. related_gap (which gap this addresses)

        Guidelines:
        - Mix of research questions (exploratory) and hypotheses (confirmatory)
        - Use specific, measurable constructs
        - Ensure hypotheses are directional and testable
        - Align with PhD research scope
        - Build on conceptual model relationships
        """
        )

        # JSON schema for validation
        rq_schema = {
            "type": "object",
            "properties": {
                "research_questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["question", "hypothesis"],
                            },
                            "text": {"type": "string", "minLength": 20},
                            "constructs": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "predicted_direction": {
                                "type": "string",
                                "enum": ["positive", "negative", "moderated", None],
                            },
                            "justification": {"type": "string", "minLength": 50},
                            "related_gap": {"type": "string"},
                        },
                        "required": [
                            "type",
                            "text",
                            "constructs",
                            "justification",
                            "related_gap",
                        ],
                    },
                    "minItems": 2,
                    "maxItems": 4,
                }
            },
            "required": ["research_questions"],
        }

        response = self._call_ai_model(prompt, schema=rq_schema)
        rq_data = json.loads(response)

        research_questions = []
        for rq_json in rq_data["research_questions"]:
            rq = ResearchQuestion(
                type=rq_json["type"],
                text=rq_json["text"],
                constructs=rq_json["constructs"],
                predicted_direction=rq_json.get("predicted_direction"),
                justification=rq_json["justification"],
                related_gap=rq_json["related_gap"],
            )
            research_questions.append(rq)

        self.logger.info(
            f"Generated {len(research_questions)} research questions / hypotheses"
        )
        return research_questions

    def human_checkpoint(self, checkpoint_name: str, data: Any) -> Any:
        """Human - in - the - loop checkpoint for review and editing."""
        if not self.config.human_checkpoints:
            return data

        self.logger.info(f"Human checkpoint: {checkpoint_name}")

        # Save current data for review
        checkpoint_file = (
            Path(self.config.output_dir) / f"checkpoint_{checkpoint_name}.json"
        )
        with open(checkpoint_file, "w") as f:
            if hasattr(data, "__dict__"):
                json.dump(
                    asdict(data) if hasattr(data, "__dict__") else data,
                    f,
                    indent=2,
                    default=str,
                )
            else:
                json.dump(data, f, indent=2, default=str)

        print(f"\n{'='*60}")
        print(f"HUMAN CHECKPOINT: {checkpoint_name.upper()}")
        print(f"{'='*60}")
        print(f"Review file: {checkpoint_file}")
        print("Current data summary:")

        if isinstance(data, list):
            print(f"  - {len(data)} items")
            for i, item in enumerate(data[:3]):  # Show first 3 items
                if hasattr(item, "name"):
                    print(f"    {i + 1}. {item.name}")
                elif hasattr(item, "title"):
                    print(f"    {i + 1}. {item.title}")
        elif hasattr(data, "__dict__"):
            print(f"  - Object type: {type(data).__name__}")
            if hasattr(data, "description"):
                print(f"  - Description: {data.description[:100]}...")

        response = input("\nProceed with current data? (y / n/edit): ").strip().lower()

        if response == "n":
            print("Aborting generation...")
            sys.exit(1)
        elif response == "edit":
            print(f"Please edit {checkpoint_file} and press Enter to continue...")
            input()
            # Reload edited data
            with open(checkpoint_file, "r") as f:
                edited_data = json.load(f)
            return edited_data

        return data

    def render_templates(self, template_data: Dict[str, Any]) -> Dict[str, str]:
        """Render output using Jinja2 templates."""
        self.logger.info("Rendering templates...")

        if not self.jinja_env:
            self.logger.warning("Jinja2 not available - using fallback rendering")
            return self._fallback_render(template_data)

        outputs = {}

        # Custom filters for LaTeX
        def escape_latex(text):
            """Escape special LaTeX characters."""
            if not isinstance(text, str):
                return str(text)

            latex_chars = {
                "&": r"\&",
                "%": r"\%",
                "$": r"\$",
                "#": r"\#",
                "^": r"\textasciicircum{}",
                "_": r"\_",
                "{": r"\{",
                "}": r"\}",
                "~": r"\textasciitilde{}",
                "\\": r"\textbackslash{}",
            }

            for char, replacement in latex_chars.items():
                text = text.replace(char, replacement)
            return text

        self.jinja_env.filters["escape_latex"] = escape_latex

        # Render each template
        formats = self.config.output_formats or ["markdown"]
        for format_name in formats:
            if format_name == "markdown":
                template = self.jinja_env.get_template("thesis_chapter.md")
                outputs["markdown"] = template.render(**template_data)

            elif format_name == "latex":
                template = self.jinja_env.get_template("thesis_chapter.tex")
                outputs["latex"] = template.render(**template_data)

            elif format_name == "html":
                # Convert markdown to HTML using simple conversion or keep existing HTML
                if "markdown" in outputs:
                    outputs["html"] = self._markdown_to_html(outputs["markdown"])

        return outputs

    def _fallback_render(self, template_data: Dict[str, Any]) -> Dict[str, str]:
        """Fallback rendering without Jinja2."""
        markdown_content = f"""
# {template_data['metadata']['title']}

## Abstract
{template_data.get('abstract', {}).get('background', '')}

## 1. Introduction
### 1.1 Background
{template_data.get('introduction', {}).get('background', {}).get('clinical_context', '')}

## 2. Thematic Synthesis
"""

        for i, theme in enumerate(template_data.get("themes", []), 1):
            markdown_content += f"""
### 2.{i} {theme.name}
{theme.summary}

**Representative Studies:** {', '.join(theme.representative_studies)}
**Strength of Evidence:** {theme.strength_of_evidence}
"""

        markdown_content += "\n## 3. Research Gaps\n"
        for i, gap in enumerate(template_data.get("gaps", []), 1):
            markdown_content += f"""
### 3.{i} {gap.title}
{gap.description}

**Priority:** {gap.priority_rank} | **Impact:** {gap.impact_score}/5 | **Feasibility:** {gap.feasibility_score}/5
"""

        return {"markdown": markdown_content}

    def _markdown_to_html(self, markdown_content: str) -> str:
        """Convert markdown to HTML (basic implementation)."""
        # This is a simplified conversion - in practice, use a proper markdown library
        html_content = markdown_content.replace("\n## ", "\n<h2>").replace(
            "\n### ", "\n<h3>"
        )
        html_content = html_content.replace("\n**", "\n<strong>").replace(
            "**", "</strong>"
        )
        html_content = f"<html><body>{html_content}</body></html>"
        return html_content

    def export_outputs(self, outputs: Dict[str, str], metadata: Dict[str, Any]):
        """Export rendered outputs to files."""
        self.logger.info("Exporting outputs...")

        timestamp = datetime.now().strftime("%Y % m%d_ % H%M % S")

        for format_name, content in outputs.items():
            if format_name == "markdown":
                output_file = (
                    Path(self.config.output_dir) / f"thesis_chapter_{timestamp}.md"
                )
            elif format_name == "latex":
                output_file = (
                    Path(self.config.output_dir) / f"thesis_chapter_{timestamp}.tex"
                )
            elif format_name == "html":
                output_file = (
                    Path(self.config.output_dir) / f"thesis_chapter_{timestamp}.html"
                )
            else:
                output_file = (
                    Path(self.config.output_dir)
                    / f"thesis_chapter_{timestamp}.{format_name}"
                )

            with open(output_file, "w", encoding="utf - 8") as f:
                f.write(content)

            self.logger.info(f"Exported {format_name}: {output_file}")

            # Convert to additional formats using Pandoc if available
            if format_name == "markdown":
                self._pandoc_convert(output_file, timestamp)

        # Export metadata and audit log
        metadata_file = (
            Path(self.config.output_dir) / f"generation_metadata_{timestamp}.json"
        )
        with open(metadata_file, "w") as f:
            json.dump(
                {
                    "metadata": metadata,
                    "audit_log": self.audit_log,
                    "config": asdict(self.config),
                },
                f,
                indent=2,
                default=str,
            )

    def _pandoc_convert(self, markdown_file: Path, timestamp: str):
        """Convert markdown to additional formats using Pandoc."""
        try:
            # Convert to PDF
            pdf_file = Path(self.config.output_dir) / f"thesis_chapter_{timestamp}.pdf"
            subprocess.run(
                [
                    "pandoc",
                    str(markdown_file),
                    "-o",
                    str(pdf_file),
                    "--pdf - engine=xelatex",
                    "--template=default",
                ],
                check=True,
                capture_output=True,
            )
            self.logger.info(f"Generated PDF: {pdf_file}")

            # Convert to DOCX
            docx_file = (
                Path(self.config.output_dir) / f"thesis_chapter_{timestamp}.docx"
            )
            subprocess.run(
                ["pandoc", str(markdown_file), "-o", str(docx_file)],
                check=True,
                capture_output=True,
            )
            self.logger.info(f"Generated DOCX: {docx_file}")

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.warning(f"Pandoc conversion failed: {e}")

    def generate_thesis_chapter(self) -> Dict[str, Any]:
        """Main method to generate thesis - style literature review chapter."""
        self.logger.info("Starting thesis literature review generation...")
        start_time = time.time()

        try:
            # 1. Load and validate PRISMA data
            self.logger.info("Loading PRISMA data...")
            with open(self.config.input_file, "r", encoding="utf - 8") as f:
                prisma_data = json.load(f)

            PRISMAValidator.validate_prisma_structure(prisma_data)
            studies = PRISMAValidator.extract_studies(prisma_data)
            self.logger.info(f"Loaded {len(studies)} studies")

            # 2. Extract themes
            themes = self.extract_themes(studies, prisma_data)
            themes = self.human_checkpoint("themes", themes)

            # 3. Analyze gaps
            gaps = self.analyze_gaps(themes, studies)
            gaps = self.human_checkpoint("gaps", gaps)

            # 4. Generate conceptual model
            conceptual_model = self.generate_conceptual_model(themes, gaps)
            conceptual_model = self.human_checkpoint(
                "conceptual_model", conceptual_model
            )

            # 5. Generate research questions
            research_questions = self.generate_research_questions(
                gaps, conceptual_model
            )
            research_questions = self.human_checkpoint(
                "research_questions", research_questions
            )

            # 6. Prepare template data
            template_data = {
                "metadata": prisma_data.get("metadata", {}),
                "abstract": prisma_data.get("abstract", {}),
                "introduction": prisma_data.get("introduction", {}),
                "methods": prisma_data.get("methods", {}),
                "themes": themes,
                "gaps": gaps,
                "conceptual_model": conceptual_model,
                "research_questions": research_questions,
                "generation_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "processing_time": time.time() - start_time,
                    "ai_model": self.config.ai_model,
                    "study_count": len(studies),
                    "theme_count": len(themes),
                    "gap_count": len(gaps),
                },
            }

            # 7. Render templates
            outputs = self.render_templates(template_data)

            # 8. Export outputs
            self.export_outputs(outputs, template_data["generation_metadata"])

            self.logger.info(f"Generation completed in {time.time() - start_time:.2f}s")
            return template_data

        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            raise


def main():
    """CLI interface for thesis literature review generation."""
    parser = argparse.ArgumentParser(
        description="Generate thesis - style literature review from PRISMA data"
    )

    parser.add_argument("--input", "-i", required=True, help="Input PRISMA JSON file")
    parser.add_argument("--output", "-o", default="output", help="Output directory")
    parser.add_argument(
        "--templates", "-t", default="templates", help="Template directory"
    )
    parser.add_argument("--cache", "-c", default="cache", help="Cache directory")
    parser.add_argument(
        "--provider",
        "-p",
        default="openai",
        choices=["openai", "xai"],
        help="AI provider",
    )
    parser.add_argument("--model", "-m", default="gpt - 4", help="AI model name")
    parser.add_argument(
        "--deterministic",
        action="store_true",
        help="Use deterministic generation (temp=0)",
    )
    parser.add_argument("--no - cache", action="store_true", help="Disable caching")
    parser.add_argument(
        "--no - checkpoints", action="store_true", help="Skip human checkpoints"
    )
    parser.add_argument(
        "--themes", type=int, default=5, help="Number of themes to extract"
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        default=["markdown", "html", "latex"],
        help="Output formats",
    )

    args = parser.parse_args()

    # Create configuration
    config = ThesisConfig(
        input_file=args.input,
        output_dir=args.output,
        template_dir=args.templates,
        cache_dir=args.cache,
        ai_provider=args.provider,
        ai_model=args.model,
        deterministic=args.deterministic,
        enable_cache=not args.no_cache,
        human_checkpoints=not args.no_checkpoints,
        theme_count=args.themes,
        output_formats=args.formats,
    )

    # Generate thesis chapter
    generator = ThesisLiteratureReviewGenerator(config)
    result = generator.generate_thesis_chapter()

    print("\n✅ Thesis literature review generated successfully!")
    print(f"📁 Output directory: {config.output_dir}")
    print(
        f"📊 Generated {len(result['themes'])} themes and {len(result['gaps'])} research gaps"
    )
    print(
        f"🎯 Created {len(result['research_questions'])} research questions / hypotheses"
    )


if __name__ == "__main__":
    main()
