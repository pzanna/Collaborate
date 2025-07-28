"""
Data Import / Export Hub for Standardized Data Exchange

This module provides comprehensive data exchange capabilities supporting multiple
formats for importing and exporting systematic review data. It ensures data
integrity, format validation, and seamless conversion between different formats.

Features:
- Multi - format support (CSV, Excel, RIS, BibTeX, JSON, XML)
- Data validation and quality checks
- Format conversion and standardization
- Bulk import / export operations
- Progress tracking for large datasets-Error handling and recovery mechanisms

Author: Eunice AI System
Date: July 2025
"""

import asyncio
import csv
import io
import json
import logging
import re
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataFormat(Enum):
    """Supported data formats"""

    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    XML = "xml"
    RIS = "ris"
    BIBTEX = "bibtex"
    ENDNOTE_XML = "endnote_xml"
    PRISMA_CSV = "prisma_csv"
    COCHRANE_XML = "cochrane_xml"
    ZOTERO_JSON = "zotero_json"
    TSV = "tsv"
    JSONL = "jsonl"


class ExchangeFormat(Enum):
    """Standard exchange formats"""

    SYSTEMATIC_REVIEW_JSON = "systematic_review_json"
    STUDY_METADATA = "study_metadata"
    SCREENING_DECISIONS = "screening_decisions"
    QUALITY_ASSESSMENTS = "quality_assessments"
    EXTRACTED_DATA = "extracted_data"
    PRISMA_FLOW = "prisma_flow"
    REFERENCE_LIBRARY = "reference_library"


class ValidationLevel(Enum):
    """Data validation strictness levels"""

    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"
    NONE = "none"


@dataclass
class DataValidationResult:
    """Data validation result"""

    is_valid: bool
    error_count: int
    warning_count: int
    errors: List[str]
    warnings: List[str]
    corrected_data: Optional[Dict[str, Any]]
    validation_level: ValidationLevel
    timestamp: datetime


@dataclass
class ImportResult:
    """Data import operation result"""

    success: bool
    records_imported: int
    records_failed: int
    total_records: int
    validation_result: DataValidationResult
    imported_data: Dict[str, Any]
    error_log: List[str]
    processing_time: float
    metadata: Dict[str, Any]


@dataclass
class ExportResult:
    """Data export operation result"""

    success: bool
    records_exported: int
    output_file: Optional[str]
    output_data: Optional[str]
    format_type: DataFormat
    validation_result: DataValidationResult
    processing_time: float
    metadata: Dict[str, Any]


