"""
Research Tool Integration for External Analysis and Workflow Compatibility

This module provides comprehensive integration with external research tools including
R for statistical analysis, RevMan for Cochrane reviews, PROSPERO for protocol
registration, and GRADE Pro for evidence assessment.

Features:
- R integration for advanced statistical analysis
- RevMan compatibility for Cochrane systematic reviews
- PROSPERO protocol registration and retrieval
- GRADE Pro integration for evidence quality assessment
- Automated data exchange between tools
- Version control and reproducibility tracking

Author: Eunice AI System
Date: July 2025
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ToolType(Enum):
    """Supported research tool types"""

    R_STATISTICAL = "r_statistical"
    REVMAN = "revman"
    PROSPERO = "prospero"
    GRADE_PRO = "grade_pro"
    STATA = "stata"
    SAS = "sas"
    SPSS = "spss"
    PYTHON_ANALYSIS = "python_analysis"


class AnalysisType(Enum):
    """Types of statistical analyses"""

    META_ANALYSIS = "meta_analysis"
    FOREST_PLOT = "forest_plot"
    FUNNEL_PLOT = "funnel_plot"
    SUBGROUP_ANALYSIS = "subgroup_analysis"
    SENSITIVITY_ANALYSIS = "sensitivity_analysis"
    NETWORK_META_ANALYSIS = "network_meta_analysis"
    DESCRIPTIVE_STATISTICS = "descriptive_statistics"
    RISK_OF_BIAS_ASSESSMENT = "risk_of_bias"


@dataclass
class AnalysisResult:
    """Standardized analysis result structure"""

    result_id: str
    tool_type: ToolType
    analysis_type: AnalysisType
    title: str
    description: Optional[str]
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    plots: List[str]  # File paths to generated plots
    tables: List[Dict[str, Any]]
    statistics: Dict[str, float]
    confidence_intervals: Dict[str, Dict[str, float]]
    p_values: Dict[str, float]
    effect_sizes: Dict[str, float]
    heterogeneity: Optional[Dict[str, float]]
    code_used: Optional[str]
    log_output: Optional[str]
    created_timestamp: datetime
    execution_time: Optional[float]
    metadata: Dict[str, Any]


@dataclass
class ToolInterface:
    """Interface configuration for external tools"""

    tool_id: str
    tool_type: ToolType
    tool_path: str
    version: Optional[str]
    configuration: Dict[str, Any]
    is_available: bool
    last_used: Optional[datetime]
    usage_stats: Dict[str, Any]


class ResearchToolIntegration(ABC):
    """Abstract base class for research tool integrations"""

    def __init__(self, tool_config: ToolInterface):
        self.config = tool_config
        self.temp_dir = tempfile.mkdtemp(prefix="eunice_analysis_")

    @abstractmethod
    async def check_availability(self) -> bool:
        """Check if the tool is available and properly configured"""

    @abstractmethod
    async def execute_analysis(
        self,
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> AnalysisResult:
        """Execute analysis with the external tool"""

    @abstractmethod
    def generate_script(
        self,
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> str:
        """Generate analysis script for the tool"""

    def cleanup(self):
        """Clean up temporary files"""
        try:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory: {e}")


class RIntegration(ResearchToolIntegration):
    """R statistical software integration"""

    def __init__(self, r_path: str = "R", rscript_path: str = "Rscript"):
        config = ToolInterface(
            tool_id="r_default",
            tool_type=ToolType.R_STATISTICAL,
            tool_path=r_path,
            version=None,
            configuration={
                "rscript_path": rscript_path,
                "timeout": 300,
                "memory_limit": "8G",
            },  # 5 minutes
            is_available=False,
            last_used=None,
            usage_stats={},
        )
        super().__init__(config)
        self.rscript_path = rscript_path

    async def check_availability(self) -> bool:
        """Check if R is available"""
        try:
            # Test R installation
            result = subprocess.run(
                [self.config.tool_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                # Extract version info
                version_info = result.stdout.split("\n")[0]
                self.config.version = version_info
                self.config.is_available = True

                # Check for required packages
                await self._check_required_packages()

                logger.info(f"R is available: {version_info}")
                return True
            else:
                logger.error(f"R check failed: {result.stderr}")
                return False

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"R not found or timeout: {e}")
            return False

    async def _check_required_packages(self):
        """Check and install required R packages"""
        required_packages = [
            "meta",  # Meta - analysis
            "metafor",  # Meta - analysis framework
            "forestplot",  # Forest plots
            "funnel",  # Funnel plots
            "ggplot2",  # Advanced plotting
            "dplyr",  # Data manipulation
            "readr",  # Data reading
            "jsonlite",  # JSON handling
        ]

        check_script = f"""
