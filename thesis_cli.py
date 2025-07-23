#!/usr/bin/env python3
"""
Eunice Thesis Generator CLI
===========================

Command-line interface for the Eunice thesis generation system.
This script provides easy access to both basic and enhanced thesis generation capabilities.

Usage:
    python thesis_cli.py <input_file> [options]

Author: GitHub Copilot for Paul Zanna
Date: July 23, 2025
"""

import sys
import argparse
from pathlib import Path

# Add source directory to path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.thesis.generators.enhanced_thesis_generator import EnhancedThesisGenerator


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Eunice Thesis Generator - Transform PRISMA reviews into thesis chapters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage with default settings
    python thesis_cli.py data/review.json
    
    # Enhanced generation with custom config
    python thesis_cli.py data/review.json -c src/thesis/config/thesis_config.yaml
    
    # Generate only specific formats
    python thesis_cli.py data/review.json --formats markdown latex
    
    # Skip human checkpoints for automated processing
    python thesis_cli.py data/review.json --no-checkpoints
    
    # Custom output directory
    python thesis_cli.py data/review.json -o my_thesis_output
        """
    )
    
    parser.add_argument(
        'input', 
        nargs='?',  # Make input optional
        help="Input PRISMA JSON file containing systematic review data"
    )
    parser.add_argument(
        '-c', '--config', 
        help="Configuration YAML file (default: src/thesis/config/thesis_config.yaml)"
    )
    parser.add_argument(
        '-o', '--output', 
        help="Output directory (default: thesis_output)"
    )
    parser.add_argument(
        '--formats', 
        nargs='+', 
        choices=['markdown', 'latex', 'html'], 
        help="Output formats to generate (default: all)"
    )
    parser.add_argument(
        '--no-checkpoints', 
        action='store_true', 
        help="Skip human review checkpoints for automated processing"
    )
    parser.add_argument(
        '--basic', 
        action='store_true', 
        help="Use basic thesis generator instead of enhanced version"
    )
    parser.add_argument(
        '--setup', 
        action='store_true', 
        help="Run dependency check and setup"
    )
    parser.add_argument(
        '--version', 
        action='version', 
        version='Eunice Thesis Generator v1.0.0'
    )
    
    args = parser.parse_args()
    
    # Handle setup mode
    if args.setup:
        from src.thesis.setup_thesis import main as setup_main
        setup_main()
        return
    
    # Validate input file is provided
    if not args.input:
        print("❌ Error: Input file is required (except for --setup mode)")
        parser.print_help()
        sys.exit(1)
    
    # Validate input file exists
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"❌ Error: Input file not found: {input_file}")
        sys.exit(1)
    
    # Set default config if not provided
    if not args.config:
        args.config = str(Path(__file__).parent / 'src/thesis/config/thesis_config.yaml')
    
    try:
        if args.basic:
            # Use basic generator
            from src.thesis.generators.basic_thesis_generator import ThesisGenerator
            generator = ThesisGenerator()
            print("🔧 Using basic thesis generator...")
            # Note: Basic generator has different interface - would need adaptation
            print("⚠️  Basic generator interface needs updating for new CLI")
            sys.exit(1)
        else:
            # Use enhanced generator
            generator = EnhancedThesisGenerator(args.config)
            
            # Override config with CLI args
            if args.output:
                generator.config['output']['directory'] = args.output
            if args.no_checkpoints:
                generator.config['processing']['human_checkpoints'] = False
            if args.formats:
                generator.config['output']['formats'] = args.formats
            
            print("🚀 Starting enhanced thesis generation...")
            result = generator.generate_enhanced_thesis_chapter(str(input_file))
            
            print(f"\n✅ Thesis chapter generated successfully!")
            print(f"📁 Output directory: {generator.config['output']['directory']}")
            print(f"📊 Generated: {len(result['themes'])} themes, {len(result['gaps'])} gaps, {len(result['research_questions'])} research questions")
            print(f"📄 Formats: {list(result['outputs'].keys())}")
            print(f"⏱️  Processing time: {result['duration']:.1f}s")
            
            # List output files
            print(f"\n📋 Output files:")
            for file_path in result['saved_files']:
                print(f"   • {file_path}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
