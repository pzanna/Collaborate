#!/usr/bin/env python3
"""
Document Quality Validation Test

This script analyzes the quality of generated PRISMA reports and thesis chapters,
validating compliance with academic standards and providing quality metrics.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


@dataclass
class QualityMetrics:
    """Quality metrics for academic documents."""
    word_count: int
    section_count: int
    citation_count: int
    academic_language_score: float
    structure_compliance: float
    completeness_score: float
    issues: List[str]
    recommendations: List[str]


class DocumentQualityAnalyzer:
    """Analyzer for academic document quality."""
    
    def __init__(self):
        """Initialize the quality analyzer."""
        # Academic language indicators
        self.academic_terms = [
            'however', 'moreover', 'furthermore', 'therefore', 'consequently',
            'nonetheless', 'nevertheless', 'accordingly', 'subsequently',
            'methodology', 'analysis', 'systematic', 'comprehensive', 'significant',
            'evidence', 'findings', 'implications', 'limitations', 'framework'
        ]
        
        # PRISMA section requirements
        self.prisma_required_sections = [
            'abstract', 'introduction', 'methods', 'results', 'discussion',
            'eligibility criteria', 'information sources', 'study selection'
        ]
        
        # Thesis chapter requirements
        self.thesis_required_sections = [
            'introduction', 'thematic synthesis', 'research gaps',
            'conceptual framework', 'conclusion'
        ]
    
    def analyze_prisma_report(self, content: str) -> QualityMetrics:
        """Analyze PRISMA report quality."""
        issues = []
        recommendations = []
        
        # Basic metrics
        word_count = len(content.split())
        sections = self._extract_sections(content)
        section_count = len(sections)
        citation_count = self._count_citations(content)
        
        # Structure compliance check
        structure_score = self._check_prisma_structure(sections)
        if structure_score < 0.8:
            issues.append("Missing required PRISMA sections")
            recommendations.append("Ensure all PRISMA 2020 checklist items are addressed")
        
        # Academic language assessment
        language_score = self._assess_academic_language(content)
        if language_score < 0.6:
            issues.append("Limited use of academic language")
            recommendations.append("Incorporate more academic terminology and formal language")
        
        # Completeness check
        completeness_score = self._assess_completeness(content, 'prisma')
        if completeness_score < 0.7:
            issues.append("Content appears incomplete")
            recommendations.append("Expand sections with more detailed analysis")
        
        # Word count validation
        if word_count < 1000:
            issues.append("Document length below typical systematic review standards")
            recommendations.append("Expand content to meet academic publication standards")
        
        return QualityMetrics(
            word_count=word_count,
            section_count=section_count,
            citation_count=citation_count,
            academic_language_score=language_score,
            structure_compliance=structure_score,
            completeness_score=completeness_score,
            issues=issues,
            recommendations=recommendations
        )
    
    def analyze_thesis_chapter(self, content: str) -> QualityMetrics:
        """Analyze thesis chapter quality."""
        issues = []
        recommendations = []
        
        # Basic metrics
        word_count = len(content.split())
        sections = self._extract_sections(content)
        section_count = len(sections)
        citation_count = self._count_citations(content)
        
        # Structure compliance check
        structure_score = self._check_thesis_structure(sections)
        if structure_score < 0.8:
            issues.append("Missing required thesis chapter sections")
            recommendations.append("Include all standard literature review sections")
        
        # Academic language assessment
        language_score = self._assess_academic_language(content)
        if language_score < 0.7:
            issues.append("Academic language could be more sophisticated")
            recommendations.append("Use more advanced academic vocabulary and expressions")
        
        # Completeness check
        completeness_score = self._assess_completeness(content, 'thesis')
        if completeness_score < 0.8:
            issues.append("Chapter content needs expansion")
            recommendations.append("Develop themes and arguments more thoroughly")
        
        # Word count validation for thesis chapter
        if word_count < 2000:
            issues.append("Chapter length below PhD thesis standards")
            recommendations.append("Expand to 3000-5000 words for comprehensive coverage")
        
        # Critical analysis check
        critical_analysis_score = self._assess_critical_analysis(content)
        if critical_analysis_score < 0.6:
            issues.append("Limited critical analysis evident")
            recommendations.append("Include more critical evaluation of studies and theories")
        
        return QualityMetrics(
            word_count=word_count,
            section_count=section_count,
            citation_count=citation_count,
            academic_language_score=language_score,
            structure_compliance=structure_score,
            completeness_score=completeness_score,
            issues=issues,
            recommendations=recommendations
        )
    
    def _extract_sections(self, content: str) -> List[str]:
        """Extract section headings from content."""
        # Match markdown headers (# ## ###)
        headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        return [header.lower().strip() for header in headers]
    
    def _count_citations(self, content: str) -> int:
        """Count citations in content."""
        # Count patterns like "Author et al. 2023" or "[1]" or "(Smith, 2023)"
        citation_patterns = [
            r'\b[A-Z][a-z]+\s+et\s+al\.\s+\d{4}',  # Author et al. 2023
            r'\[[0-9,\s-]+\]',  # [1] or [1,2,3] or [1-3]
            r'\([A-Z][a-z]+,?\s+\d{4}\)',  # (Smith, 2023)
        ]
        
        total_citations = 0
        for pattern in citation_patterns:
            total_citations += len(re.findall(pattern, content))
        
        return total_citations
    
    def _check_prisma_structure(self, sections: List[str]) -> float:
        """Check PRISMA structure compliance."""
        found_sections = 0
        for required in self.prisma_required_sections:
            if any(required in section for section in sections):
                found_sections += 1
        
        return found_sections / len(self.prisma_required_sections)
    
    def _check_thesis_structure(self, sections: List[str]) -> float:
        """Check thesis chapter structure compliance."""
        found_sections = 0
        for required in self.thesis_required_sections:
            if any(required in section for section in sections):
                found_sections += 1
        
        return found_sections / len(self.thesis_required_sections)
    
    def _assess_academic_language(self, content: str) -> float:
        """Assess academic language usage."""
        content_lower = content.lower()
        academic_terms_found = 0
        
        for term in self.academic_terms:
            if term in content_lower:
                academic_terms_found += 1
        
        # Normalize by content length and term list
        word_count = len(content.split())
        normalized_score = (academic_terms_found / len(self.academic_terms)) * (word_count / 1000)
        
        return min(1.0, normalized_score)
    
    def _assess_completeness(self, content: str, doc_type: str) -> float:
        """Assess content completeness."""
        # Check for placeholder text or incomplete sections
        incomplete_indicators = [
            'todo', 'tbd', 'to be determined', 'placeholder', 
            'insert content', 'add details', '...', 'etc.',
            'background:', 'conclusion:', 'discussion:'  # Empty section headers
        ]
        
        content_lower = content.lower()
        incomplete_count = 0
        
        for indicator in incomplete_indicators:
            incomplete_count += content_lower.count(indicator)
        
        # Check section lengths
        sections = content.split('\n##')
        short_sections = sum(1 for section in sections if len(section.split()) < 50)
        
        # Completeness score (1.0 is perfect, lower means more incomplete)
        incompleteness_penalty = (incomplete_count * 0.1) + (short_sections * 0.05)
        completeness_score = max(0.0, 1.0 - incompleteness_penalty)
        
        return completeness_score
    
    def _assess_critical_analysis(self, content: str) -> float:
        """Assess level of critical analysis."""
        critical_indicators = [
            'limitations', 'strengths', 'weaknesses', 'critique', 'evaluation',
            'however', 'although', 'despite', 'contradicts', 'conflicts',
            'supports', 'challenges', 'inconsistent', 'consistent',
            'gap', 'gaps', 'missing', 'unclear', 'ambiguous'
        ]
        
        content_lower = content.lower()
        critical_terms_found = 0
        
        for term in critical_indicators:
            if term in content_lower:
                critical_terms_found += 1
        
        # Normalize score
        return min(1.0, critical_terms_found / len(critical_indicators))


def generate_quality_report(file_path: Path, doc_type: str) -> Tuple[QualityMetrics, str]:
    """Generate quality report for a document."""
    analyzer = DocumentQualityAnalyzer()
    
    try:
        content = file_path.read_text(encoding='utf-8')
        
        if doc_type == 'prisma':
            metrics = analyzer.analyze_prisma_report(content)
        elif doc_type == 'thesis':
            metrics = analyzer.analyze_thesis_chapter(content)
        else:
            raise ValueError(f"Unknown document type: {doc_type}")
        
        # Generate detailed report
        report = f"""