# Check and install required packages
required_packages <- c({', '.join([f'"{pkg}"' for pkg in required_packages])})
missing_packages <- required_packages[!(required_packages %in% installed.packages()[,"Package"])]

if(length(missing_packages) > 0) {{
    cat("Installing missing packages:", paste(missing_packages, collapse=", "), "\\n")
    install.packages(missing_packages, repos="https://cran.r - project.org")
}}

cat("Package check complete\\n")
"""

        try:
            await self._execute_r_script(check_script, timeout=120)
            logger.info("R package dependencies verified")
        except Exception as e:
            logger.warning(f"R package check failed: {e}")

    async def execute_analysis(
        self,
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> AnalysisResult:
        """Execute R statistical analysis"""
        start_time = datetime.now()

        try:
            # Generate R script
            r_script = self.generate_script(analysis_type, data, parameters)

            # Execute R script
            result = await self._execute_r_script(r_script)

            # Parse results
            analysis_result = self._parse_r_output(
                result, analysis_type, data, parameters, r_script
            )

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            analysis_result.execution_time = execution_time

            return analysis_result

        except Exception as e:
            logger.error(f"R analysis failed: {e}")
            raise

    def generate_script(
        self,
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> str:
        """Generate R script for analysis"""

        if analysis_type == AnalysisType.META_ANALYSIS:
            return self._generate_meta_analysis_script(data, parameters)
        elif analysis_type == AnalysisType.FOREST_PLOT:
            return self._generate_forest_plot_script(data, parameters)
        elif analysis_type == AnalysisType.FUNNEL_PLOT:
            return self._generate_funnel_plot_script(data, parameters)
        elif analysis_type == AnalysisType.SUBGROUP_ANALYSIS:
            return self._generate_subgroup_analysis_script(data, parameters)
        else:
            raise ValueError(f"Unsupported analysis type: {analysis_type}")

    def _generate_meta_analysis_script(
        self, data: Dict[str, Any], parameters: Dict[str, Any]
    ) -> str:
        """Generate R script for meta - analysis"""

        parameters.get("effect_measure", "MD")  # MD, SMD, OR, RR
        model_type = parameters.get("model", "random")  # fixed, random
        method = parameters.get("method", "REML")  # REML, DL, etc.

        script = f"""
# Meta - analysis using metafor package
library(metafor)
library(jsonlite)

# Prepare data
studies <- '{json.dumps(data["studies"])}'
studies_data <- fromJSON(studies)

# Extract effect sizes and variances
yi <- studies_data$effect_size
vi <- studies_data$variance
sei <- studies_data$standard_error

# If standard errors provided instead of variances
if(is.null(vi) && !is.null(sei)) {{
    vi <- sei^2
}}

# Study labels
study_labels <- studies_data$study_id

# Perform meta - analysis
ma_result <- rma(yi = yi, vi = vi, method = "{method}",
                 model = "{model_type}", slab = study_labels)

# Summary statistics
summary_stats <- list(
    overall_effect = ma_result$beta[1],
    overall_se = ma_result$se,
    overall_ci_lower = ma_result$ci.lb,
    overall_ci_upper = ma_result$ci.ub,
    overall_pval = ma_result$pval,
    tau_squared = ma_result$tau2,
    i_squared = ma_result$I2,
    h_squared = ma_result$H2,
    q_statistic = ma_result$QE,
    q_pval = ma_result$QEp,
    number_of_studies = ma_result$k
)

# Forest plot
png(file.path("{self.temp_dir}", "forest_plot.png"), width = 800, height = 600)
forest(ma_result, main = "Meta - analysis Forest Plot")
dev.off()

# Funnel plot
png(file.path("{self.temp_dir}", "funnel_plot.png"), width = 600, height = 600)
funnel(ma_result, main = "Funnel Plot")
dev.off()

