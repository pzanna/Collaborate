#!/usr / bin / env python3
"""
Enhanced Thesis Literature Review Generator
==========================================

Production - ready thesis generator with templates, configuration, and full LaTeX support.
Integrates with existing Eunice AI system and provides comprehensive output options.

Features:
- YAML configuration system
- Jinja2 templates for consistent output
- Deterministic AI generation with caching
- LaTeX, Markdown, and HTML output
- Pandoc integration for multiple formats
- Human - in - the - loop checkpoints
- Comprehensive audit logging
- Research question generation
- Publication - ready formatting

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

import yaml

# Add Eunice modules to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import dependencies
try:
    import jinja2
    from jinja2 import Environment, FileSystemLoader

    JINJA_AVAILABLE = True
except ImportError:
    JINJA_AVAILABLE = False

try:
    from src.ai_clients.openai_client import AIProviderConfig, OpenAIClient

    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


@dataclass
class ThesisTheme:
    """Thesis literature review theme."""

    name: str
    summary: str
    studies: List[str]
    strength: str
    contradictions: Optional[List[str]] = None

    def __post_init__(self):
        if self.contradictions is None:
            self.contradictions = []


@dataclass
class ResearchGap:
    """Research gap for PhD thesis."""

    title: str
    description: str
    justification: str
    impact: float
    feasibility: float
    novelty: float
    themes: Optional[List[str]] = None
    priority_score: float = 0.0

    def __post_init__(self):
        if self.themes is None:
            self.themes = []
        if self.priority_score == 0.0:
            self.priority_score = (self.impact + self.feasibility + self.novelty) / 3


@dataclass
class ConceptualFramework:
    """Conceptual framework for thesis research."""

    description: str
    constructs: List[Dict[str, str]]
    relationships: List[Dict[str, str]]
    diagram_mermaid: str
    diagram_latex: str = ""


@dataclass
class ResearchQuestion:
    """Research question or hypothesis."""

    type: str  # 'question' or 'hypothesis'
    text: str
    constructs: List[str]
    related_gap: str
    justification: str
    predicted_direction: Optional[str] = None


class EnhancedThesisGenerator:
    """Enhanced thesis generator with templates and configuration."""

    def __init__(self, config_file: Optional[str] = None):
        self.config = self._load_config(config_file)
        self.logger = self._setup_logging()
        self.cache = self._setup_cache()
        self.jinja_env = self._setup_templates()
        self.ai_client = self._setup_ai_client()
        self.audit_log = []

        # Create output directory
        Path(self.config["output"]["directory"]).mkdir(parents=True, exist_ok=True)

    def _load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if config_file and Path(config_file).exists():
            with open(config_file, "r") as f:
                return yaml.safe_load(f)

        # Default configuration
        return {
            "ai": {
                "provider": "openai",
                "model": "gpt - 4",
                "deterministic": True,
                "temperature": 0.0,
                "max_tokens": 4000,
            },
            "output": {"formats": ["markdown", "latex", "html"], "directory": "thesis_output", "include_cache": True},
            "processing": {
                "use_cache": True,
                "cache_version": "v1.0",
                "human_checkpoints": True,
                "theme_count": 5,
                "max_gaps": 5,
            },
            "templates": {"directory": "templates / thesis"},
        }

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger("enhanced_thesis_generator")
        logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # File handler - use logs directory
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "thesis_generation.log")
        file_handler.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def _setup_cache(self):
        """Setup caching system."""
        if not self.config["processing"]["use_cache"]:
            return None

        cache_dir = Path(self.config["output"]["directory"]) / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        class SimpleCache:
            def __init__(self, cache_dir):
                self.cache_file = cache_dir / "enhanced_cache.json"
                self.cache = self._load()

            def _load(self):
                if self.cache_file.exists():
                    try:
                        with open(self.cache_file, "r") as f:
                            return json.load(f)
                    except Exception:
                        return {}
                return {}

            def _save(self):
                with open(self.cache_file, "w") as f:
                    json.dump(self.cache, f, indent=2)

            def get(self, key):
                return self.cache.get(key)

            def set(self, key, value):
                self.cache[key] = {"value": value, "timestamp": datetime.now().isoformat()}
                self._save()

        return SimpleCache(cache_dir)

    def _setup_templates(self):
        """Setup Jinja2 template environment."""
        if not JINJA_AVAILABLE:
            self.logger.warning("Jinja2 not available - using fallback rendering")
            return None

        template_dir = Path(self.config["templates"]["directory"])
        if not template_dir.exists():
            self.logger.warning(f"Template directory not found: {template_dir}")
            return None

        try:
            from jinja2 import Environment, FileSystemLoader

            env = Environment(loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)
        except ImportError:
            self.logger.warning("Jinja2 import failed")
            return None

        # Add custom filters
        env.filters["round"] = lambda x, precision=2: round(float(x), precision)

        return env

    def _setup_ai_client(self):
        """Setup AI client."""
        provider = self.config["ai"]["provider"]

        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable required")

            try:
                # Try Eunice client first
                from src.ai_clients.openai_client import AIProviderConfig, OpenAIClient

                config = AIProviderConfig(
                    provider="openai",
                    model=self.config["ai"]["model"],
                    temperature=self.config["ai"]["temperature"],
                    max_tokens=self.config["ai"]["max_tokens"],
                )
                return OpenAIClient(api_key, config)

            except ImportError:
                # Fallback to direct OpenAI
                import openai

                class DirectOpenAIClient:
                    def __init__(self, api_key, model, temperature, max_tokens):
                        self.client = openai.OpenAI(api_key=api_key)
                        self.model = model
                        self.temperature = temperature
                        self.max_tokens = max_tokens

                    def get_response(self, user_message, system_prompt=None):
                        messages = []
                        if system_prompt:
                            messages.append({"role": "system", "content": system_prompt})
                        messages.append({"role": "user", "content": user_message})

                        response = self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            temperature=self.temperature,
                            max_tokens=self.max_tokens,
                        )

                        return response.choices[0].message.content or ""

                return DirectOpenAIClient(
                    api_key,
                    self.config["ai"]["model"],
                    self.config["ai"]["temperature"],
                    self.config["ai"]["max_tokens"],
                )
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")

    def call_ai(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call AI model with caching."""
        # Generate cache key
        cache_key = hashlib.sha256(f"{prompt}|{system_prompt or ''}".encode()).hexdigest()

        # Check cache
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                self.logger.info("Using cached AI response")
                return cached["value"]

        # Call AI
        start_time = time.time()
        try:
            response = self.ai_client.get_response(prompt, system_prompt)
            duration = time.time() - start_time

            # Cache response
            if self.cache:
                self.cache.set(cache_key, response)

            # Log
            self.audit_log.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "operation": "ai_call",
                    "model": self.config["ai"]["model"],
                    "duration": duration,
                    "prompt_hash": cache_key[:16],
                    "response_length": len(response),
                }
            )

            self.logger.info(f"AI call completed in {duration:.2f}s")
            return response

        except Exception as e:
            self.logger.error(f"AI call failed: {e}")
            raise

    def extract_themes(self, prisma_data: Dict[str, Any]) -> List[ThesisTheme]:
        """Extract themes using AI with structured output."""
        self.logger.info("Extracting themes for thesis literature review...")

        # Prepare data
        studies = prisma_data["data_extraction_tables"]["table_1_study_characteristics"]["data"]
        study_summaries = []

        for study in studies[:15]:  # Limit for prompt length
            study_summaries.append(
                {
                    "id": study.get("study", "Unknown"),
                    "design": study.get("design", ""),
                    "sample_size": study.get("sample_size", ""),
                    "outcomes": study.get("outcomes", ""),
                    "effect_summary": study.get("effect_summary", ""),
                }
            )

        # Enhanced prompt for thesis - level analysis
        prompt = f"""
You are a PhD researcher conducting thematic synthesis for a literature review chapter.

TASK: Extract {self.config['processing']['theme_count']} distinct, high - level themes suitable for a PhD thesis literature review.

STUDY DATA:
{json.dumps(study_summaries, indent=2)}

DISCUSSION CONTENT:
{json.dumps(prisma_data.get('discussion', {}), indent=2)}

Respond with JSON in this exact format:
{{
  "themes": [
    {{
      "name": "Theme Name (academic, 4 - 8 words)",
      "summary": "Comprehensive academic summary (200 - 300 words, PhD - level analysis)",
      "studies": ["study1", "study2", "study3"],
      "strength": "High|Moderate|Low",
      "contradictions": ["any contradictory findings"]
    }}
  ]
}}

Requirements for themes:
- Academic rigor suitable for PhD thesis
- Theoretical depth and clinical significance
- Clear identification of knowledge contributions
- Recognition of limitations and contradictions
- Integration across multiple studies
- Forward - looking implications for research

Focus on:
- Theoretical frameworks and conceptual advances
- Methodological innovations and limitations
- Clinical and practical implications
- Policy and implementation considerations
- Knowledge gaps and future research directions

Ensure themes are:
- Mutually exclusive yet collectively exhaustive
- Grounded in empirical evidence
- Theoretically sophisticated
- Practically relevant
"""

        system_prompt = """You are an expert in systematic reviews and academic writing.
Provide only valid JSON that strictly follows the requested schema.
Focus on creating themes suitable for PhD - level literature review."""

        try:
            response = self.call_ai(prompt, system_prompt)
            theme_data = json.loads(response)

            themes = []
            for theme_json in theme_data.get("themes", []):
                theme = ThesisTheme(
                    name=theme_json.get("name", ""),
                    summary=theme_json.get("summary", ""),
                    studies=theme_json.get("studies", []),
                    strength=theme_json.get("strength", "Moderate"),
                    contradictions=theme_json.get("contradictions", []),
                )
                themes.append(theme)

            self.logger.info(f"Extracted {len(themes)} themes")
            return themes

        except Exception as e:
            self.logger.error(f"Theme extraction failed: {e}")
            raise

    def identify_gaps(self, themes: List[ThesisTheme], prisma_data: Dict) -> List[ResearchGap]:
        """Identify research gaps for PhD research."""
        self.logger.info("Identifying research gaps for PhD thesis...")

        theme_data = []
        for theme in themes:
            theme_data.append(
                {
                    "name": theme.name,
                    "summary": theme.summary,
                    "strength": theme.strength,
                    "contradictions": theme.contradictions,
                }
            )

        prompt = f"""
You are a PhD supervisor identifying research gaps for doctoral research.

TASK: Identify {self.config['processing']['max_gaps']} high - priority research gaps suitable for PhD thesis research.

THEMES:
{json.dumps(theme_data, indent=2)}

Respond with JSON in this exact format:
{{
  "gaps": [
    {{
      "title": "Research Gap Title (specific, actionable)",
      "description": "Detailed description (150 - 200 words, PhD scope)",
      "justification": "Evidence - based justification (100 - 150 words)",
      "impact": 4.2,
      "feasibility": 3.8,
      "novelty": 4.5,
      "themes": ["related theme names"]
    }}
  ]
}}

Scoring criteria (1 - 5 scale):
- Impact: Potential contribution to field and clinical practice
- Feasibility: Realistic for 3 - 4 year PhD timeline with available resources
- Novelty: Originality and theoretical advancement potential

Prioritize gaps that are:
- Theoretically significant and methodologically addressable
- Feasible within PhD constraints (time, resources, ethics)
- High impact for academic and clinical communities
- Novel enough for substantial contribution
- Supported by limitations in current literature
- Aligned with emerging technological / clinical trends

Each gap should:
- Build directly on identified themes and contradictions
- Specify the knowledge contribution
- Consider methodological approaches
- Address practical implementation
- Connect to broader theoretical frameworks
"""

        system_prompt = """You are an expert in research methodology and PhD supervision.
Provide only valid JSON. Focus on gaps that are realistic for individual PhD research
while maintaining high academic standards and potential impact."""

        try:
            response = self.call_ai(prompt, system_prompt)
            gap_data = json.loads(response)

            gaps = []
            for gap_json in gap_data.get("gaps", []):
                gap = ResearchGap(
                    title=gap_json.get("title", ""),
                    description=gap_json.get("description", ""),
                    justification=gap_json.get("justification", ""),
                    impact=float(gap_json.get("impact", 3.0)),
                    feasibility=float(gap_json.get("feasibility", 3.0)),
                    novelty=float(gap_json.get("novelty", 3.0)),
                    themes=gap_json.get("themes", []),
                )
                gaps.append(gap)

            # Sort by priority score
            gaps.sort(key=lambda g: g.priority_score, reverse=True)

            self.logger.info(f"Identified {len(gaps)} research gaps")
            return gaps

        except Exception as e:
            self.logger.error(f"Gap identification failed: {e}")
            raise

    def create_framework(self, themes: List[ThesisTheme], gaps: List[ResearchGap]) -> ConceptualFramework:
        """Create conceptual framework."""
        self.logger.info("Creating conceptual framework...")

        theme_data = [{"name": t.name, "summary": t.summary[:150]} for t in themes]
        gap_data = [{"title": g.title, "description": g.description[:150]} for g in gaps[:3]]

        prompt = f"""
You are a theoretical framework expert creating a conceptual model for PhD research.

TASK: Develop a sophisticated conceptual framework that integrates the themes and provides foundation for addressing research gaps.

THEMES:
{json.dumps(theme_data, indent=2)}

PRIORITY GAPS:
{json.dumps(gap_data, indent=2)}

Respond with JSON in this exact format:
{{
  "description": "Framework overview (2 - 3 sentences, academic tone)",
  "constructs": [
    {{
      "name": "Construct Name",
      "description": "Theoretical definition and explanation"
    }}
  ],
  "relationships": [
    {{
      "source": "Construct A",
      "target": "Construct B",
      "description": "Nature and direction of relationship"
    }}
  ],
  "diagram_mermaid": "graph TD\\n  A[Construct A] --> B[Construct B]\\n  B --> C[Construct C]"
}}

Requirements:
- 4 - 6 key theoretical constructs
- Clear, testable relationships
- Integration of all major themes
- Foundation for addressing research gaps
- Theoretically grounded in existing literature
- Empirically addressable through research

The framework should:
- Synthesize insights from thematic analysis
- Provide conceptual foundation for empirical research
- Enable hypothesis generation and testing
- Consider both theoretical and practical dimensions
- Account for implementation and outcome variables
"""

        try:
            response = self.call_ai(prompt)
            framework_data = json.loads(response)

            framework = ConceptualFramework(
                description=framework_data.get("description", ""),
                constructs=framework_data.get("constructs", []),
                relationships=framework_data.get("relationships", []),
                diagram_mermaid=framework_data.get("diagram_mermaid", ""),
                diagram_latex="",  # Can be generated separately
            )

            self.logger.info("Conceptual framework created")
            return framework

        except Exception as e:
            self.logger.error(f"Framework creation failed: {e}")
            raise

    def generate_research_questions(
        self, gaps: List[ResearchGap], framework: ConceptualFramework
    ) -> List[ResearchQuestion]:
        """Generate research questions and hypotheses."""
        self.logger.info("Generating research questions and hypotheses...")

        top_gaps = gaps[:3]  # Focus on highest priority gaps
        gap_data = []
        for gap in top_gaps:
            gap_data.append({"title": gap.title, "description": gap.description, "priority_score": gap.priority_score})

        constructs = [c["name"] for c in framework.constructs]

        prompt = f"""
You are a research methodology expert formulating research questions and hypotheses for PhD research.

TASK: Generate 2 - 4 research questions and hypotheses based on the highest priority research gaps.

TOP RESEARCH GAPS:
{json.dumps(gap_data, indent=2)}

CONCEPTUAL FRAMEWORK:
Description: {framework.description}
Available Constructs: {constructs}

Respond with JSON in this exact format:
{{
  "research_questions": [
    {{
      "type": "question",
      "text": "Well - formed research question",
      "constructs": ["construct1", "construct2"],
      "related_gap": "gap title",
      "justification": "Why this question is important and feasible",
      "predicted_direction": null
    }},
    {{
      "type": "hypothesis",
      "text": "Testable hypothesis statement",
      "constructs": ["construct1", "construct2"],
      "related_gap": "gap title",
      "justification": "Theoretical basis and expected contribution",
      "predicted_direction": "positive|negative|moderated"
    }}
  ]
}}

Requirements:
- Mix of exploratory questions and confirmatory hypotheses
- Aligned with PhD research scope and timeline
- Theoretically grounded in conceptual framework
- Methodologically feasible and ethically acceptable
- Clear contribution to knowledge and practice
- Specific, measurable, and testable

Each question / hypothesis should:
- Address a specific research gap
- Use precise constructs from the framework
- Be answerable within PhD constraints
- Contribute to theory and practice
- Build toward coherent research program
"""

        try:
            response = self.call_ai(prompt)
            rq_data = json.loads(response)

            research_questions = []
            for rq_json in rq_data.get("research_questions", []):
                rq = ResearchQuestion(
                    type=rq_json.get("type", "question"),
                    text=rq_json.get("text", ""),
                    constructs=rq_json.get("constructs", []),
                    related_gap=rq_json.get("related_gap", ""),
                    justification=rq_json.get("justification", ""),
                    predicted_direction=rq_json.get("predicted_direction"),
                )
                research_questions.append(rq)

            self.logger.info(f"Generated {len(research_questions)} research questions / hypotheses")
            return research_questions

        except Exception as e:
            self.logger.error(f"Research question generation failed: {e}")
            raise

    def human_checkpoint(self, name: str, data: Any) -> Any:
        """Human review checkpoint."""
        if not self.config["processing"]["human_checkpoints"]:
            return data

        # Ensure output directory exists
        output_dir = Path(self.config["output"]["directory"])
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save checkpoint
        checkpoint_file = output_dir / f"checkpoint_{name}.json"
        with open(checkpoint_file, "w") as f:
            if isinstance(data, list):
                json.dump([asdict(item) for item in data], f, indent=2, default=str)
            else:
                json.dump(asdict(data) if hasattr(data, "__dict__") else data, f, indent=2, default=str)

        print(f"\n{'='*60}")
        print(f"CHECKPOINT: {name.upper()}")
        print(f"{'='*60}")
        print(f"Review: {checkpoint_file}")

        if isinstance(data, list):
            print(f"Items: {len(data)}")
            for i, item in enumerate(data[:3]):
                if hasattr(item, "name"):
                    print(f"  {i + 1}. {item.name}")
                elif hasattr(item, "title"):
                    print(f"  {i + 1}. {item.title}")

        response = input("Continue? (y / n/edit): ").strip().lower()

        if response == "n":
            print("Aborting...")
            sys.exit(1)
        elif response == "edit":
            print(f"Edit {checkpoint_file} and press Enter...")
            input()
            # Reload
            with open(checkpoint_file, "r") as f:
                return json.load(f)

        return data

    def render_outputs(self, template_data: Dict[str, Any]) -> Dict[str, str]:
        """Render outputs using templates."""
        self.logger.info("Rendering thesis chapter outputs...")

        outputs = {}

        if self.jinja_env:
            try:
                # Markdown
                if "markdown" in self.config["output"]["formats"]:
                    template = self.jinja_env.get_template("chapter.md.j2")
                    outputs["markdown"] = template.render(**template_data)

                # LaTeX (if template exists)
                if "latex" in self.config["output"]["formats"]:
                    try:
                        template = self.jinja_env.get_template("chapter.tex.j2")
                        outputs["latex"] = template.render(**template_data)
                    except Exception:
                        self.logger.info("LaTeX template not found, generating programmatically")
                        outputs["latex"] = self._generate_latex_fallback(template_data)

                # HTML (if template exists)
                if "html" in self.config["output"]["formats"]:
                    try:
                        template = self.jinja_env.get_template("chapter.html.j2")
                        outputs["html"] = template.render(**template_data)
                    except Exception:
                        self.logger.info("HTML template not found, converting from markdown")
                        if "markdown" in outputs:
                            outputs["html"] = self._markdown_to_html(outputs["markdown"])

            except Exception as e:
                self.logger.error(f"Template rendering failed: {e}")
                outputs["markdown"] = self._generate_markdown_fallback(template_data)
        else:
            # Fallback without templates
            outputs["markdown"] = self._generate_markdown_fallback(template_data)

        return outputs

    def _generate_markdown_fallback(self, data: Dict[str, Any]) -> str:
        """Generate markdown without templates."""
        themes = data.get("themes", [])
        gaps = data.get("gaps", [])
        framework = data.get("framework", {})

        md = f"""# Literature Review

## Abstract

This literature review synthesizes evidence from machine learning applications in healthcare diagnosis, identifying key themes and research opportunities for future investigation.

## 1. Introduction

### 1.1 Background

Healthcare diagnosis remains a critical challenge where machine learning technologies show significant promise for improving accuracy and efficiency.

## 2. Thematic Synthesis

"""

        for i, theme in enumerate(themes, 1):
            theme_name = theme.get("name", f"Theme {i}") if isinstance(theme, dict) else theme.name
            theme_summary = theme.get("summary", "") if isinstance(theme, dict) else theme.summary
            theme_strength = theme.get("strength", "Moderate") if isinstance(theme, dict) else theme.strength

            md += f"""### 2.{i} {theme_name}

{theme_summary}

**Strength of Evidence:** {theme_strength}

"""

        md += "## 3. Research Gaps\n\n"

        for i, gap in enumerate(gaps, 1):
            gap_title = gap.get("title", f"Gap {i}") if isinstance(gap, dict) else gap.title
            gap_description = gap.get("description", "") if isinstance(gap, dict) else gap.description
            gap_score = gap.get("priority_score", 0.0) if isinstance(gap, dict) else gap.priority_score

            md += f"""### 3.{i} {gap_title}

{gap_description}

**Priority Score:** {gap_score:.2f}/5.0

"""

        if framework:
            framework_description = (
                framework.get("description", "") if isinstance(framework, dict) else framework.description
            )
            framework_diagram = (
                framework.get("diagram_mermaid", "") if isinstance(framework, dict) else framework.diagram_mermaid
            )

            md += f"""## 4. Conceptual Framework

{framework_description}

```mermaid
{framework_diagram}
```

"""

        md += f"""## 5. Conclusion

This literature review has identified {len(themes)} major themes and {len(gaps)} research gaps, providing a foundation for future PhD research in machine learning applications for healthcare diagnosis.

---
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return md

    def _generate_latex_fallback(self, data: Dict[str, Any]) -> str:
        """Generate LaTeX fallback."""
        # Use the existing LaTeX generator
        from ..converters.latex_converter import generate_latex_document

        return generate_latex_document(data)

    def _markdown_to_html(self, markdown: str) -> str:
        """Convert markdown to HTML."""
        # Simple conversion
        html = markdown.replace("# ", "<h1>").replace("\n", "</h1>\n", 1)
        html = html.replace("## ", "<h2>").replace("\n", "</h2>\n")
        html = html.replace("### ", "<h3>").replace("\n", "</h3>\n")
        html = html.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
        return f"<html><body>{html}</body></html>"

    def save_outputs(self, outputs: Dict[str, str], metadata: Dict[str, Any]):
        """Save all outputs."""
        timestamp = datetime.now().strftime("%Y % m%d_ % H%M % S")
        output_dir = Path(self.config["output"]["directory"])

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []

        # Save each format
        for format_name, content in outputs.items():
            if format_name == "markdown":
                output_file = output_dir / f"enhanced_thesis_chapter_{timestamp}.md"
            elif format_name == "latex":
                output_file = output_dir / f"enhanced_thesis_chapter_{timestamp}.tex"
            elif format_name == "html":
                output_file = output_dir / f"enhanced_thesis_chapter_{timestamp}.html"
            else:
                output_file = output_dir / f"enhanced_thesis_chapter_{timestamp}.{format_name}"

            with open(output_file, "w", encoding="utf - 8") as f:
                f.write(content)

            saved_files.append(output_file)
            self.logger.info(f"Saved {format_name}: {output_file}")

        # Save metadata
        metadata_file = output_dir / f"enhanced_metadata_{timestamp}.json"
        with open(metadata_file, "w") as f:
            json.dump(
                {"metadata": metadata, "audit_log": self.audit_log, "config": self.config}, f, indent=2, default=str
            )

        saved_files.append(metadata_file)

        # Try Pandoc conversions
        if "markdown" in outputs:
            md_file = [f for f in saved_files if f.suffix == ".md"][0]
            self._try_pandoc_conversion(md_file, timestamp)

        return saved_files

    def _try_pandoc_conversion(self, md_file: Path, timestamp: str):
        """Convert using Pandoc if available."""
        try:
            output_dir = md_file.parent

            # PDF
            pdf_file = output_dir / f"enhanced_thesis_chapter_{timestamp}.pdf"
            subprocess.run(
                ["pandoc", str(md_file), "-o", str(pdf_file), "--pdf - engine=xelatex"], check=True, capture_output=True
            )
            self.logger.info(f"Generated PDF: {pdf_file}")

            # DOCX
            docx_file = output_dir / f"enhanced_thesis_chapter_{timestamp}.docx"
            subprocess.run(["pandoc", str(md_file), "-o", str(docx_file)], check=True, capture_output=True)
            self.logger.info(f"Generated DOCX: {docx_file}")

        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.info("Pandoc not available - install for additional format conversions")

    def generate_enhanced_thesis_chapter(self, input_file: str) -> Dict[str, Any]:
        """Main generation workflow."""
        self.logger.info("Starting enhanced thesis literature review generation")
        start_time = time.time()

        try:
            # Load PRISMA data
            self.logger.info(f"Loading PRISMA data from {input_file}")
            with open(input_file, "r") as f:
                prisma_data = json.load(f)

            # Extract themes
            themes = self.extract_themes(prisma_data)
            themes = self.human_checkpoint("themes", themes)

            # Identify gaps
            gaps = self.identify_gaps(themes, prisma_data)
            gaps = self.human_checkpoint("gaps", gaps)

            # Create framework
            framework = self.create_framework(themes, gaps)
            framework = self.human_checkpoint("framework", framework)

            # Generate research questions
            research_questions = self.generate_research_questions(gaps, framework)
            research_questions = self.human_checkpoint("research_questions", research_questions)

            # Prepare template data
            template_data = {
                "metadata": {
                    "title": prisma_data.get("metadata", {}).get("title", "Literature Review"),
                    "authors": prisma_data.get("metadata", {}).get("authors", []),
                    "generated_date": datetime.now().strftime("%Y-%m-%d"),
                },
                "abstract": prisma_data.get("abstract", {}),
                "introduction": prisma_data.get("introduction", {}),
                "methods": prisma_data.get("methods", {}),
                "themes": [asdict(theme) for theme in themes],
                "gaps": [asdict(gap) for gap in gaps],
                "framework": asdict(framework),
                "research_questions": [asdict(rq) for rq in research_questions],
                "generation_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "processing_time": time.time() - start_time,
                    "ai_model": self.config["ai"]["model"],
                    "study_count": len(
                        prisma_data.get("data_extraction_tables", {})
                        .get("table_1_study_characteristics", {})
                        .get("data", [])
                    ),
                    "theme_count": len(themes),
                    "gap_count": len(gaps),
                },
            }

            # Render outputs
            outputs = self.render_outputs(template_data)

            # Save outputs
            saved_files = self.save_outputs(outputs, template_data["generation_metadata"])

            duration = time.time() - start_time
            self.logger.info(f"Enhanced thesis chapter generation completed in {duration:.2f}s")

            return {
                "themes": themes,
                "gaps": gaps,
                "framework": framework,
                "research_questions": research_questions,
                "outputs": outputs,
                "saved_files": saved_files,
                "duration": duration,
            }

        except Exception as e:
            self.logger.error(f"Enhanced generation failed: {e}")
            raise


def main():
    """CLI interface for enhanced thesis generator."""
    parser = argparse.ArgumentParser(description="Enhanced thesis literature review generator")

    parser.add_argument("input", help="Input PRISMA JSON file")
    parser.add_argument("-c", "--config", help="Configuration YAML file")
    parser.add_argument("-o", "--output", help="Output directory")
    parser.add_argument("--no - checkpoints", action="store_true", help="Skip human checkpoints")
    parser.add_argument("--formats", nargs="+", choices=["markdown", "latex", "html"], help="Output formats")

    args = parser.parse_args()

    # Create generator
    generator = EnhancedThesisGenerator(args.config)

    # Override config with CLI args
    if args.output:
        generator.config["output"]["directory"] = args.output
    if args.no_checkpoints:
        generator.config["processing"]["human_checkpoints"] = False
    if args.formats:
        generator.config["output"]["formats"] = args.formats

    # Generate
    result = generator.generate_enhanced_thesis_chapter(args.input)

    print(f"\n✅ Enhanced thesis chapter generated successfully!")
    print(f"📁 Output: {generator.config['output']['directory']}")
    print(
        f"📊 {len(result['themes'])} themes, {len(result['gaps'])} gaps, {len(result['research_questions'])} research questions"
    )
    print(f"📄 Formats: {list(result['outputs'].keys())}")
    print(f"⏱️  Duration: {result['duration']:.1f}s")


if __name__ == "__main__":
    main()
