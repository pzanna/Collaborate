#!/usr/bin/env python3
"""
LaTeX Template Generator for Thesis Literature Reviews
=====================================================

Converts thesis literature review to LaTeX with proper academic formatting.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, Any, List


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    if not isinstance(text, str):
        return str(text)
    
    # LaTeX special characters
    latex_chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '^': r'\textasciicircum{}',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '\\': r'\textbackslash{}'
    }
    
    for char, replacement in latex_chars.items():
        text = text.replace(char, replacement)
    
    return text


def generate_latex_document(thesis_data: Dict[str, Any]) -> str:
    """Generate complete LaTeX document."""
    
    themes = thesis_data.get("themes", [])
    gaps = thesis_data.get("gaps", [])
    framework = thesis_data.get("framework", {})
    metadata = thesis_data.get("metadata", {})
    
    latex_content = r"""
\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amsfonts,amssymb}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{setspace}
\usepackage{tikz}
\usepackage{xcolor}
\usepackage{minted}

\geometry{margin=1in}
\doublespacing
\pagestyle{fancy}
\fancyhf{}
\fancyhead[R]{\thepage}
\fancyhead[L]{Literature Review}

\title{Literature Review: Machine Learning in Healthcare Diagnosis}
\author{PhD Candidate}
\date{\today}

\begin{document}

\maketitle
\tableofcontents
\newpage

\section{Abstract}

Machine learning (ML) applications in healthcare diagnosis have rapidly expanded, but their clinical effectiveness requires systematic evaluation. This review synthesizes evidence on ML diagnostic tools' performance and clinical impact through a comprehensive thematic analysis and identification of research gaps.

\section{Introduction}

\subsection{Background and Context}

Healthcare diagnosis remains one of the most critical and challenging aspects of clinical practice. Diagnostic errors affect an estimated 12 million adults annually in the United States, with significant implications for patient safety and healthcare costs. The complexity of modern medicine, combined with increasing patient volumes and time constraints, has created a pressing need for diagnostic support tools.

\subsection{Rationale}

\textbf{Knowledge Gap:} """ + escape_latex("While individual studies have demonstrated promising results for ML diagnostic tools, a comprehensive synthesis of evidence across medical domains is lacking. Previous reviews have focused on specific conditions or technologies, but a broad evaluation of ML diagnostic effectiveness remains needed.") + r"""

\textbf{Clinical Importance:} """ + escape_latex("Understanding the overall performance and implementation challenges of ML diagnostic tools is crucial for healthcare systems considering adoption. Clinicians need evidence-based guidance on when and how to integrate these technologies into clinical workflows.") + r"""

\section{Thematic Synthesis}

"""
    
    # Add themes
    for i, theme in enumerate(themes, 1):
        theme_name = escape_latex(theme.get("name", f"Theme {i}"))
        theme_summary = escape_latex(theme.get("summary", ""))
        theme_strength = escape_latex(theme.get("strength", "Moderate"))
        
        latex_content += f"""
\\subsection{{{theme_name}}}

{theme_summary}

\\textbf{{Strength of Evidence:}} {theme_strength}

"""
        
        if theme.get("contradictions"):
            contradictions = "; ".join(theme["contradictions"])
            latex_content += f"\\textbf{{Contradictory Findings:}} {escape_latex(contradictions)}\n\n"
    
    # Add research gaps
    latex_content += r"""
\section{Research Gaps and Opportunities}

"""
    
    for i, gap in enumerate(gaps, 1):
        gap_title = escape_latex(gap.get("title", f"Gap {i}"))
        gap_description = escape_latex(gap.get("description", ""))
        gap_justification = escape_latex(gap.get("justification", ""))
        
        latex_content += f"""
\\subsection{{{gap_title}}}

{gap_description}

\\textbf{{Justification:}} {gap_justification}

\\textbf{{Scores:}} Impact: {gap.get('impact', 0):.1f}/5 | Feasibility: {gap.get('feasibility', 0):.1f}/5 | Novelty: {gap.get('novelty', 0):.1f}/5

"""
    
    # Add conceptual framework
    framework_description = escape_latex(framework.get("description", ""))
    
    latex_content += f"""
\\section{{Conceptual Framework}}

{framework_description}

\\subsection{{Key Constructs}}

"""
    
    for construct in framework.get("constructs", []):
        construct_name = escape_latex(construct.get("name", ""))
        construct_desc = escape_latex(construct.get("description", ""))
        latex_content += f"\\textbf{{{construct_name}:}} {construct_desc}\n\n"
    
    latex_content += r"""
\subsection{Theoretical Relationships}

\begin{itemize}
"""
    
    for rel in framework.get("relationships", []):
        source = escape_latex(rel.get("source", ""))
        target = escape_latex(rel.get("target", ""))
        description = escape_latex(rel.get("description", ""))
        latex_content += f"\\item {source} $\\rightarrow$ {target}: {description}\n"
    
    latex_content += r"""
\end{itemize}

\section{Summary and Research Direction}

This literature review has identified """ + str(len(themes)) + r""" major themes and """ + str(len(gaps)) + r""" significant research gaps. The proposed conceptual framework provides a foundation for addressing these gaps through systematic empirical research.

The highest priority research opportunities focus on regulatory framework development for ML diagnostic tools, which offers both high impact potential and feasible implementation within a PhD research timeline.

\section{Conclusion}

The systematic analysis reveals significant opportunities for advancing machine learning applications in healthcare diagnosis. The identified research gaps provide clear directions for future PhD research that can contribute meaningfully to both theoretical understanding and clinical practice.

\bibliographystyle{apa}
\bibliography{references}

\end{document}
"""
    
    return latex_content


def main():
    """Generate LaTeX from thesis data."""
    parser = argparse.ArgumentParser(description="Convert thesis data to LaTeX")
    parser.add_argument("input", help="Input thesis JSON data file")
    parser.add_argument("-o", "--output", help="Output LaTeX file")
    
    args = parser.parse_args()
    
    # Load thesis data
    with open(args.input, 'r') as f:
        thesis_data = json.load(f)
    
    # Generate LaTeX
    latex_content = generate_latex_document(thesis_data)
    
    # Save output
    output_file = args.output or args.input.replace('.json', '.tex')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(latex_content)
    
    print(f"✅ LaTeX document generated: {output_file}")
    print(f"📝 Compile with: pdflatex {output_file}")


if __name__ == "__main__":
    main()
