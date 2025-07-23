#!/usr/bin/env python3
"""
Thesis-Style Literature Review Generator
========================================

A simplified implementation that transforms PRISMA systematic review outputs 
into PhD thesis-quality literature review chapters.

This version integrates with the existing Eunice AI system and provides:
- Local AI model integration with your existing clients
- Deterministic generation with caching
- PRISMA JSON parsing and thematic synthesis
- Research gap analysis and conceptual modeling
- Markdown/LaTeX output with Jinja2 templates
- Human-in-the-loop checkpoints

Author: GitHub Copilot for Paul Zanna
Date: July 23, 2025
"""

import argparse
import json
import os
import sys
import hashlib
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from textwrap import dedent
import subprocess

# Add Eunice modules to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import dependencies
try:
    from src.ai_clients.openai_client import OpenAIClient, AIProviderConfig
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# Optional dependencies
try:
    import jinja2
    from jinja2 import Environment, FileSystemLoader
    JINJA_AVAILABLE = True
except ImportError:
    JINJA_AVAILABLE = False
    print("Warning: Jinja2 not available. Install with: pip install jinja2")

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("Warning: PyYAML not available. Install with: pip install PyYAML")


@dataclass
class ThemeResult:
    """Theme extracted from literature synthesis."""
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
    """Research gap identified from literature."""
    title: str
    description: str
    justification: str
    impact: float
    feasibility: float
    novelty: float
    themes: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.themes is None:
            self.themes = []


@dataclass
class ConceptualFramework:
    """Conceptual framework for thesis research."""
    description: str
    constructs: List[Dict[str, str]]
    relationships: List[Dict[str, str]]
    diagram_mermaid: str
    diagram_latex: str = ""