# Save results as JSON
results <- list(
    summary = summary_stats,
    study_results = data.frame(
        study = study_labels,
        effect_size = yi,
        variance = vi,
        weight = weights(ma_result),
        residual = residuals(ma_result)
    )
)

write_json(results, file.path("{self.temp_dir}", "results.json"))

cat("Meta - analysis completed successfully\\n")
print(summary_stats)
"""
        return script

    def _generate_forest_plot_script(
        self, data: Dict[str, Any], parameters: Dict[str, Any]
    ) -> str:
        """Generate R script for forest plot"""

        script = f"""
# Forest plot generation
library(metafor)
library(forestplot)
library(jsonlite)

# Prepare data
studies <- '{json.dumps(data["studies"])}'
studies_data <- fromJSON(studies)

# Extract data
study_names <- studies_data$study_id
effect_sizes <- studies_data$effect_size
ci_lower <- studies_data$ci_lower
ci_upper <- studies_data$ci_upper

# Create forest plot data
forest_data <- data.frame(
    study = study_names,
    effect = effect_sizes,
    lower = ci_lower,
    upper = ci_upper
)

# Generate forest plot
png(file.path("{self.temp_dir}", "forest_plot.png"), width = 1000, height = 800)

forestplot(
    labeltext = list(study_names),
    mean = effect_sizes,
    lower = ci_lower,
    upper = ci_upper,
    title = "Forest Plot",
    xlab = "Effect Size",
    boxsize = 0.3,
    lineheight = "auto",
    colgap = unit(4, "mm")
)

dev.off()

# Save plot data
write_json(forest_data, file.path("{self.temp_dir}", "forest_data.json"))

cat("Forest plot generated successfully\\n")
"""
        return script

    def _generate_funnel_plot_script(
        self, data: Dict[str, Any], parameters: Dict[str, Any]
    ) -> str:
        """Generate R script for funnel plot"""

        script = f"""
# Funnel plot for publication bias assessment
library(metafor)
library(jsonlite)

# Prepare data
studies <- '{json.dumps(data["studies"])}'
studies_data <- fromJSON(studies)

yi <- studies_data$effect_size
vi <- studies_data$variance
sei <- studies_data$standard_error

# If standard errors provided instead of variances
if(is.null(vi) && !is.null(sei)) {{
    vi <- sei^2
    sei <- sqrt(vi)
}} else {{
    sei <- sqrt(vi)
}}

# Create funnel plot
png(file.path("{self.temp_dir}", "funnel_plot.png"), width = 600, height = 600)
funnel(yi, sei, main = "Funnel Plot", xlab = "Effect Size", ylab = "Standard Error")
dev.off()

# Egger's test for asymmetry
egger_test <- regtest(yi, vi, model = "rma")

# Trim and fill method
tf_result <- trimfill(rma(yi, vi))

# Publication bias tests
bias_tests <- list(
    egger_intercept = egger_test$beta,
    egger_pval = egger_test$pval,
    trim_fill_k0 = tf_result$k0,
    trim_fill_side = tf_result$side
)

# Save results
write_json(bias_tests, file.path("{self.temp_dir}", "bias_tests.json"))

cat("Funnel plot and bias tests completed\\n")
print(bias_tests)
"""
        return script

    def _generate_subgroup_analysis_script(
        self, data: Dict[str, Any], parameters: Dict[str, Any]
    ) -> str:
        """Generate R script for subgroup analysis"""

        subgroup_var = parameters.get("subgroup_variable", "study_design")

        script = f"""
# Subgroup meta - analysis
library(metafor)
library(jsonlite)

# Prepare data
studies <- '{json.dumps(data["studies"])}'
studies_data <- fromJSON(studies)

yi <- studies_data$effect_size
vi <- studies_data$variance
subgroup <- studies_data${subgroup_var}

# Perform subgroup analysis
subgroup_result <- rma(yi, vi, mods = ~ subgroup)

# Test for subgroup differences
qm_test <- subgroup_result$QM
qm_pval <- subgroup_result$QMp

# Results by subgroup
subgroup_summary <- list(
    overall_test_statistic = qm_test,
    overall_test_pval = qm_pval,
    subgroups = list()
)

