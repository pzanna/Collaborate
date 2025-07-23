# Thesis Generation System Documentation

## Overview

The Eunice Thesis Generation System transforms PRISMA systematic review data into PhD-quality literature review chapters. The system provides both basic and enhanced generation capabilities with support for multiple output formats.

## Architecture

```plaintext
src/thesis/
├── __init__.py                 # Main module exports
├── generators/                 # Core generation engines
│   ├── __init__.py
│   ├── enhanced_thesis_generator.py  # Full-featured AI-powered generator
│   └── basic_thesis_generator.py     # Simplified generation engine
├── converters/                 # Format conversion utilities
│   ├── __init__.py
│   └── latex_converter.py            # LaTeX document generation
├── config/                     # Configuration management
│   ├── __init__.py
│   └── thesis_config.yaml            # Main configuration file
└── setup_thesis.py            # Dependency management and setup
```

## Features

### Enhanced Thesis Generator

- **AI Integration**: Uses OpenAI GPT-4 for intelligent theme extraction and gap analysis
- **Deterministic Caching**: SHA-256 based caching for reproducible outputs (temp=0, top_p=1)
- **Template System**: Jinja2 templates for consistent academic formatting
- **Multiple Formats**: Markdown, LaTeX, HTML output with Pandoc integration
- **Human Checkpoints**: Interactive review points for quality control
- **Research Questions**: Automatic generation of testable hypotheses
- **Conceptual Frameworks**: Visual diagrams and theoretical models

### Output Formats

1. **Markdown**: Clean, readable format for review and editing
2. **LaTeX**: Publication-ready academic documents with proper formatting
3. **HTML**: Web-friendly format for online sharing
4. **PDF/DOCX**: Via Pandoc conversion (requires system installation)

## Quick Start

### 1. Setup and Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Check system dependencies and setup
python thesis_cli.py --setup

# Install optional dependencies (macOS)
brew install pandoc
brew install --cask mactex
```

### 2. Basic Usage

```bash
# Generate thesis chapter from PRISMA data
python thesis_cli.py tests/literature/comprehensive_literature_review.json

# Use custom configuration
python thesis_cli.py data/review.json -c src/thesis/config/thesis_config.yaml

# Generate specific formats only
python thesis_cli.py data/review.json --formats markdown latex

# Skip human checkpoints for automation
python thesis_cli.py data/review.json --no-checkpoints
```

### 3. Advanced Usage

```python
# Programmatic usage
from src.thesis import EnhancedThesisGenerator

generator = EnhancedThesisGenerator('src/thesis/config/thesis_config.yaml')
result = generator.generate_enhanced_thesis_chapter('data/review.json')
print(f"Generated {len(result['themes'])} themes and {len(result['gaps'])} gaps")
```

## Configuration

The system uses YAML configuration files for customization:

```yaml
# AI Configuration
ai:
  provider: openai
  model: gpt-4
  temperature: 0.0        # Deterministic generation
  max_tokens: 4000

# Output Configuration  
output:
  formats: [markdown, latex, html]
  directory: thesis_output
  include_cache: true

# Processing Configuration
processing:
  use_cache: true
  human_checkpoints: true
  theme_count: 5
  max_gaps: 5
```

## Input Data Format

The system expects PRISMA systematic review data in JSON format:

```json
{
  "metadata": {
    "title": "Machine Learning in Healthcare Diagnosis",
    "authors": ["Dr. Smith", "Dr. Jones"]
  },
  "data_extraction_tables": {
    "table_1_study_characteristics": {
      "data": [
        {
          "study": "Author et al. 2023",
          "design": "RCT", 
          "sample_size": "1000",
          "outcomes": "Diagnostic accuracy"
        }
      ]
    }
  },
  "discussion": {
    "limitations": "...",
    "conclusions": "..."
  }
}
```

## Output Structure

Generated outputs include:

1. **Thesis Chapter** (`.md`, `.tex`, `.html`)
   - Abstract and introduction
   - Thematic synthesis (5 themes)
   - Research gaps analysis (up to 5 gaps)
   - Conceptual framework with diagrams
   - Research questions and hypotheses
   - Academic conclusions

2. **Metadata** (`.json`)
   - Generation parameters
   - Processing statistics
   - Audit log of AI calls
   - Configuration snapshot

3. **Checkpoints** (`.json`) - if enabled
   - Intermediate results for review
   - Allows manual editing and continuation

## Examples

### Generated Themes

- "Diagnostic Accuracy of Machine Learning" (High evidence strength)
- "Real-world Implementation Challenges" (Moderate evidence strength)
- "Regulatory and Ethical Considerations" (High evidence strength)

### Research Gaps

- "Bias Assessment and Mitigation Strategies" (Priority: 4.3/5.0)
- "Long-term Clinical Outcomes Studies" (Priority: 4.1/5.0)
- "Standardized Evaluation Frameworks" (Priority: 4.2/5.0)

### Research Questions

- "How can bias mitigation strategies improve ML diagnostic equity?"
- Hypothesis: "Implementing bias-aware training will reduce diagnostic disparities by 25%"

## Troubleshooting

### Common Issues

1. **Missing Dependencies**

   ```bash
   python thesis_cli.py --setup  # Check and install
   ```

2. **AI API Errors**

   ```bash
   export OPENAI_API_KEY="your-key-here"
   ```

3. **Template Errors**
   - Ensure Jinja2 is installed: `pip install jinja2>=3.1.0`
   - Check template directory exists: `templates/thesis/`

4. **LaTeX Compilation Issues**
   - Install TeX Live: `brew install --cask mactex` (macOS)
   - Check special character escaping in LaTeX output

### Performance Tips

- Use caching for repeated generations (enabled by default)
- Skip checkpoints for batch processing (`--no-checkpoints`)
- Limit theme count in config for faster processing
- Use basic generator for simple use cases

## Integration with Eunice

The thesis generation system integrates seamlessly with the main Eunice research assistant:

- Uses existing AI client infrastructure
- Leverages Eunice's literature analysis capabilities  
- Shares configuration and logging systems
- Compatible with MCP server architecture

## Development

### Adding New Generators

1. Create new generator in `src/thesis/generators/`
2. Inherit from base generator class
3. Implement required methods: `extract_themes()`, `identify_gaps()`, etc.
4. Add to `__init__.py` exports

### Custom Templates

1. Create templates in `templates/thesis/`
2. Use Jinja2 syntax with academic formatting
3. Add custom filters in generator setup
4. Test with different data sets

### Testing

```bash
# Run thesis generation tests
python -m pytest tests/thesis/

# Test with sample data
python thesis_cli.py tests/literature/comprehensive_literature_review.json --no-checkpoints
```

## Support and Contributions

- **Documentation**: See `docs/` directory for detailed specifications
- **Issues**: Report bugs and feature requests via GitHub issues
- **Development**: Follow existing code patterns and include tests
- **Configuration**: Extend YAML configs for new features

---

*Last updated: July 23, 2025*
*Version: 1.0.0*