class SimpleCache:
    """Simple file-based cache for AI responses."""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "ai_cache.json"
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, str]:
        """Load cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Save cache to file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")
    
    def get_key(self, prompt: str, model: str) -> str:
        """Generate cache key."""
        return hashlib.sha256(f"{prompt}|{model}".encode()).hexdigest()
    
    def get(self, prompt: str, model: str) -> Optional[str]:
        """Get cached response."""
        key = self.get_key(prompt, model)
        return self.cache.get(key)
    
    def set(self, prompt: str, model: str, response: str):
        """Cache response."""
        key = self.get_key(prompt, model)
        self.cache[key] = response
        self._save_cache()


class ThesisGenerator:
    """Main thesis literature review generator."""
    
    def __init__(self, 
                 input_file: str,
                 output_dir: str,
                 ai_provider: str = "openai",
                 ai_model: str = "gpt-4",
                 deterministic: bool = True,
                 use_cache: bool = True,
                 human_checkpoints: bool = True):
        
        self.input_file = input_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.ai_provider = ai_provider
        self.ai_model = ai_model
        self.deterministic = deterministic
        self.use_cache = use_cache
        self.human_checkpoints = human_checkpoints
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Setup AI client
        self.ai_client = self._setup_ai_client()
        
        # Setup cache
        self.cache = SimpleCache(str(self.output_dir / "cache")) if use_cache else None
        
        # Audit trail
        self.audit_log = []
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging."""
        logger = logging.getLogger("thesis_generator")
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler(self.output_dir / "thesis_generation.log")
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def _setup_ai_client(self):
        """Setup AI client."""
        if self.ai_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable required")
            
            try:
                # Try to import and create client
                from src.ai_clients.openai_client import OpenAIClient, AIProviderConfig
                
                config = AIProviderConfig(
                    provider="openai",
                    model=self.ai_model,
                    temperature=0.0 if self.deterministic else 0.7,
                    max_tokens=4000
                )
                
                return OpenAIClient(api_key, config)
                
            except ImportError:
                # Fallback: create a simple client wrapper
                self.logger.warning("Using fallback OpenAI client")
                return self._create_fallback_client(api_key)
        else:
            raise ValueError(f"Unsupported AI provider: {self.ai_provider}")
    
    def _create_fallback_client(self, api_key: str):
        """Create a simple fallback OpenAI client."""
        try:
            import openai
            
            class FallbackClient:
                def __init__(self, api_key, model, deterministic):
                    self.client = openai.OpenAI(api_key=api_key)
                    self.model = model
                    self.deterministic = deterministic
                
                def get_response(self, user_message: str, system_prompt: Optional[str] = None) -> str:
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": user_message})
                    
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=0.0 if self.deterministic else 0.7,
                        max_tokens=4000
                    )
                    
                    content = response.choices[0].message.content
                    return content or ""
            
            return FallbackClient(api_key, self.ai_model, self.deterministic)
            
        except ImportError:
            raise RuntimeError("OpenAI client not available. Install with: pip install openai")
    
    def call_ai(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call AI model with caching."""
        # Check cache
        if self.cache:
            cached = self.cache.get(prompt, self.ai_model)
            if cached:
                self.logger.info("Using cached AI response")
                return cached
        
        # Prepare system prompt for JSON output
        if not system_prompt:
            system_prompt = "You are a research assistant. Respond with valid JSON only."
        
        # Call AI
        start_time = time.time()
        try:
            response = self.ai_client.get_response(prompt, system_prompt)
            duration = time.time() - start_time
            
            # Cache response
            if self.cache:
                self.cache.set(prompt, self.ai_model, response)
            
            # Log
            self.audit_log.append({
                "timestamp": datetime.now().isoformat(),
                "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
                "model": self.ai_model,
                "duration": duration,
                "response_length": len(response)
            })
            
            self.logger.info(f"AI call completed in {duration:.2f}s")
            return response
            
        except Exception as e:
            self.logger.error(f"AI call failed: {e}")
            raise
    
    def load_prisma_data(self) -> Dict[str, Any]:
        """Load and validate PRISMA JSON data."""
        self.logger.info(f"Loading PRISMA data from {self.input_file}")
        
        with open(self.input_file, 'r') as f:
            data = json.load(f)
        
        # Basic validation
        required_sections = ["metadata", "results", "data_extraction_tables"]
        for section in required_sections:
            if section not in data:
                raise ValueError(f"Missing required section: {section}")
        
        self.logger.info("PRISMA data loaded successfully")
        return data
    
    def extract_themes(self, prisma_data: Dict[str, Any]) -> List[ThemeResult]:
        """Extract themes from the systematic review."""
        self.logger.info("Extracting themes...")
        
        # Prepare study data
        studies_table = prisma_data["data_extraction_tables"]["table_1_study_characteristics"]
        study_summaries = []
        
        for study in studies_table["data"]:
            summary = {
                "id": study.get("study", "Unknown"),
                "design": study.get("design", ""),
                "sample_size": study.get("sample_size", ""),
                "outcomes": study.get("outcomes", ""),
                "effect_summary": study.get("effect_summary", "")
            }
            study_summaries.append(summary)
        
        # Prepare narrative content
        discussion = prisma_data.get("discussion", {})
        results = prisma_data.get("results", {})
        
        prompt = f"""
Extract 4-6 major themes from this systematic review data for a PhD thesis literature review.

STUDIES:
{json.dumps(study_summaries[:10], indent=2)}

DISCUSSION POINTS:
{json.dumps(discussion, indent=2)}

RESULTS SUMMARY:
{json.dumps(results.get("summary", {}), indent=2)}

Respond with JSON in this format:
{{
  "themes": [
    {{
      "name": "Theme Name (max 8 words)",
      "summary": "Detailed summary (150-200 words, academic tone)",
      "studies": ["study1", "study2"],
      "strength": "High|Moderate|Low",
      "contradictions": ["any contradictory findings"]
    }}
  ]
}}

Focus on:
- Clinical significance
- Methodological patterns
- Theoretical implications
- Knowledge gaps
- Contradictions in findings

Ensure themes are mutually exclusive and collectively exhaustive.
"""
        
        try:
            response = self.call_ai(prompt)
            theme_data = json.loads(response)
            
            themes = []
            for theme_json in theme_data.get("themes", []):
                theme = ThemeResult(
                    name=theme_json.get("name", ""),
                    summary=theme_json.get("summary", ""),
                    studies=theme_json.get("studies", []),
                    strength=theme_json.get("strength", "Moderate"),
                    contradictions=theme_json.get("contradictions", [])
                )
                themes.append(theme)
            
            self.logger.info(f"Extracted {len(themes)} themes")
            return themes
            
        except Exception as e:
            self.logger.error(f"Theme extraction failed: {e}")
            raise
    
    def identify_gaps(self, themes: List[ThemeResult], prisma_data: Dict[str, Any]) -> List[ResearchGap]:
        """Identify research gaps."""
        self.logger.info("Identifying research gaps...")
        
        theme_summaries = []
        for theme in themes:
            theme_summaries.append({
                "name": theme.name,
                "summary": theme.summary,
                "strength": theme.strength,
                "contradictions": theme.contradictions
            })
        
        study_count = len(prisma_data["data_extraction_tables"]["table_1_study_characteristics"]["data"])
        
        prompt = f"""
Identify 3-5 high-priority research gaps for PhD thesis research based on this thematic analysis.

THEMES:
{json.dumps(theme_summaries, indent=2)}

TOTAL STUDIES: {study_count}

Respond with JSON in this format:
{{
  "gaps": [
    {{
      "title": "Gap title (concise)",
      "description": "Detailed description (100-150 words)",
      "justification": "Why this gap matters (evidence from themes)",
      "impact": 4.2,
      "feasibility": 3.8,
      "novelty": 4.5,
      "themes": ["related theme names"]
    }}
  ]
}}

Scoring (1-5 scale):
- Impact: Potential contribution to field
- Feasibility: Realistic for PhD research
- Novelty: How unexplored this area is

Prioritize gaps that are:
- Feasible for individual PhD research (2-4 years)
- High impact for the field
- Supported by limitations/contradictions in literature
- Methodologically addressable
- Theoretically significant
"""
        
        try:
            response = self.call_ai(prompt)
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
                    themes=gap_json.get("themes", [])
                )
                gaps.append(gap)
            
            # Sort by combined score
            gaps.sort(key=lambda g: g.impact + g.feasibility + g.novelty, reverse=True)
            
            self.logger.info(f"Identified {len(gaps)} research gaps")
            return gaps
            
        except Exception as e:
            self.logger.error(f"Gap analysis failed: {e}")
            raise
    
    def create_conceptual_framework(self, themes: List[ThemeResult], gaps: List[ResearchGap]) -> ConceptualFramework:
        """Create conceptual framework."""
        self.logger.info("Creating conceptual framework...")
        
        theme_data = [{"name": t.name, "summary": t.summary[:100]} for t in themes]
        gap_data = [{"title": g.title, "description": g.description[:100]} for g in gaps[:3]]
        
        prompt = f"""
Create a conceptual framework for PhD research that integrates these themes and addresses the research gaps.

THEMES:
{json.dumps(theme_data, indent=2)}

TOP GAPS:
{json.dumps(gap_data, indent=2)}

Respond with JSON in this format:
{{
  "description": "2-3 sentence framework overview",
  "constructs": [
    {{
      "name": "Construct Name",
      "description": "Definition and explanation"
    }}
  ],
  "relationships": [
    {{
      "source": "Construct A",
      "target": "Construct B", 
      "description": "Nature of relationship"
    }}
  ],
  "diagram_mermaid": "graph TD\\n  A[Construct A] --> B[Construct B]\\n  B --> C[Construct C]"
}}

Create:
- 3-5 key theoretical constructs
- Clear relationships between constructs
- Framework that addresses the research gaps
- Mermaid diagram syntax for visualization
"""
        
        try:
            response = self.call_ai(prompt)
            framework_data = json.loads(response)
            
            framework = ConceptualFramework(
                description=framework_data.get("description", ""),
                constructs=framework_data.get("constructs", []),
                relationships=framework_data.get("relationships", []),
                diagram_mermaid=framework_data.get("diagram_mermaid", ""),
                diagram_latex=""  # Can be added later
            )
            
            self.logger.info("Conceptual framework created")
            return framework
            
        except Exception as e:
            self.logger.error(f"Framework creation failed: {e}")
            raise
    
    def human_checkpoint(self, name: str, data: Any) -> Any:
        """Human checkpoint for review."""
        if not self.human_checkpoints:
            return data
        
        # Save checkpoint data
        checkpoint_file = self.output_dir / f"checkpoint_{name}.json"
        with open(checkpoint_file, 'w') as f:
            if hasattr(data, '__dict__'):
                json.dump([asdict(item) for item in data] if isinstance(data, list) else asdict(data), 
                         f, indent=2, default=str)
            else:
                json.dump(data, f, indent=2, default=str)
        
        print(f"\n{'='*50}")
        print(f"CHECKPOINT: {name.upper()}")
        print(f"{'='*50}")
        print(f"Review: {checkpoint_file}")
        
        if isinstance(data, list):
            print(f"Items: {len(data)}")
            for i, item in enumerate(data[:3]):
                if hasattr(item, 'name'):
                    print(f"  {i+1}. {item.name}")
                elif hasattr(item, 'title'):
                    print(f"  {i+1}. {item.title}")
        
        response = input("Continue? (y/n/edit): ").strip().lower()
        
        if response == 'n':
            print("Stopping...")
            exit(1)
        elif response == 'edit':
            print(f"Edit {checkpoint_file} and press Enter...")
            input()
            # Reload edited data
            with open(checkpoint_file, 'r') as f:
                return json.load(f)
        
        return data
    
    def generate_markdown(self, 
                         themes: List[ThemeResult], 
                         gaps: List[ResearchGap], 
                         framework: ConceptualFramework,
                         prisma_data: Dict[str, Any]) -> str:
        """Generate markdown thesis chapter."""
        self.logger.info("Generating markdown...")
        
        metadata = prisma_data.get("metadata", {})
        abstract = prisma_data.get("abstract", {})
        intro = prisma_data.get("introduction", {})
        
        markdown = f"""# Literature Review

## Abstract

{abstract.get('background', '')}

{abstract.get('objectives', '')}

## 1. Introduction

### 1.1 Background and Context

{intro.get('background', {}).get('clinical_context', '')}

### 1.2 Rationale

**Knowledge Gap:** {intro.get('rationale', {}).get('knowledge_gap', '')}

**Clinical Importance:** {intro.get('rationale', {}).get('clinical_importance', '')}

## 2. Thematic Synthesis

"""
        
        for i, theme in enumerate(themes, 1):
            markdown += f"""### 2.{i} {theme.name}

{theme.summary}

**Representative Studies:** {', '.join(theme.studies)}  
**Strength of Evidence:** {theme.strength}

"""
            if theme.contradictions:
                markdown += f"**Contradictory Findings:** {'; '.join(theme.contradictions)}\n\n"
        
        markdown += """## 3. Research Gaps and Opportunities

"""
        
        for i, gap in enumerate(gaps, 1):
            markdown += f"""### 3.{i} {gap.title}

{gap.description}

**Justification:** {gap.justification}

**Scores:** Impact: {gap.impact:.1f}/5 | Feasibility: {gap.feasibility:.1f}/5 | Novelty: {gap.novelty:.1f}/5

"""
        
        markdown += f"""## 4. Conceptual Framework

{framework.description}

```mermaid
{framework.diagram_mermaid}
```

### 4.1 Key Constructs

"""
        
        for construct in framework.constructs:
            markdown += f"**{construct['name']}:** {construct['description']}\n\n"
        
        markdown += """### 4.2 Theoretical Relationships

"""
        
        for rel in framework.relationships:
            markdown += f"- {rel['source']} → {rel['target']}: {rel['description']}\n"
        
        markdown += f"""

## 5. Summary and Research Direction

This literature review has identified {len(themes)} major themes and {len(gaps)} significant research gaps. 
The proposed conceptual framework provides a foundation for addressing these gaps through systematic empirical research.

The highest priority research opportunities focus on {gaps[0].title.lower() if gaps else 'identified gaps'}, 
which offers both high impact potential and feasible implementation within a PhD research timeline.

---

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*  
*Model: {self.ai_model}*  
*Deterministic: {self.deterministic}*
"""
        
        return markdown
    
    def save_outputs(self, markdown: str, themes: List[ThemeResult], gaps: List[ResearchGap], framework: ConceptualFramework):
        """Save all outputs."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save markdown
        md_file = self.output_dir / f"thesis_chapter_{timestamp}.md"
        with open(md_file, 'w') as f:
            f.write(markdown)
        
        # Save structured data
        data_file = self.output_dir / f"thesis_data_{timestamp}.json"
        with open(data_file, 'w') as f:
            json.dump({
                "themes": [asdict(theme) for theme in themes],
                "gaps": [asdict(gap) for gap in gaps],
                "framework": asdict(framework),
                "metadata": {
                    "generated": datetime.now().isoformat(),
                    "model": self.ai_model,
                    "deterministic": self.deterministic
                },
                "audit_log": self.audit_log
            }, f, indent=2, default=str)
        
        # Try Pandoc conversion
        self._try_pandoc_conversion(md_file, timestamp)
        
        self.logger.info(f"Outputs saved:")
        self.logger.info(f"  Markdown: {md_file}")
        self.logger.info(f"  Data: {data_file}")
    
    def _try_pandoc_conversion(self, md_file: Path, timestamp: str):
        """Try converting to other formats with Pandoc."""
        try:
            # PDF
            pdf_file = self.output_dir / f"thesis_chapter_{timestamp}.pdf"
            subprocess.run([
                "pandoc", str(md_file), "-o", str(pdf_file)
            ], check=True, capture_output=True)
            self.logger.info(f"  PDF: {pdf_file}")
            
            # DOCX
            docx_file = self.output_dir / f"thesis_chapter_{timestamp}.docx"
            subprocess.run([
                "pandoc", str(md_file), "-o", str(docx_file)
            ], check=True, capture_output=True)
            self.logger.info(f"  DOCX: {docx_file}")
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.info("  Pandoc not available - install for PDF/DOCX output")
    
    def generate_thesis_chapter(self) -> Dict[str, Any]:
        """Main generation workflow."""
        self.logger.info("Starting thesis literature review generation")
        start_time = time.time()
        
        try:
            # 1. Load data
            prisma_data = self.load_prisma_data()
            
            # 2. Extract themes
            themes = self.extract_themes(prisma_data)
            themes = self.human_checkpoint("themes", themes)
            
            # 3. Identify gaps  
            gaps = self.identify_gaps(themes, prisma_data)
            gaps = self.human_checkpoint("gaps", gaps)
            
            # 4. Create framework
            framework = self.create_conceptual_framework(themes, gaps)
            framework = self.human_checkpoint("framework", framework)
            
            # 5. Generate markdown
            markdown = self.generate_markdown(themes, gaps, framework, prisma_data)
            
            # 6. Save outputs
            self.save_outputs(markdown, themes, gaps, framework)
            
            duration = time.time() - start_time
            self.logger.info(f"Generation completed in {duration:.2f}s")
            
            return {
                "themes": themes,
                "gaps": gaps,
                "framework": framework,
                "markdown": markdown,
                "duration": duration
            }
            
        except Exception as e:
            self.logger.error(f"Generation failed: {e}")
            raise


def main():
    """CLI interface."""
    parser = argparse.ArgumentParser(description="Generate thesis literature review from PRISMA data")
    
    parser.add_argument("input", help="Input PRISMA JSON file")
    parser.add_argument("-o", "--output", default="thesis_output", help="Output directory")
    parser.add_argument("-p", "--provider", default="openai", choices=["openai"], help="AI provider")
    parser.add_argument("-m", "--model", default="gpt-4", help="AI model")
    parser.add_argument("--no-deterministic", action="store_true", help="Disable deterministic mode")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    parser.add_argument("--no-checkpoints", action="store_true", help="Skip human checkpoints")
    
    args = parser.parse_args()
    
    # Create generator
    generator = ThesisGenerator(
        input_file=args.input,
        output_dir=args.output,
        ai_provider=args.provider,
        ai_model=args.model,
        deterministic=not args.no_deterministic,
        use_cache=not args.no_cache,
        human_checkpoints=not args.no_checkpoints
    )
    
    # Generate
    result = generator.generate_thesis_chapter()
    
    print(f"\n✅ Thesis chapter generated successfully!")
    print(f"📁 Output: {args.output}")
    print(f"📊 {len(result['themes'])} themes, {len(result['gaps'])} gaps")
    print(f"⏱️  Duration: {result['duration']:.1f}s")


if __name__ == "__main__":
    main()