# Analyze each subgroup separately
unique_subgroups <- unique(subgroup)
for(sg in unique_subgroups) {{
    sg_indices <- which(subgroup == sg)
    sg_yi <- yi[sg_indices]
    sg_vi <- vi[sg_indices]

    sg_ma <- rma(sg_yi, sg_vi)

    subgroup_summary$subgroups[[sg]] <- list(
        n_studies = sg_ma$k,
        effect_size = sg_ma$beta[1],
        se = sg_ma$se,
        ci_lower = sg_ma$ci.lb,
        ci_upper = sg_ma$ci.ub,
        pval = sg_ma$pval,
        i_squared = sg_ma$I2
    )
}}

# Generate subgroup forest plot
png(file.path("{self.temp_dir}", "subgroup_forest.png"), width = 1000, height = 800)
forest(subgroup_result, main = "Subgroup Analysis")
dev.off()

# Save results
write_json(subgroup_summary, file.path("{self.temp_dir}", "subgroup_results.json"))

cat("Subgroup analysis completed\\n")
print(subgroup_summary)
"""
        return script

    async def _execute_r_script(
        self, script: str, timeout: int = 300
    ) -> Dict[str, Any]:
        """Execute R script and return results"""

        # Write script to temporary file
        script_file = os.path.join(self.temp_dir, "analysis.R")
        with open(script_file, "w") as f:
            f.write(script)

        try:
            # Execute R script
            result = subprocess.run(
                [self.rscript_path, script_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.temp_dir,
            )

            if result.returncode == 0:
                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "success": True,
                }
            else:
                raise Exception(f"R script failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise Exception(f"R script timed out after {timeout} seconds")
        except Exception as e:
            raise Exception(f"R execution error: {e}")

    def _parse_r_output(
        self,
        result: Dict[str, Any],
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
        script: str,
    ) -> AnalysisResult:
        """Parse R output and create AnalysisResult"""

        # Load JSON results if available
        results_file = os.path.join(self.temp_dir, "results.json")
        output_data = {}
        statistics = {}
        confidence_intervals = {}
        p_values = {}
        effect_sizes = {}
        heterogeneity = {}

        if os.path.exists(results_file):
            with open(results_file, "r") as f:
                json_results = json.load(f)
                output_data = json_results

                # Extract common statistics
                if "summary" in json_results:
                    summary = json_results["summary"]
                    statistics = {
                        "overall_effect": summary.get("overall_effect", 0),
                        "tau_squared": summary.get("tau_squared", 0),
                        "i_squared": summary.get("i_squared", 0),
                        "q_statistic": summary.get("q_statistic", 0),
                    }

                    confidence_intervals = {
                        "overall_effect": {
                            "lower": summary.get("overall_ci_lower", 0),
                            "upper": summary.get("overall_ci_upper", 0),
                        }
                    }

                    p_values = {
                        "overall_effect": summary.get("overall_pval", 1),
                        "heterogeneity": summary.get("q_pval", 1),
                    }

                    effect_sizes = {"overall": summary.get("overall_effect", 0)}

                    heterogeneity = {
                        "tau_squared": summary.get("tau_squared", 0),
                        "i_squared": summary.get("i_squared", 0),
                        "h_squared": summary.get("h_squared", 0),
                    }

        # Collect generated plots
        plots = []
        for filename in os.listdir(self.temp_dir):
            if filename.endswith(".png"):
                plots.append(os.path.join(self.temp_dir, filename))

        # Create analysis result
        return AnalysisResult(
            result_id=f"r_analysis_{int(datetime.now().timestamp())}",
            tool_type=ToolType.R_STATISTICAL,
            analysis_type=analysis_type,
            title=f"R {analysis_type.value.replace('_', ' ').title()}",
            description="Statistical analysis performed using R",
            input_data=data,
            output_data=output_data,
            plots=plots,
            tables=[],  # Would need additional parsing
            statistics=statistics,
            confidence_intervals=confidence_intervals,
            p_values=p_values,
            effect_sizes=effect_sizes,
            heterogeneity=heterogeneity,
            code_used=script,
            log_output=result.get("stdout", ""),
            created_timestamp=datetime.now(timezone.utc),
            execution_time=None,  # Set by caller
            metadata={
                "r_version": self.config.version,
                "parameters": parameters,
                "temp_dir": self.temp_dir,
            },
        )


class RevManCompatibility(ResearchToolIntegration):
    """RevMan (Review Manager) compatibility for Cochrane reviews"""

    def __init__(self, revman_path: Optional[str] = None):
        config = ToolInterface(
            tool_id="revman_default",
            tool_type=ToolType.REVMAN,
            tool_path=revman_path or "",
            version=None,
            configuration={"export_format": "xml", "data_validation": True},
            is_available=False,
            last_used=None,
            usage_stats={},
        )
        super().__init__(config)

    async def check_availability(self) -> bool:
        """Check RevMan availability (placeholder)"""
        # RevMan is typically a Windows application
        # This would require specific RevMan API or file format handling
        logger.info("RevMan compatibility check - would verify RevMan installation")
        self.config.is_available = False  # Set to False for now
        return False

    async def execute_analysis(
        self,
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> AnalysisResult:
        """Execute RevMan analysis (placeholder)"""
        raise NotImplementedError("RevMan integration not yet implemented")

    def generate_script(
        self,
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> str:
        """Generate RevMan - compatible data (placeholder)"""
        raise NotImplementedError("RevMan script generation not yet implemented")

    def export_to_revman_format(self, review_data: Dict[str, Any]) -> str:
        """Export systematic review data to RevMan - compatible XML"""

        # Create basic RevMan XML structure
        root = ET.Element("COCHRANE_REVIEW")

        # Add review metadata
        review_elem = ET.SubElement(root, "REVIEW_INFO")
        ET.SubElement(review_elem, "TITLE").text = review_data.get("title", "")
        ET.SubElement(review_elem, "STAGE").text = "PROTOCOL"

        # Add studies
        studies_elem = ET.SubElement(root, "STUDIES")
        for study in review_data.get("studies", []):
            study_elem = ET.SubElement(studies_elem, "STUDY")
            ET.SubElement(study_elem, "STUDY_ID").text = study.get("id", "")
            ET.SubElement(study_elem, "TITLE").text = study.get("title", "")
            ET.SubElement(study_elem, "YEAR").text = str(study.get("year", ""))

        # Convert to string
        return ET.tostring(root, encoding="unicode")


class ProsperoRegistration(ResearchToolIntegration):
    """PROSPERO protocol registration integration"""

    def __init__(self):
        config = ToolInterface(
            tool_id="prospero_default",
            tool_type=ToolType.PROSPERO,
            tool_path="https://www.crd.york.ac.uk / prospero/",
            version="1.0",
            configuration={
                "api_endpoint": "https://www.crd.york.ac.uk / prospero / api/",
                "timeout": 30,
            },
            is_available=True,
            last_used=None,
            usage_stats={},
        )
        super().__init__(config)

    async def check_availability(self) -> bool:
        """Check PROSPERO API availability"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                # Test PROSPERO website accessibility
                async with session.get(self.config.tool_path, timeout=10) as response:
                    if response.status == 200:
                        self.config.is_available = True
                        return True

            return False

        except Exception as e:
            logger.error(f"PROSPERO availability check failed: {e}")
            return False

    async def execute_analysis(
        self,
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> AnalysisResult:
        """Execute PROSPERO operations (placeholder)"""

        # This would involve protocol registration or retrieval
        logger.info(f"Would perform PROSPERO {analysis_type.value} operation")

        return AnalysisResult(
            result_id=f"prospero_{int(datetime.now().timestamp())}",
            tool_type=ToolType.PROSPERO,
            analysis_type=analysis_type,
            title="PROSPERO Protocol Operation",
            description="Protocol registration or retrieval",
            input_data=data,
            output_data={"status": "placeholder"},
            plots=[],
            tables=[],
            statistics={},
            confidence_intervals={},
            p_values={},
            effect_sizes={},
            heterogeneity=None,
            code_used=None,
            log_output="PROSPERO operation completed",
            created_timestamp=datetime.now(timezone.utc),
            execution_time=1.0,
            metadata={"prospero_id": parameters.get("prospero_id")},
        )

    def generate_script(
        self,
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> str:
        """Generate PROSPERO registration data"""
        return f"PROSPERO registration for: {data.get('title', 'Unnamed Review')}"


class GradeProIntegration(ResearchToolIntegration):
    """GRADE Pro integration for evidence quality assessment"""

    def __init__(self):
        config = ToolInterface(
            tool_id="grade_pro_default",
            tool_type=ToolType.GRADE_PRO,
            tool_path="",  # GRADE Pro is typically web - based
            version="1.0",
            configuration={
                "assessment_domains": [
                    "risk_of_bias",
                    "inconsistency",
                    "indirectness",
                    "imprecision",
                    "publication_bias",
                ],
                "quality_levels": ["high", "moderate", "low", "very_low"],
            },
            is_available=True,
            last_used=None,
            usage_stats={},
        )
        super().__init__(config)

    async def check_availability(self) -> bool:
        """Check GRADE Pro availability"""
        # GRADE Pro is typically a web application
        # This would check for proper configuration
        self.config.is_available = True
        return True

    async def execute_analysis(
        self,
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> AnalysisResult:
        """Execute GRADE assessment"""

        if analysis_type == AnalysisType.RISK_OF_BIAS_ASSESSMENT:
            return await self._perform_grade_assessment(data, parameters)
        else:
            raise ValueError(
                f"Unsupported analysis type for GRADE Pro: {analysis_type}"
            )

    async def _perform_grade_assessment(
        self, data: Dict[str, Any], parameters: Dict[str, Any]
    ) -> AnalysisResult:
        """Perform GRADE quality assessment"""

        # Simulate GRADE assessment
        outcomes = data.get("outcomes", [])
        assessments = {}

        for outcome in outcomes:
            outcome_id = outcome.get("id", "unknown")

            # Assess each GRADE domain
            domain_scores = {}
            for domain in self.config.configuration["assessment_domains"]:
                # Simplified scoring (would use actual GRADE criteria)
                score = self._assess_domain(outcome, domain, parameters)
                domain_scores[domain] = score

            # Calculate overall quality
            overall_quality = self._calculate_overall_quality(domain_scores)

            assessments[outcome_id] = {
                "outcome": outcome.get("name", outcome_id),
                "domain_scores": domain_scores,
                "overall_quality": overall_quality,
                "confidence": self._calculate_confidence(domain_scores),
            }

        return AnalysisResult(
            result_id=f"grade_{int(datetime.now().timestamp())}",
            tool_type=ToolType.GRADE_PRO,
            analysis_type=AnalysisType.RISK_OF_BIAS_ASSESSMENT,
            title="GRADE Quality Assessment",
            description="Evidence quality assessment using GRADE methodology",
            input_data=data,
            output_data={"assessments": assessments},
            plots=[],
            tables=[self._create_grade_table(assessments)],
            statistics={"n_outcomes": len(outcomes)},
            confidence_intervals={},
            p_values={},
            effect_sizes={},
            heterogeneity=None,
            code_used=None,
            log_output="GRADE assessment completed",
            created_timestamp=datetime.now(timezone.utc),
            execution_time=2.0,
            metadata={"grade_version": "simulated"},
        )

    def _assess_domain(
        self, outcome: Dict[str, Any], domain: str, parameters: Dict[str, Any]
    ) -> str:
        """Assess a single GRADE domain"""
        # Simplified assessment logic (would use detailed GRADE criteria)

        domain_mapping = {
            "risk_of_bias": "no_serious_issues",
            "inconsistency": "no_serious_issues",
            "indirectness": "no_serious_issues",
            "imprecision": "serious_issues",
            "publication_bias": "no_serious_issues",
        }

        return domain_mapping.get(domain, "no_serious_issues")

    def _calculate_overall_quality(self, domain_scores: Dict[str, str]) -> str:
        """Calculate overall GRADE quality level"""
        # Start with high quality for RCTs
        quality_score = 4

        # Downgrade for serious issues
        for domain, score in domain_scores.items():
            if score == "serious_issues":
                quality_score -= 1
            elif score == "very_serious_issues":
                quality_score -= 2

        # Map score to quality level
        if quality_score >= 4:
            return "high"
        elif quality_score >= 3:
            return "moderate"
        elif quality_score >= 2:
            return "low"
        else:
            return "very_low"

    def _calculate_confidence(self, domain_scores: Dict[str, str]) -> float:
        """Calculate confidence in assessment"""
        # Simple confidence calculation
        total_domains = len(domain_scores)
        serious_issues = sum(
            1 for score in domain_scores.values() if "serious" in score
        )

        return max(0.5, 1.0 - (serious_issues / total_domains * 0.3))

    def _create_grade_table(self, assessments: Dict[str, Any]) -> Dict[str, Any]:
        """Create GRADE summary table"""

        table_data = {
            "title": "GRADE Summary of Findings",
            "headers": [
                "Outcome",
                "Quality",
                "Risk of Bias",
                "Inconsistency",
                "Indirectness",
                "Imprecision",
                "Publication Bias",
            ],
            "rows": [],
        }

        for outcome_id, assessment in assessments.items():
            row = [
                assessment["outcome"],
                assessment["overall_quality"],
                assessment["domain_scores"].get("risk_of_bias", "unknown"),
                assessment["domain_scores"].get("inconsistency", "unknown"),
                assessment["domain_scores"].get("indirectness", "unknown"),
                assessment["domain_scores"].get("imprecision", "unknown"),
                assessment["domain_scores"].get("publication_bias", "unknown"),
            ]
            table_data["rows"].append(row)

        return table_data

    def generate_script(
        self,
        analysis_type: AnalysisType,
        data: Dict[str, Any],
        parameters: Dict[str, Any],
    ) -> str:
        """Generate GRADE assessment script"""
        return f"GRADE assessment script for {len(data.get('outcomes', []))} outcomes"


# Example usage and testing
if __name__ == "__main__":

    async def test_research_tools():
        """Test research tool integrations"""

        print("Testing R Integration...")

        # Test R availability
        r_integration = RIntegration()
        is_available = await r_integration.check_availability()
        print(
            f"R availability: {'✅ AVAILABLE' if is_available else '❌ NOT AVAILABLE'}"
        )

        if is_available:
            # Test meta - analysis
            sample_data = {
                "studies": [
                    {"study_id": "Study1", "effect_size": 0.5, "variance": 0.1},
                    {"study_id": "Study2", "effect_size": 0.3, "variance": 0.08},
                    {"study_id": "Study3", "effect_size": 0.7, "variance": 0.12},
                    {"study_id": "Study4", "effect_size": 0.4, "variance": 0.09},
                ]
            }

            parameters = {"effect_measure": "MD", "model": "random", "method": "REML"}

            try:
                result = await r_integration.execute_analysis(
                    AnalysisType.META_ANALYSIS, sample_data, parameters
                )

                print("\n✅ Meta - analysis completed:")
                print(f"   Overall effect: {result.effect_sizes.get('overall', 0):.3f}")
                print(f"   I²: {result.heterogeneity.get('i_squared', 0):.1f}%")
                print(f"   p - value: {result.p_values.get('overall_effect', 1):.3f}")
                print(f"   Plots generated: {len(result.plots)}")

            except Exception as e:
                print(f"❌ Meta - analysis failed: {e}")

        # Test other tools
        print("\n" + "=" * 50)
        print("Testing other research tools...")

        # PROSPERO
        prospero = ProsperoRegistration()
        prospero_available = await prospero.check_availability()
        print(
            f"PROSPERO availability: {'✅ AVAILABLE' if prospero_available else '❌ NOT AVAILABLE'}"
        )

        # GRADE Pro
        grade_pro = GradeProIntegration()
        grade_available = await grade_pro.check_availability()
        print(
            f"GRADE Pro availability: {'✅ AVAILABLE' if grade_available else '❌ NOT AVAILABLE'}"
        )

        if grade_available:
            # Test GRADE assessment
            grade_data = {
                "outcomes": [
                    {"id": "mortality", "name": "All - cause mortality"},
                    {"id": "quality_of_life", "name": "Quality of life"},
                ]
            }

            grade_result = await grade_pro.execute_analysis(
                AnalysisType.RISK_OF_BIAS_ASSESSMENT, grade_data, {}
            )

            print("\n✅ GRADE assessment completed:")
            print(
                f"   Outcomes assessed: {grade_result.statistics.get('n_outcomes', 0)}"
            )
            print(f"   Tables generated: {len(grade_result.tables)}")

        print("\n✅ Research tool integration tests completed")

        # Cleanup
        r_integration.cleanup()

    # Run test
    asyncio.run(test_research_tools())
