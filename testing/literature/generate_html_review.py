#!/usr/bin/env python3
"""
Literature Review HTML Generator
===============================

Converts the comprehensive JSON literature review into a readable HTML format
suitable for academic presentation and publication.
"""

import json
import html as html_module
from pathlib import Path


def generate_html_review():
    """Generate HTML version of the comprehensive literature review"""
    
    # Load the comprehensive review
    with open("comprehensive_literature_review.json", "r") as f:
        review = json.load(f)
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{review['metadata']['title']}</title>
    <style>
        body {{
            font-family: 'Times New Roman', serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .container {{
            background-color: white;
            padding: 40px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            font-size: 28px;
            margin-bottom: 30px;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            font-size: 22px;
            margin-top: 30px;
            margin-bottom: 15px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        h3 {{
            color: #2c3e50;
            font-size: 18px;
            margin-top: 25px;
            margin-bottom: 10px;
        }}
        .authors {{
            text-align: center;
            font-style: italic;
            margin-bottom: 20px;
            color: #7f8c8d;
        }}
        .metadata {{
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
        }}
        .abstract {{
            background-color: #e8f5e8;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 5px solid #27ae60;
        }}
        .abstract h3 {{
            color: #27ae60;
            margin-top: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }}
        th, td {{
            border: 1px solid #bdc3c7;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        .grade-table {{
            background-color: #fff3cd;
            border: 2px solid #ffc107;
        }}
        .grade-table th {{
            background-color: #ffc107;
            color: #212529;
        }}
        .highlight {{
            background-color: #fff3cd;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        .conclusion {{
            background-color: #d1ecf1;
            padding: 20px;
            border-radius: 5px;
            border-left: 5px solid #17a2b8;
            margin-top: 30px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #bdc3c7;
            color: #7f8c8d;
            font-size: 12px;
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            background-color: #e3f2fd;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #1976d2;
        }}
        .stat-label {{
            font-size: 14px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{review['metadata']['title']}</h1>
        
        <div class="authors">
            {', '.join(review['metadata']['authors'])}
        </div>
        
        <div class="metadata">
            <strong>Registration:</strong> {review['metadata']['registration']} | 
            <strong>Funding:</strong> {review['metadata']['funding']} | 
            <strong>Conflicts:</strong> {review['metadata']['conflicts_of_interest']}
        </div>
        
        <div class="abstract">
            <h3>Abstract</h3>
            <p><strong>Background:</strong> {review['abstract']['background']}</p>
            <p><strong>Objectives:</strong> {review['abstract']['objectives']}</p>
            <p><strong>Methods:</strong> {review['abstract']['methods']}</p>
            <p><strong>Results:</strong> {review['abstract']['results']}</p>
            <p><strong>Conclusions:</strong> {review['abstract']['conclusions']}</p>
        </div>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-value">{review['results']['study_characteristics']['total_studies']}</div>
                <div class="stat-label">Studies Included</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{review['results']['participant_characteristics']['total_participants']:,}</div>
                <div class="stat-label">Total Participants</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{review['results']['diagnostic_performance']['pooled_sensitivity']['estimate']:.3f}</div>
                <div class="stat-label">Pooled Sensitivity</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{review['results']['diagnostic_performance']['pooled_specificity']['estimate']:.3f}</div>
                <div class="stat-label">Pooled Specificity</div>
            </div>
        </div>
        
        <h2>1. Introduction</h2>
        <h3>Background</h3>
        <p>{review['introduction']['background']['clinical_context']}</p>
        <p>{review['introduction']['background']['technology_evolution']}</p>
        <p>{review['introduction']['background']['current_landscape']}</p>
        
        <h3>Rationale</h3>
        <p><strong>Knowledge Gap:</strong> {review['introduction']['rationale']['knowledge_gap']}</p>
        <p><strong>Clinical Importance:</strong> {review['introduction']['rationale']['clinical_importance']}</p>
        
        <h3>Objectives</h3>
        <p><strong>Primary:</strong> {review['introduction']['objectives']['primary']}</p>
        <p><strong>Secondary Objectives:</strong></p>
        <ul>
        {''.join(f'<li>{obj}</li>' for obj in review['introduction']['objectives']['secondary'])}
        </ul>
        
        <h2>2. Methods</h2>
        <h3>Search Strategy</h3>
        <p>We searched {len(review['methods']['search_strategy']['databases'])} databases: 
        {', '.join(db['name'] for db in review['methods']['search_strategy']['databases'])}.</p>
        
        <h3>Eligibility Criteria</h3>
        <p><strong>Inclusion Criteria:</strong></p>
        <ul>
        {''.join(f'<li>{criteria}</li>' for criteria in review['methods']['eligibility_criteria']['inclusion'])}
        </ul>
        <p><strong>Exclusion Criteria:</strong></p>
        <ul>
        {''.join(f'<li>{criteria}</li>' for criteria in review['methods']['eligibility_criteria']['exclusion'])}
        </ul>
        
        <h3>Quality Assessment</h3>
        <p>Quality was assessed using the {review['methods']['quality_assessment']['framework']} framework. 
        {review['methods']['quality_assessment']['bias_assessment']}.</p>
        
        <h2>3. Results</h2>
        <h3>Search Results</h3>
        <p>The search yielded {review['results']['search_results']['total_records']:,} records. 
        After deduplication and screening, {review['results']['search_results']['included_studies']} studies 
        met the inclusion criteria.</p>
        
        <h3>Study Characteristics</h3>
        {generate_study_characteristics_table(review['data_extraction_tables']['table_1_study_characteristics'])}
        
        <h3>Diagnostic Performance</h3>
        <div class="highlight">
            <p><strong>Pooled Results:</strong></p>
            <ul>
                <li>Sensitivity: {review['results']['diagnostic_performance']['pooled_sensitivity']['estimate']:.3f} 
                (95% CI: {review['results']['diagnostic_performance']['pooled_sensitivity']['ci_lower']:.3f}-{review['results']['diagnostic_performance']['pooled_sensitivity']['ci_upper']:.3f})</li>
                <li>Specificity: {review['results']['diagnostic_performance']['pooled_specificity']['estimate']:.3f} 
                (95% CI: {review['results']['diagnostic_performance']['pooled_specificity']['ci_lower']:.3f}-{review['results']['diagnostic_performance']['pooled_specificity']['ci_upper']:.3f})</li>
                <li>Accuracy: {review['results']['diagnostic_performance']['pooled_accuracy']['estimate']:.3f} 
                (95% CI: {review['results']['diagnostic_performance']['pooled_accuracy']['ci_lower']:.3f}-{review['results']['diagnostic_performance']['pooled_accuracy']['ci_upper']:.3f})</li>
            </ul>
        </div>
        
        {generate_performance_table(review['data_extraction_tables']['table_3_diagnostic_performance'])}
        
        <h3>Subgroup Analyses</h3>
        {generate_subgroup_analysis(review['results']['subgroup_analyses'])}
        
        <h2>4. Quality Assessment</h2>
        {generate_quality_table(review['data_extraction_tables']['table_4_quality_assessment'])}
        
        <h2>5. GRADE Evidence Profile</h2>
        {generate_grade_table(review['grade_evidence_profiles']['main_outcome_profile'])}
        
        <h2>6. Discussion</h2>
        <h3>Summary of Findings</h3>
        <p>{review['discussion']['summary_of_findings']['main_results']}</p>
        <p>{review['discussion']['summary_of_findings']['clinical_significance']}</p>
        
        <h3>Strengths and Limitations</h3>
        <p><strong>Strengths:</strong></p>
        <ul>
        {''.join(f'<li>{strength}</li>' for strength in review['discussion']['strengths_and_limitations']['strengths'])}
        </ul>
        <p><strong>Limitations:</strong></p>
        <ul>
        {''.join(f'<li>{limitation}</li>' for limitation in review['discussion']['strengths_and_limitations']['limitations'])}
        </ul>
        
        <h3>Clinical Implications</h3>
        <p><strong>For Healthcare Providers:</strong> {review['discussion']['clinical_implications']['healthcare_providers']}</p>
        <p><strong>For Healthcare Systems:</strong> {review['discussion']['clinical_implications']['healthcare_systems']}</p>
        
        <h2>7. Conclusions</h2>
        <div class="conclusion">
            <p><strong>Main Conclusions:</strong> {review['conclusions']['main_conclusions']}</p>
            <p><strong>Clinical Practice:</strong> {review['conclusions']['clinical_practice']}</p>
            <p><strong>Research Priorities:</strong> {review['conclusions']['research_priorities']}</p>
        </div>
        
        <div class="footer">
            <p><strong>Generated:</strong> {review['generation_metadata']['generated_at']} | 
            <strong>Processing Time:</strong> {review['generation_metadata']['processing_time']:.2f}s | 
            <strong>Word Count:</strong> {review['generation_metadata']['word_count']:,}</p>
            <p><em>This systematic review was generated by the Eunice AI Research System demonstrating 
            comprehensive literature analysis capabilities.</em></p>
        </div>
    </div>
</body>
</html>
"""
    
    return html_content


def generate_study_characteristics_table(table_data):
    """Generate HTML table for study characteristics"""
    html = f'<h4>{table_data["title"]}</h4><table>'
    
    # Header
    html += '<tr>'
    for col in table_data['columns']:
        html += f'<th>{col}</th>'
    html += '</tr>'
    
    # Data rows
    for row in table_data['data']:
        html += '<tr>'
        for col in table_data['columns']:
            key = col.lower().replace(' ', '_').replace('-', '_')
            value = str(row.get(key, ''))
            escaped_value = html_module.escape(value) if value else ""
            html += f'<td>{escaped_value}</td>'
        html += '</tr>'
    
    html += '</table>'
    return html


def generate_performance_table(table_data):
    """Generate HTML table for diagnostic performance"""
    html = f'<h4>{table_data["title"]}</h4><table>'
    
    # Header
    html += '<tr>'
    for col in table_data['columns']:
        html += f'<th>{col}</th>'
    html += '</tr>'
    
    # Data rows
    for row in table_data['data']:
        html += '<tr>'
        for col in table_data['columns']:
            key = col.lower().replace(' ', '_').replace('-', '_').replace('+', '_positive').replace('-', '_negative')
            value = str(row.get(key, ''))
            html += f'<td>{value}</td>'
        html += '</tr>'
    
    html += '</table>'
    return html


def generate_subgroup_analysis(subgroups):
    """Generate subgroup analysis section"""
    html = ""
    
    for analysis_type, data in subgroups.items():
        html += f'<h4>{analysis_type.replace("_", " ").title()}</h4><table>'
        html += '<tr><th>Group</th><th>Studies</th><th>Sensitivity</th><th>Specificity</th><th>Accuracy</th><th>AUC</th></tr>'
        
        for group, metrics in data.items():
            html += f'''<tr>
                <td>{group.replace("_", " ").title()}</td>
                <td>{metrics["n_studies"]}</td>
                <td>{metrics["sensitivity"]:.3f}</td>
                <td>{metrics["specificity"]:.3f}</td>
                <td>{metrics["accuracy"]:.3f}</td>
                <td>{metrics["auc"]:.3f}</td>
            </tr>'''
        
        html += '</table>'
    
    return html


def generate_quality_table(table_data):
    """Generate quality assessment table"""
    html = f'<h4>{table_data["title"]}</h4><table>'
    
    # Header
    html += '<tr>'
    for col in table_data['columns']:
        html += f'<th>{col}</th>'
    html += '</tr>'
    
    # Data rows
    for row in table_data['data']:
        html += '<tr>'
        for col in table_data['columns']:
            key = col.lower().replace(' ', '_')
            value = str(row.get(key, ''))
            html += f'<td>{value}</td>'
        html += '</tr>'
    
    html += '</table>'
    return html


def generate_grade_table(grade_profile):
    """Generate GRADE evidence profile table"""
    html = f'''
    <div class="grade-table">
        <h4>GRADE Evidence Profile: {grade_profile['question']}</h4>
        <table class="grade-table">
            <tr>
                <th>Population</th>
                <th>Intervention</th>
                <th>Comparator</th>
                <th>Outcome</th>
                <th>Certainty</th>
            </tr>
            <tr>
                <td>{grade_profile['population']}</td>
                <td>{grade_profile['intervention']}</td>
                <td>{grade_profile['comparator']}</td>
                <td>{grade_profile['outcome']}</td>
                <td><strong>{grade_profile['final_certainty']}</strong></td>
            </tr>
        </table>
        
        <h4>Certainty Assessment Details</h4>
        <table class="grade-table">
            <tr>
                <th>Factor</th>
                <th>Assessment</th>
                <th>Explanation</th>
                <th>Impact</th>
            </tr>
            <tr>
                <td>Risk of Bias</td>
                <td>{grade_profile['evidence_assessment']['factors_decreasing_certainty']['risk_of_bias']['rating']}</td>
                <td>{grade_profile['evidence_assessment']['factors_decreasing_certainty']['risk_of_bias']['explanation']}</td>
                <td>{grade_profile['evidence_assessment']['factors_decreasing_certainty']['risk_of_bias']['downgrade']}</td>
            </tr>
            <tr>
                <td>Inconsistency</td>
                <td>{grade_profile['evidence_assessment']['factors_decreasing_certainty']['inconsistency']['rating']}</td>
                <td>{grade_profile['evidence_assessment']['factors_decreasing_certainty']['inconsistency']['explanation']}</td>
                <td>{grade_profile['evidence_assessment']['factors_decreasing_certainty']['inconsistency']['downgrade']}</td>
            </tr>
            <tr>
                <td>Indirectness</td>
                <td>{grade_profile['evidence_assessment']['factors_decreasing_certainty']['indirectness']['rating']}</td>
                <td>{grade_profile['evidence_assessment']['factors_decreasing_certainty']['indirectness']['explanation']}</td>
                <td>{grade_profile['evidence_assessment']['factors_decreasing_certainty']['indirectness']['downgrade']}</td>
            </tr>
            <tr>
                <td>Imprecision</td>
                <td>{grade_profile['evidence_assessment']['factors_decreasing_certainty']['imprecision']['rating']}</td>
                <td>{grade_profile['evidence_assessment']['factors_decreasing_certainty']['imprecision']['explanation']}</td>
                <td>{grade_profile['evidence_assessment']['factors_decreasing_certainty']['imprecision']['downgrade']}</td>
            </tr>
        </table>
        
        <div class="highlight">
            <p><strong>Final Assessment:</strong> {grade_profile['justification']}</p>
        </div>
    </div>
    '''
    return html


def main():
    """Generate and save HTML literature review"""
    print("📄 Converting literature review to HTML format...")
    
    html_content = generate_html_review()
    
    # Save HTML file
    with open("systematic_review.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print("✅ HTML literature review generated successfully!")
    print("📋 File saved as: systematic_review.html")
    print("🌐 Open in browser to view the formatted systematic review")


if __name__ == "__main__":
    main()