📊 Document Quality Analysis Report
=====================================

📄 Document: {file_path.name}
📋 Type: {doc_type.upper()}
📅 Analysis Date: {Path(__file__).stat().st_mtime}

📈 Quality Metrics:
------------------
• Word Count: {metrics.word_count:,} words
• Section Count: {metrics.section_count} sections
• Citation Count: {metrics.citation_count} citations
• Academic Language Score: {metrics.academic_language_score:.2%}
• Structure Compliance: {metrics.structure_compliance:.2%}
• Completeness Score: {metrics.completeness_score:.2%}

📋 Overall Quality Grade:
------------------------
{_calculate_overall_grade(metrics)}

⚠️  Issues Found ({len(metrics.issues)}):
{chr(10).join(f'• {issue}' for issue in metrics.issues) if metrics.issues else '• No significant issues detected'}

💡 Recommendations ({len(metrics.recommendations)}):
{chr(10).join(f'• {rec}' for rec in metrics.recommendations) if metrics.recommendations else '• Document meets quality standards'}

"""
        
        return metrics, report
    
    except Exception as e:
        error_report = f"❌ Error analyzing {file_path}: {e}"
        # Return empty metrics for error case
        empty_metrics = QualityMetrics(0, 0, 0, 0.0, 0.0, 0.0, [f"Analysis failed: {e}"], [])
        return empty_metrics, error_report


def _calculate_overall_grade(metrics: QualityMetrics) -> str:
    """Calculate overall quality grade."""
    # Weighted average of metrics
    weights = {
        'structure': 0.25,
        'language': 0.20,
        'completeness': 0.25,
        'content_depth': 0.15,  # Based on word count
        'citations': 0.15
    }
    
    # Normalize metrics to 0-1 scale
    structure_score = metrics.structure_compliance
    language_score = metrics.academic_language_score
    completeness_score = metrics.completeness_score
    content_depth_score = min(1.0, metrics.word_count / 2000)  # 2000 words = 100%
    citation_score = min(1.0, metrics.citation_count / 10)  # 10 citations = 100%
    
    overall_score = (
        structure_score * weights['structure'] +
        language_score * weights['language'] +
        completeness_score * weights['completeness'] +
        content_depth_score * weights['content_depth'] +
        citation_score * weights['citations']
    )
    
    if overall_score >= 0.9:
        return "🌟 EXCELLENT (A+)"
    elif overall_score >= 0.8:
        return "✅ VERY GOOD (A)"
    elif overall_score >= 0.7:
        return "👍 GOOD (B)"
    elif overall_score >= 0.6:
        return "⚠️  ADEQUATE (C)"
    elif overall_score >= 0.5:
        return "🔄 NEEDS IMPROVEMENT (D)"
    else:
        return "❌ POOR (F)"


def main():
    """Main function to analyze document quality."""
    print("📊 Document Quality Analysis Tool")
    print("=" * 50)
    
    # Find the most recent export directory - check both regular and enhanced
    export_dirs_to_check = [
        "exports/enhanced_pipeline",
        "exports/complete_pipeline"
    ]
    
    latest_export = None
    latest_time = 0
    
    for exports_path in export_dirs_to_check:
        exports_dir = Path(exports_path)
        if exports_dir.exists():
            export_dirs = [d for d in exports_dir.iterdir() if d.is_dir()]
            for export_dir in export_dirs:
                dir_time = export_dir.stat().st_mtime
                if dir_time > latest_time:
                    latest_time = dir_time
                    latest_export = export_dir
    
    if not latest_export:
        print("❌ No export directories found. Run test_complete_pipeline.py or test_enhanced_pipeline.py first.")
        return
    
    print(f"📁 Analyzing documents from: {latest_export.parent.name}/{latest_export.name}")
    
    # Analyze documents
    results = []
    
    # Find PRISMA documents - check both naming patterns
    prisma_patterns = ["prisma_report.*", "enhanced_prisma_report.*"]
    thesis_patterns = ["thesis_*.md", "enhanced_thesis_*.md"]
    
    prisma_files = []
    thesis_files = []
    
    for pattern in prisma_patterns:
        prisma_files.extend(list(latest_export.glob(pattern)))
    
    for pattern in thesis_patterns:
        thesis_files.extend(list(latest_export.glob(pattern)))
    
    print(f"\n📋 Found {len(prisma_files)} PRISMA documents and {len(thesis_files)} thesis chapters")
    
    # Analyze PRISMA reports
    for prisma_file in prisma_files:
        if prisma_file.suffix in ['.md', '.html']:
            print(f"\n🔍 Analyzing PRISMA: {prisma_file.name}")
            metrics, report = generate_quality_report(prisma_file, 'prisma')
            if metrics:
                results.append(('PRISMA', prisma_file.name, metrics))
                print(report)
    
    # Analyze thesis chapters
    for thesis_file in thesis_files:
        print(f"\n🔍 Analyzing Thesis: {thesis_file.name}")
        metrics, report = generate_quality_report(thesis_file, 'thesis')
        if metrics:
            results.append(('Thesis', thesis_file.name, metrics))
            print(report)
    
    # Summary comparison
    if results:
        print("\n" + "=" * 60)
        print("📊 QUALITY SUMMARY COMPARISON")
        print("=" * 60)
        
        for doc_type, filename, metrics in results:
            grade = _calculate_overall_grade(metrics)
            print(f"{doc_type:8} | {filename:30} | {grade}")
        
        print("\n💡 Next Steps:")
        print("• Review recommendations above for each document")
        print("• Consider running the pipeline again with improvements")
        print("• Use generated documents as templates for further research")


if __name__ == "__main__":
    main()