class DataValidator:
    """Data validation and quality checking"""

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.validation_level = validation_level
        self.required_fields = {
            "study": ["title", "authors"],
            "screening": ["study_id", "decision"],
            "quality_assessment": ["study_id", "domain", "rating"],
            "extracted_data": ["study_id", "variable", "value"],
        }

    async def validate_data(
        self, data: Dict[str, Any], data_type: str
    ) -> DataValidationResult:
        """Validate data based on type and validation level"""

        datetime.now()
        errors = []
        warnings = []
        corrected_data = None

        try:
            if data_type == "studies":
                errors, warnings, corrected_data = await self._validate_studies(data)
            elif data_type == "screening_decisions":
                errors, warnings, corrected_data = await self._validate_screening(data)
            elif data_type == "quality_assessments":
                errors, warnings, corrected_data = (
                    await self._validate_quality_assessments(data)
                )
            elif data_type == "extracted_data":
                errors, warnings, corrected_data = await self._validate_extracted_data(
                    data
                )
            else:
                warnings.append(f"Unknown data type: {data_type}")

            # Apply validation level filtering
            if self.validation_level == ValidationLevel.LENIENT:
                errors = [e for e in errors if "critical" in e.lower()]
            elif self.validation_level == ValidationLevel.NONE:
                errors = []
                warnings = []

            is_valid = len(errors) == 0

            return DataValidationResult(
                is_valid=is_valid,
                error_count=len(errors),
                warning_count=len(warnings),
                errors=errors,
                warnings=warnings,
                corrected_data=corrected_data,
                validation_level=self.validation_level,
                timestamp=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return DataValidationResult(
                is_valid=False,
                error_count=1,
                warning_count=0,
                errors=[f"Validation failed: {str(e)}"],
                warnings=[],
                corrected_data=None,
                validation_level=self.validation_level,
                timestamp=datetime.now(timezone.utc),
            )

    async def _validate_studies(self, data: Dict[str, Any]) -> tuple:
        """Validate study data"""
        errors = []
        warnings = []
        corrected_data = data.copy()

        studies = data.get("studies", [])
        if not studies:
            errors.append("No studies found in data")
            return errors, warnings, corrected_data

        for i, study in enumerate(studies):
            study_id = study.get("id", f"study_{i}")

            # Check required fields
            if not study.get("title"):
                errors.append(f"Study {study_id}: Missing title")

            if not study.get("authors"):
                warnings.append(f"Study {study_id}: No authors specified")

            # Validate publication year
            year = study.get("publication_year")
            if year:
                try:
                    year_int = int(year)
                    current_year = datetime.now().year
                    if year_int < 1800 or year_int > current_year + 1:
                        warnings.append(
                            f"Study {study_id}: Unusual publication year: {year}"
                        )
                except (ValueError, TypeError):
                    errors.append(
                        f"Study {study_id}: Invalid publication year format: {year}"
                    )

            # Validate DOI format
            doi = study.get("doi")
            if doi and not re.match(r"^10\.\d+/", doi):
                warnings.append(f"Study {study_id}: DOI format may be invalid: {doi}")

            # Check for duplicate studies
            for j, other_study in enumerate(studies[i + 1:], i + 1):
                if study.get("title") == other_study.get("title"):
                    warnings.append(
                        f"Possible duplicate studies: {study_id} and study_{j}"
                    )

        return errors, warnings, corrected_data

    async def _validate_screening(self, data: Dict[str, Any]) -> tuple:
        """Validate screening decision data"""
        errors = []
        warnings = []
        corrected_data = data.copy()

        decisions = data.get("screening_decisions", [])

        valid_decisions = ["include", "exclude", "unclear", "pending"]

        for i, decision in enumerate(decisions):
            decision_id = f"decision_{i}"

            if not decision.get("study_id"):
                errors.append(f"{decision_id}: Missing study_id")

            dec_value = decision.get("decision", "").lower()
            if dec_value not in valid_decisions:
                errors.append(f"{decision_id}: Invalid decision value: {dec_value}")

            # Check for reviewer information
            if not decision.get("reviewer_id"):
                warnings.append(f"{decision_id}: No reviewer specified")

            # Validate timestamp
            timestamp = decision.get("timestamp")
            if timestamp:
                try:
                    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except ValueError:
                    warnings.append(
                        f"{decision_id}: Invalid timestamp format: {timestamp}"
                    )

        return errors, warnings, corrected_data

    async def _validate_quality_assessments(self, data: Dict[str, Any]) -> tuple:
        """Validate quality assessment data"""
        errors = []
        warnings = []
        corrected_data = data.copy()

        assessments = data.get("quality_assessments", [])

        valid_ratings = [
            "low",
            "high",
            "unclear",
            "low_risk",
            "high_risk",
            "unclear_risk",
        ]

        for i, assessment in enumerate(assessments):
            assessment_id = f"assessment_{i}"

            if not assessment.get("study_id"):
                errors.append(f"{assessment_id}: Missing study_id")

            if not assessment.get("domain"):
                errors.append(f"{assessment_id}: Missing assessment domain")

            rating = assessment.get("rating", "").lower()
            if rating and rating not in valid_ratings:
                warnings.append(f"{assessment_id}: Unusual rating value: {rating}")

        return errors, warnings, corrected_data

    async def _validate_extracted_data(self, data: Dict[str, Any]) -> tuple:
        """Validate extracted data"""
        errors = []
        warnings = []
        corrected_data = data.copy()

        extracted = data.get("extracted_data", [])

        for i, extraction in enumerate(extracted):
            extraction_id = f"extraction_{i}"

            if not extraction.get("study_id"):
                errors.append(f"{extraction_id}: Missing study_id")

            if not extraction.get("variable"):
                errors.append(f"{extraction_id}: Missing variable name")

            # Check for reasonable numeric values
            value = extraction.get("value")
            if value and extraction.get("variable_type") == "numeric":
                try:
                    float(value)
                except (ValueError, TypeError):
                    warnings.append(
                        f"{extraction_id}: non-numeric value for numeric variable: {value}"
                    )

        return errors, warnings, corrected_data


class FormatConverter:
    """Convert between different data formats"""

    @staticmethod
    def csv_to_json(
        csv_data: str, headers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Convert CSV data to JSON format"""

        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)

        return {
            "data": rows,
            "headers": reader.fieldnames or headers or [],
            "row_count": len(rows),
        }

    @staticmethod
    def json_to_csv(
        json_data: Dict[str, Any], fields: Optional[List[str]] = None
    ) -> str:
        """Convert JSON data to CSV format"""

        data = json_data.get("data", [])
        if not data:
            return ""

        # Determine fields from data if not provided
        if not fields:
            if isinstance(data[0], dict):
                fields = list(data[0].keys())
            else:
                raise ValueError("Cannot determine CSV fields from data")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()

        for row in data:
            if isinstance(row, dict):
                writer.writerow(row)
            else:
                # Handle list / tuple rows
                row_dict = {
                    fields[i]: row[i] if i < len(row) else ""
                    for i in range(len(fields))
                }
                writer.writerow(row_dict)

        return output.getvalue()

    @staticmethod
    def ris_to_json(ris_data: str) -> Dict[str, Any]:
        """Convert RIS format to JSON"""

        references = []
        current_ref = {}

        for line in ris_data.split("\n"):
            line = line.strip()
            if not line:
                continue

            if line.startswith("TY -"):
                # Start new reference
                if current_ref:
                    references.append(current_ref)
                current_ref = {"type": line[6:]}
            elif line.startswith("ER -"):
                # End reference
                if current_ref:
                    references.append(current_ref)
                    current_ref = {}
            elif "-" in line:
                # Field data
                tag, value = line.split("-", 1)
                tag = tag.strip()
                value = value.strip()

                # Handle multiple values for same tag
                if tag in current_ref:
                    if not isinstance(current_ref[tag], list):
                        current_ref[tag] = [current_ref[tag]]  # type: ignore
                    current_ref[tag].append(value)  # type: ignore
                else:
                    current_ref[tag] = value

        # Add last reference if exists
        if current_ref:
            references.append(current_ref)

        return {"references": references, "count": len(references), "format": "RIS"}

    @staticmethod
    def json_to_ris(json_data: Dict[str, Any]) -> str:
        """Convert JSON to RIS format"""

        references = json_data.get("references", [])
        ris_lines = []

        for ref in references:
            # Reference type
            ref_type = ref.get("type", "JOUR")
            ris_lines.append(f"TY -{ref_type}")

            # Map common fields
            field_mapping = {
                "title": "TI",
                "author": "AU",
                "journal": "JO",
                "year": "PY",
                "volume": "VL",
                "issue": "IS",
                "pages": "SP",
                "doi": "DO",
                "url": "UR",
                "abstract": "AB",
                "keywords": "KW",
            }

            for json_field, ris_tag in field_mapping.items():
                if json_field in ref:
                    value = ref[json_field]
                    if isinstance(value, list):
                        for v in value:
                            ris_lines.append(f"{ris_tag} -{v}")
                    else:
                        ris_lines.append(f"{ris_tag} -{value}")

            # End reference
            ris_lines.append("ER -")
            ris_lines.append("")  # Empty line between references

        return "\n".join(ris_lines)


class ImportEngine:
    """Data import engine with format detection and validation"""

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.validator = DataValidator(validation_level)
        self.converter = FormatConverter()

    async def import_data(
        self,
        data_source: Union[str, Dict[str, Any]],
        format_type: DataFormat,
        exchange_format: ExchangeFormat,
    ) -> ImportResult:
        """Import data from various sources and formats"""

        start_time = datetime.now()

        try:
            # Parse data based on format
            if isinstance(data_source, str):
                if format_type == DataFormat.CSV:
                    parsed_data = self._parse_csv(data_source)
                elif format_type == DataFormat.JSON:
                    parsed_data = json.loads(data_source)
                elif format_type == DataFormat.RIS:
                    parsed_data = self.converter.ris_to_json(data_source)
                elif format_type == DataFormat.XML:
                    parsed_data = self._parse_xml(data_source)
                else:
                    raise ValueError(f"Unsupported format: {format_type}")
            else:
                parsed_data = data_source

            # Transform to exchange format
            transformed_data = await self._transform_to_exchange_format(
                parsed_data, exchange_format
            )

            # Validate data
            data_type = self._get_data_type_from_exchange_format(exchange_format)
            validation_result = await self.validator.validate_data(
                transformed_data, data_type
            )

            # Count records
            records_imported = self._count_records(transformed_data)
            records_failed = validation_result.error_count
            total_records = records_imported + records_failed

            processing_time = (datetime.now()-start_time).total_seconds()

            return ImportResult(
                success=validation_result.is_valid,
                records_imported=records_imported,
                records_failed=records_failed,
                total_records=total_records,
                validation_result=validation_result,
                imported_data=validation_result.corrected_data or transformed_data,
                error_log=validation_result.errors,
                processing_time=processing_time,
                metadata={
                    "source_format": format_type.value,
                    "exchange_format": exchange_format.value,
                    "validation_level": self.validator.validation_level.value,
                },
            )

        except Exception as e:
            processing_time = (datetime.now()-start_time).total_seconds()
            logger.error(f"Import failed: {e}")

            return ImportResult(
                success=False,
                records_imported=0,
                records_failed=0,
                total_records=0,
                validation_result=DataValidationResult(
                    is_valid=False,
                    error_count=1,
                    warning_count=0,
                    errors=[str(e)],
                    warnings=[],
                    corrected_data=None,
                    validation_level=self.validator.validation_level,
                    timestamp=datetime.now(timezone.utc),
                ),
                imported_data={},
                error_log=[str(e)],
                processing_time=processing_time,
                metadata={},
            )

    def _parse_csv(self, csv_data: str) -> Dict[str, Any]:
        """Parse CSV data"""
        return self.converter.csv_to_json(csv_data)

    def _parse_xml(self, xml_data: str) -> Dict[str, Any]:
        """Parse XML data"""
        try:
            root = ET.fromstring(xml_data)

            # Convert XML to dict (simplified)
            def xml_to_dict(element):
                """Convert XML element to dictionary representation.
                
                Args:
                    element: XML element to convert
                    
                Returns:
                    dict: Dictionary representation of the XML element
                """
                result = {}

                # Add attributes
                if element.attrib:
                    result["@attributes"] = element.attrib

                # Add text content
                if element.text and element.text.strip():
                    if len(element) == 0:
                        return element.text.strip()
                    result["#text"] = element.text.strip()

                # Add child elements
                for child in element:
                    child_data = xml_to_dict(child)
                    if child.tag in result:
                        if not isinstance(result[child.tag], list):
                            result[child.tag] = [result[child.tag]]
                        result[child.tag].append(child_data)
                    else:
                        result[child.tag] = child_data

                return result

            return {"root": root.tag, "data": xml_to_dict(root)}

        except ET.ParseError as e:
            raise ValueError(f"Invalid XML data: {e}")

    async def _transform_to_exchange_format(
        self, data: Dict[str, Any], exchange_format: ExchangeFormat
    ) -> Dict[str, Any]:
        """Transform parsed data to standard exchange format"""

        if exchange_format == ExchangeFormat.STUDY_METADATA:
            return await self._transform_to_study_metadata(data)
        elif exchange_format == ExchangeFormat.SCREENING_DECISIONS:
            return await self._transform_to_screening_decisions(data)
        elif exchange_format == ExchangeFormat.REFERENCE_LIBRARY:
            return await self._transform_to_reference_library(data)
        else:
            # Return as-is for unknown formats
            return data

    async def _transform_to_study_metadata(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform data to study metadata format"""

        # Handle different input structures
        if "data" in data and isinstance(data["data"], list):
            # CSV-like data
            studies = []
            for row in data["data"]:
                study = {
                    "id": row.get("id")
                    or row.get("study_id")
                    or f"study_{len(studies)}",
                    "title": row.get("title") or row.get("Title"),
                    "authors": self._parse_authors(
                        row.get("authors") or row.get("Authors", "")
                    ),
                    "publication_year": self._parse_year(
                        row.get("year") or row.get("publication_year")
                    ),
                    "journal": row.get("journal") or row.get("Journal"),
                    "doi": row.get("doi") or row.get("DOI"),
                    "abstract": row.get("abstract") or row.get("Abstract"),
                    "keywords": self._parse_keywords(
                        row.get("keywords") or row.get("Keywords", "")
                    ),
                }
                studies.append(study)

            return {"studies": studies}

        elif "references" in data:
            # RIS-like data
            studies = []
            for ref in data["references"]:
                study = {
                    "id": f"study_{len(studies)}",
                    "title": ref.get("TI") or ref.get("title"),
                    "authors": self._parse_authors_from_list(ref.get("AU", [])),
                    "publication_year": self._parse_year(
                        ref.get("PY") or ref.get("year")
                    ),
                    "journal": ref.get("JO") or ref.get("journal"),
                    "doi": ref.get("DO") or ref.get("doi"),
                    "abstract": ref.get("AB") or ref.get("abstract"),
                    "keywords": self._parse_keywords_from_list(ref.get("KW", [])),
                }
                studies.append(study)

            return {"studies": studies}

        else:
            # Return as-is
            return data

    async def _transform_to_screening_decisions(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform data to screening decisions format"""

        if "data" in data:
            decisions = []
            for row in data["data"]:
                decision = {
                    "study_id": row.get("study_id") or row.get("id"),
                    "decision": row.get("decision") or row.get("include_exclude"),
                    "reviewer_id": row.get("reviewer_id") or row.get("reviewer"),
                    "stage": row.get("stage", "title_abstract"),
                    "notes": row.get("notes") or row.get("comments"),
                    "timestamp": row.get("timestamp")
                    or datetime.now(timezone.utc).isoformat(),
                }
                decisions.append(decision)

            return {"screening_decisions": decisions}

        return data

    async def _transform_to_reference_library(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Transform data to reference library format"""

        if "references" in data:
            # Already in reference format
            return data
        elif "studies" in data:
            # Convert studies to references
            references = []
            for study in data["studies"]:
                ref = {
                    "id": study.get("id"),
                    "type": "JOUR",  # Default to journal article
                    "title": study.get("title"),
                    "authors": study.get("authors", []),
                    "year": study.get("publication_year"),
                    "journal": study.get("journal"),
                    "doi": study.get("doi"),
                    "abstract": study.get("abstract"),
                }
                references.append(ref)

            return {
                "references": references,
                "count": len(references),
                "format": "transformed",
            }

        return data

    def _parse_authors(self, authors_str: str) -> List[str]:
        """Parse author string into list"""
        if not authors_str:
            return []

        # Split by common separators
        separators = [";", ",", " and ", " & "]
        authors = [authors_str]

        for sep in separators:
            new_authors = []
            for author in authors:
                new_authors.extend(author.split(sep))
            authors = new_authors

        # Clean up
        return [author.strip() for author in authors if author.strip()]

    def _parse_authors_from_list(
        self, authors_list: Union[List[str], str]
    ) -> List[str]:
        """Parse authors from list or string"""
        if isinstance(authors_list, list):
            return authors_list
        elif isinstance(authors_list, str):
            return self._parse_authors(authors_list)
        else:
            return []

    def _parse_keywords(self, keywords_str: str) -> List[str]:
        """Parse keywords string into list"""
        if not keywords_str:
            return []

        # Split by common separators
        keywords = keywords_str.split(",")
        if len(keywords) == 1:
            keywords = keywords_str.split(";")

        return [kw.strip() for kw in keywords if kw.strip()]

    def _parse_keywords_from_list(
        self, keywords_list: Union[List[str], str]
    ) -> List[str]:
        """Parse keywords from list or string"""
        if isinstance(keywords_list, list):
            return keywords_list
        elif isinstance(keywords_list, str):
            return self._parse_keywords(keywords_list)
        else:
            return []

    def _parse_year(self, year_str: Union[str, int, None]) -> Optional[int]:
        """Parse publication year"""
        if not year_str:
            return None

        try:
            if isinstance(year_str, int):
                return year_str

            # Extract 4-digit year from string
            year_match = re.search(r"\b(19|20)\d{2}\b", str(year_str))
            if year_match:
                return int(year_match.group())

        except (ValueError, TypeError):
            pass

        return None

    def _get_data_type_from_exchange_format(
        self, exchange_format: ExchangeFormat
    ) -> str:
        """Map exchange format to data type for validation"""
        mapping = {
            ExchangeFormat.STUDY_METADATA: "studies",
            ExchangeFormat.SCREENING_DECISIONS: "screening_decisions",
            ExchangeFormat.QUALITY_ASSESSMENTS: "quality_assessments",
            ExchangeFormat.EXTRACTED_DATA: "extracted_data",
            ExchangeFormat.REFERENCE_LIBRARY: "references",
        }
        return mapping.get(exchange_format, "unknown")

    def _count_records(self, data: Dict[str, Any]) -> int:
        """Count records in transformed data"""

        # Count based on main data arrays
        for key in [
            "studies",
            "screening_decisions",
            "quality_assessments",
            "extracted_data",
            "references",
        ]:
            if key in data and isinstance(data[key], list):
                return len(data[key])

        # Fallback to data array
        if "data" in data and isinstance(data["data"], list):
            return len(data["data"])

        return 0


class ExportEngine:
    """Data export engine with format conversion and validation"""

    def __init__(self):
        self.converter = FormatConverter()
        self.validator = DataValidator(ValidationLevel.LENIENT)

    async def export_data(
        self,
        data: Dict[str, Any],
        format_type: DataFormat,
        output_file: Optional[str] = None,
    ) -> ExportResult:
        """Export data to specified format"""

        start_time = datetime.now()

        try:
            # Validate input data
            data_type = self._infer_data_type(data)
            validation_result = await self.validator.validate_data(data, data_type)

            # Convert to target format
            if format_type == DataFormat.CSV:
                output_data = self._export_csv(data)
            elif format_type == DataFormat.JSON:
                output_data = json.dumps(data, indent=2, default=str)
            elif format_type == DataFormat.RIS:
                output_data = self.converter.json_to_ris(data)
            elif format_type == DataFormat.XML:
                output_data = self._export_xml(data)
            elif format_type == DataFormat.TSV:
                output_data = self._export_tsv(data)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")

            # Write to file if specified
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(output_data)

            # Count exported records
            records_exported = self._count_exported_records(data)

            processing_time = (datetime.now() - start_time).total_seconds()

            return ExportResult(
                success=True,
                records_exported=records_exported,
                output_file=output_file,
                output_data=output_data if not output_file else None,
                format_type=format_type,
                validation_result=validation_result,
                processing_time=processing_time,
                metadata={
                    "data_type": data_type,
                    "file_size": len(output_data.encode("utf-8")),
                },
            )

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Export failed: {e}")

            return ExportResult(
                success=False,
                records_exported=0,
                output_file=None,
                output_data=None,
                format_type=format_type,
                validation_result=DataValidationResult(
                    is_valid=False,
                    error_count=1,
                    warning_count=0,
                    errors=[str(e)],
                    warnings=[],
                    corrected_data=None,
                    validation_level=ValidationLevel.LENIENT,
                    timestamp=datetime.now(timezone.utc),
                ),
                processing_time=processing_time,
                metadata={},
            )

    def _export_csv(self, data: Dict[str, Any]) -> str:
        """Export data as CSV"""

        # Determine main data array
        main_data = None
        for key in [
            "studies",
            "screening_decisions",
            "quality_assessments",
            "extracted_data",
            "references",
            "data",
        ]:
            if key in data and isinstance(data[key], list):
                main_data = data[key]
                break

        if not main_data:
            raise ValueError("No exportable data found")

        if not main_data:
            return ""

        # Flatten nested data and determine fields
        flattened_data = []
        all_fields = set()

        for item in main_data:
            flattened_item = self._flatten_dict(item)
            flattened_data.append(flattened_item)
            all_fields.update(flattened_item.keys())

        # Convert to CSV
        fields = sorted(all_fields)
        return self.converter.json_to_csv({"data": flattened_data}, fields)

    def _export_tsv(self, data: Dict[str, Any]) -> str:
        """Export data as TSV (Tab Separated Values)"""
        csv_data = self._export_csv(data)
        # Convert commas to tabs (simplified approach)
        lines = csv_data.split("\n")
        tsv_lines = []
        for line in lines:
            # This is a simplified conversion-proper CSV parsing would be better
            tsv_line = line.replace(",", "\t")
            tsv_lines.append(tsv_line)

        return "\n".join(tsv_lines)

    def _export_xml(self, data: Dict[str, Any]) -> str:
        """Export data as XML"""

        root = ET.Element("systematic_review_data")

        # Add metadata
        metadata = ET.SubElement(root, "metadata")
        ET.SubElement(metadata, "export_timestamp").text = datetime.now(
            timezone.utc
        ).isoformat()
        ET.SubElement(metadata, "format").text = "xml"

        # Add main data
        for key, value in data.items():
            if isinstance(value, list):
                list_elem = ET.SubElement(root, key)
                for item in value:
                    item_elem = ET.SubElement(
                        list_elem, key[:-1] if key.endswith("s") else "item"
                    )
                    self._dict_to_xml(item, item_elem)
            elif isinstance(value, dict):
                dict_elem = ET.SubElement(root, key)
                self._dict_to_xml(value, dict_elem)
            else:
                ET.SubElement(root, key).text = str(value)

        return ET.tostring(root, encoding="unicode")

    def _dict_to_xml(self, data: Dict[str, Any], parent: ET.Element):
        """Convert dictionary to XML elements"""

        for key, value in data.items():
            if isinstance(value, list):
                for item in value:
                    elem = ET.SubElement(parent, key)
                    if isinstance(item, dict):
                        self._dict_to_xml(item, elem)
                    else:
                        elem.text = str(item)
            elif isinstance(value, dict):
                elem = ET.SubElement(parent, key)
                self._dict_to_xml(value, elem)
            else:
                elem = ET.SubElement(parent, key)
                elem.text = str(value) if value is not None else ""

    def _flatten_dict(self, data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten nested dictionary for CSV export"""

        flattened = {}

        for key, value in data.items():
            full_key = f"{prefix}_{key}" if prefix else key

            if isinstance(value, dict):
                flattened.update(self._flatten_dict(value, full_key))
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    # Handle list of dicts by creating multiple columns
                    for i, item in enumerate(value):
                        flattened.update(self._flatten_dict(item, f"{full_key}_{i}"))
                else:
                    # Handle simple list by joining
                    flattened[full_key] = ", ".join(str(v) for v in value)
            else:
                flattened[full_key] = value

        return flattened

    def _infer_data_type(self, data: Dict[str, Any]) -> str:
        """Infer data type for validation"""

        if "studies" in data:
            return "studies"
        elif "screening_decisions" in data:
            return "screening_decisions"
        elif "quality_assessments" in data:
            return "quality_assessments"
        elif "extracted_data" in data:
            return "extracted_data"
        elif "references" in data:
            return "references"
        else:
            return "unknown"

    def _count_exported_records(self, data: Dict[str, Any]) -> int:
        """Count exported records"""

        for key in [
            "studies",
            "screening_decisions",
            "quality_assessments",
            "extracted_data",
            "references",
            "data",
        ]:
            if key in data and isinstance(data[key], list):
                return len(data[key])

        return 0


class DataExchangeHub:
    """Central hub for data import / export operations"""

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.import_engine = ImportEngine(validation_level)
        self.export_engine = ExportEngine()
        self.temp_dir = tempfile.mkdtemp(prefix="eunice_data_exchange_")

    async def import_from_file(
        self, file_path: str, format_type: DataFormat, exchange_format: ExchangeFormat
    ) -> ImportResult:
        """Import data from file"""

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data_content = f.read()

            return await self.import_engine.import_data(
                data_content, format_type, exchange_format
            )

        except Exception as e:
            logger.error(f"File import failed: {e}")
            raise

    async def export_to_file(
        self, data: Dict[str, Any], file_path: str, format_type: DataFormat
    ) -> ExportResult:
        """Export data to file"""

        return await self.export_engine.export_data(data, format_type, file_path)

    async def convert_format(
        self, input_data: str, input_format: DataFormat, output_format: DataFormat
    ) -> str:
        """Convert data between formats"""

        # Import in input format
        import_result = await self.import_engine.import_data(
            input_data, input_format, ExchangeFormat.SYSTEMATIC_REVIEW_JSON
        )

        if not import_result.success:
            raise ValueError(f"Import failed: {import_result.error_log}")

        # Export in output format
        export_result = await self.export_engine.export_data(
            import_result.imported_data, output_format
        )

        if not export_result.success:
            raise ValueError("Export failed")

        return export_result.output_data or ""

    def cleanup(self):
        """Clean up temporary files"""
        try:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory: {e}")


# Example usage and testing
if __name__ == "__main__":

    async def test_data_exchange():
        """Test data import / export functionality"""

        print("Testing Data Exchange Hub...")

        # Create test data
        sample_csv = """id,title,authors,year,journal,doi
study1,"Systematic Review of AI in Healthcare","Smith J, Doe A",2023,Journal of AI,10.1000 / jai.001
study2,"Machine Learning Applications","Johnson B",2022,ML Review,10.1000 / mlr.002
study3,"Clinical Decision Support Systems","Brown C, Davis D",2024,Clinical Informatics,10.1000 / ci.003"""

        # Initialize data exchange hub
        hub = DataExchangeHub(ValidationLevel.MODERATE)

        try:
            # Test CSV import
            print("\n1. Testing CSV import...")
            import_result = await hub.import_engine.import_data(
                sample_csv, DataFormat.CSV, ExchangeFormat.STUDY_METADATA
            )

            print(f"✅ Import success: {import_result.success}")
            print(f"   Records imported: {import_result.records_imported}")
            print(
                f"   Validation errors: {import_result.validation_result.error_count}"
            )
            print(
                f"   Validation warnings: {import_result.validation_result.warning_count}"
            )

            if import_result.validation_result.warnings:
                print(f"   Warnings: {import_result.validation_result.warnings[:2]}")

            # Test JSON export
            print("\n2. Testing JSON export...")
            json_export = await hub.export_engine.export_data(
                import_result.imported_data, DataFormat.JSON
            )

            print(f"✅ JSON export success: {json_export.success}")
            print(f"   Records exported: {json_export.records_exported}")
            print(f"   Output size: {len(json_export.output_data or '')} characters")

            # Test RIS export
            print("\n3. Testing RIS export...")
            ris_export = await hub.export_engine.export_data(
                import_result.imported_data, DataFormat.RIS
            )

            print(f"✅ RIS export success: {ris_export.success}")
            print(f"   Records exported: {ris_export.records_exported}")

            if ris_export.output_data:
                ris_lines = ris_export.output_data.split("\n")
                print(f"   Sample RIS output: {ris_lines[0:3]}")

            # Test format conversion
            print("\n4. Testing format conversion...")
            converted_ris = await hub.convert_format(
                sample_csv, DataFormat.CSV, DataFormat.RIS
            )

            print("✅ CSV to RIS conversion completed")
            print(f"   Output size: {len(converted_ris)} characters")

            # Test validation levels
            print("\n5. Testing validation levels...")

            # Create data with errors
            bad_csv = """id,title,authors,year
study1,,Smith J,invalid_year
study2,Good Title,Doe A,2023"""

            # Strict validation
            hub_strict = DataExchangeHub(ValidationLevel.STRICT)
            strict_result = await hub_strict.import_engine.import_data(
                bad_csv, DataFormat.CSV, ExchangeFormat.STUDY_METADATA
            )

            print(
                f"   Strict validation errors: {strict_result.validation_result.error_count}"
            )

            # Lenient validation
            hub_lenient = DataExchangeHub(ValidationLevel.LENIENT)
            lenient_result = await hub_lenient.import_engine.import_data(
                bad_csv, DataFormat.CSV, ExchangeFormat.STUDY_METADATA
            )

            print(
                f"   Lenient validation errors: {lenient_result.validation_result.error_count}"
            )

            print("\n✅ Data exchange tests completed successfully")

        except Exception as e:
            print(f"❌ Test failed: {e}")

        finally:
            # Cleanup
            hub.cleanup()

    # Run test
    asyncio.run(test_data_exchange())
