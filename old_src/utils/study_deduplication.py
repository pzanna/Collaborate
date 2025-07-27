"""
Study deduplication and clustering utilities for systematic reviews.

This module provides tools for identifying and removing duplicate studies,
as well as clustering related studies based on various similarity measures.
"""

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Set


@dataclass
class DuplicationMatch:
    """Represents a potential duplicate match between studies."""

    study1_id: str
    study2_id: str
    match_type: str  # 'doi', 'title', 'content_hash', 'title_similarity'
    confidence: float  # 0.0 to 1.0
    details: Dict[str, Any]


@dataclass
class StudyCluster:
    """Represents a cluster of related studies."""

    cluster_id: str
    primary_study_id: str
    related_study_ids: List[str]
    cluster_type: str  # 'duplicate', 'author_overlap', 'topic_similarity'
    confidence: float
    metadata: Dict[str, Any]


class StudyDeduplicator:
    """
    Utility class for identifying and removing duplicate studies.

    Implements multiple deduplication strategies:
    1. Exact DOI matching
    2. Content hash matching
    3. Title similarity matching
    4. Author + year + title fuzzy matching
    """

    def __init__(
        self,
        title_similarity_threshold: float = 0.9,
        fuzzy_match_threshold: float = 0.85,
    ):
        """
        Initialize the deduplicator.

        Args:
            title_similarity_threshold: Minimum similarity for title matching
            fuzzy_match_threshold: Minimum similarity for fuzzy matching
        """
        self.title_similarity_threshold = title_similarity_threshold
        self.fuzzy_match_threshold = fuzzy_match_threshold

    def deduplicate_studies(self, studies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Remove duplicates from a list of studies.

        Args:
            studies: List of study records

        Returns:
            Dict containing unique studies and duplication information
        """
        if not studies:
            return {
                "unique_studies": [],
                "duplicates": [],
                "duplicate_pairs": [],
                "duplicates_removed": 0,
            }

        # Track matches and duplicates
        duplicate_matches = []
        duplicate_ids = set()

        # Strategy 1: DOI matching
        doi_matches = self._find_doi_duplicates(studies)
        duplicate_matches.extend(doi_matches)
        for match in doi_matches:
            duplicate_ids.add(match.study2_id)

        # Strategy 2: Content hash matching
        hash_matches = self._find_hash_duplicates(studies)
        duplicate_matches.extend(hash_matches)
        for match in hash_matches:
            duplicate_ids.add(match.study2_id)

        # Strategy 3: Title similarity matching
        title_matches = self._find_title_duplicates(studies)
        duplicate_matches.extend(title_matches)
        for match in title_matches:
            if match.confidence >= self.title_similarity_threshold:
                duplicate_ids.add(match.study2_id)

        # Strategy 4: Fuzzy matching (author + year + title)
        fuzzy_matches = self._find_fuzzy_duplicates(studies)
        duplicate_matches.extend(fuzzy_matches)
        for match in fuzzy_matches:
            if match.confidence >= self.fuzzy_match_threshold:
                duplicate_ids.add(match.study2_id)

        # Separate unique studies from duplicates
        unique_studies = []
        duplicates = []

        for study in studies:
            study_id = study.get("id", "")
            if study_id not in duplicate_ids:
                unique_studies.append(study)
            else:
                duplicates.append(study)

        return {
            "unique_studies": unique_studies,
            "duplicates": duplicates,
            "duplicate_pairs": duplicate_matches,
            "duplicates_removed": len(duplicates),
            "deduplication_summary": self._create_deduplication_summary(
                duplicate_matches
            ),
        }

    def _find_doi_duplicates(
        self, studies: List[Dict[str, Any]]
    ) -> List[DuplicationMatch]:
        """Find duplicates based on DOI matching."""
        matches = []
        doi_map = {}

        for study in studies:
            doi = self._extract_doi(study)
            if doi:
                doi_normalized = self._normalize_doi(doi)
                if doi_normalized in doi_map:
                    # Found duplicate
                    original_study = doi_map[doi_normalized]
                    match = DuplicationMatch(
                        study1_id=original_study.get("id", ""),
                        study2_id=study.get("id", ""),
                        match_type="doi",
                        confidence=1.0,
                        details={
                            "doi": doi_normalized,
                            "original_title": original_study.get("title", ""),
                            "duplicate_title": study.get("title", ""),
                        },
                    )
                    matches.append(match)
                else:
                    doi_map[doi_normalized] = study

        return matches

    def _find_hash_duplicates(
        self, studies: List[Dict[str, Any]]
    ) -> List[DuplicationMatch]:
        """Find duplicates based on content hash matching."""
        matches = []
        hash_map = {}

        for study in studies:
            content_hash = study.get("content_hash")
            if not content_hash:
                content_hash = self._calculate_content_hash(study)

            if content_hash in hash_map:
                # Found duplicate
                original_study = hash_map[content_hash]
                match = DuplicationMatch(
                    study1_id=original_study.get("id", ""),
                    study2_id=study.get("id", ""),
                    match_type="content_hash",
                    confidence=1.0,
                    details={
                        "hash": content_hash,
                        "original_title": original_study.get("title", ""),
                        "duplicate_title": study.get("title", ""),
                    },
                )
                matches.append(match)
            else:
                hash_map[content_hash] = study

        return matches

    def _find_title_duplicates(
        self, studies: List[Dict[str, Any]]
    ) -> List[DuplicationMatch]:
        """Find duplicates based on title similarity."""
        matches = []

        for i, study1 in enumerate(studies):
            title1 = self._normalize_title(study1.get("title", ""))
            if not title1:
                continue

            for j, study2 in enumerate(studies[i + 1:], i + 1):
                title2 = self._normalize_title(study2.get("title", ""))
                if not title2:
                    continue

                similarity = self._calculate_title_similarity(title1, title2)
                if similarity >= self.title_similarity_threshold:
                    match = DuplicationMatch(
                        study1_id=study1.get("id", ""),
                        study2_id=study2.get("id", ""),
                        match_type="title_similarity",
                        confidence=similarity,
                        details={
                            "title1": title1,
                            "title2": title2,
                            "similarity_score": similarity,
                        },
                    )
                    matches.append(match)

        return matches

    def _find_fuzzy_duplicates(
        self, studies: List[Dict[str, Any]]
    ) -> List[DuplicationMatch]:
        """Find duplicates using fuzzy matching of author + year + title."""
        matches = []

        for i, study1 in enumerate(studies):
            signature1 = self._create_study_signature(study1)
            if not signature1:
                continue

            for j, study2 in enumerate(studies[i + 1:], i + 1):
                signature2 = self._create_study_signature(study2)
                if not signature2:
                    continue

                similarity = self._calculate_signature_similarity(
                    signature1, signature2
                )
                if similarity >= self.fuzzy_match_threshold:
                    match = DuplicationMatch(
                        study1_id=study1.get("id", ""),
                        study2_id=study2.get("id", ""),
                        match_type="fuzzy_match",
                        confidence=similarity,
                        details={
                            "signature1": signature1,
                            "signature2": signature2,
                            "similarity_score": similarity,
                        },
                    )
                    matches.append(match)

        return matches

    def _extract_doi(self, study: Dict[str, Any]) -> Optional[str]:
        """Extract DOI from study record."""
        # Check multiple possible DOI fields
        doi_fields = ["doi", "DOI"]

        for field in doi_fields:
            doi = study.get(field)
            if doi:
                return doi

        # Check metadata
        metadata = study.get("metadata", {})
        for field in doi_fields:
            doi = metadata.get(field)
            if doi:
                return doi

        # Check if DOI is embedded in URL
        url = study.get("url", "")
        if "doi.org" in url:
            # Extract DOI from URL like https://doi.org / 10.1000 / xyz
            doi_match = re.search(r"doi\.org/(.+)", url)
            if doi_match:
                return doi_match.group(1)

        return None

    def _normalize_doi(self, doi: str) -> str:
        """Normalize DOI for comparison."""
        # Remove common prefixes and clean up
        doi = doi.strip()
        if doi.startswith("doi:"):
            doi = doi[4:].strip()
        if doi.startswith("DOI:"):
            doi = doi[4:].strip()
        if doi.startswith("https://doi.org/"):
            doi = doi[16:].strip()
        if doi.startswith("http://doi.org/"):
            doi = doi[15:].strip()

        return doi.lower()

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        if not title:
            return ""

        # Convert to lowercase and remove extra whitespace
        normalized = re.sub(r"\s+", " ", title.lower().strip())

        # Remove common punctuation
        normalized = re.sub(r"[^\w\s]", "", normalized)

        # Remove common stop words that don't affect content
        stop_words = {
            "a",
            "an",
            "and",
            "the",
            "of",
            "for",
            "in",
            "on",
            "at",
            "to",
            "by",
        }
        words = normalized.split()
        words = [word for word in words if word not in stop_words]

        return " ".join(words)

    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles."""
        if not title1 or not title2:
            return 0.0

        # Use sequence matcher for similarity
        return SequenceMatcher(None, title1, title2).ratio()

    def _create_study_signature(self, study: Dict[str, Any]) -> Optional[str]:
        """Create a signature for fuzzy matching."""
        title = self._normalize_title(study.get("title", ""))
        authors = study.get("authors", [])
        year = study.get("year")

        if not title:
            return None

        # Create author signature (first author + last author)
        author_sig = ""
        if authors:
            if len(authors) >= 1:
                author_sig += self._normalize_author_name(authors[0])
            if len(authors) >= 2:
                author_sig += self._normalize_author_name(authors[-1])

        # Combine components
        signature_parts = [title]
        if author_sig:
            signature_parts.append(author_sig)
        if year:
            signature_parts.append(str(year))

        return " ".join(signature_parts)

    def _normalize_author_name(self, author: str) -> str:
        """Normalize author name for comparison."""
        if not author:
            return ""

        # Remove common suffixes and prefixes
        name = re.sub(r"\b(dr|prof|md|phd|jr|sr)\b\.?", "", author.lower())

        # Extract last name (assuming last word is surname)
        words = name.strip().split()
        if words:
            return words[-1]

        return ""

    def _calculate_signature_similarity(self, sig1: str, sig2: str) -> float:
        """Calculate similarity between study signatures."""
        if not sig1 or not sig2:
            return 0.0

        return SequenceMatcher(None, sig1, sig2).ratio()

    def _calculate_content_hash(self, study: Dict[str, Any]) -> str:
        """Calculate content hash for a study."""
        # Create normalized content for hashing
        normalized_content = {
            "title": self._normalize_title(study.get("title", "")),
            "authors": sorted(
                [self._normalize_author_name(a) for a in study.get("authors", [])]
            ),
            "year": study.get("year"),
        }

        content_str = json.dumps(normalized_content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def _create_deduplication_summary(
        self, matches: List[DuplicationMatch]
    ) -> Dict[str, Any]:
        """Create a summary of deduplication results."""
        summary = {
            "total_matches": len(matches),
            "by_type": defaultdict(int),
            "high_confidence_matches": 0,
            "medium_confidence_matches": 0,
            "low_confidence_matches": 0,
        }

        for match in matches:
            summary["by_type"][match.match_type] += 1

            if match.confidence >= 0.95:
                summary["high_confidence_matches"] += 1
            elif match.confidence >= 0.8:
                summary["medium_confidence_matches"] += 1
            else:
                summary["low_confidence_matches"] += 1

        # Convert defaultdict to regular dict
        summary["by_type"] = dict(summary["by_type"])

        return summary


class StudyClusterer:
    """
    Utility class for clustering related studies.

    Clusters studies based on:
    1. Author overlap
    2. Topic similarity (keyword / abstract analysis)
    3. Citation relationships
    """

    def __init__(self, min_author_overlap: int = 1, min_cluster_size: int = 2):
        """
        Initialize the clusterer.

        Args:
            min_author_overlap: Minimum number of shared authors for clustering
            min_cluster_size: Minimum number of studies in a cluster
        """
        self.min_author_overlap = min_author_overlap
        self.min_cluster_size = min_cluster_size

    def cluster_studies(self, studies: List[Dict[str, Any]]) -> List[StudyCluster]:
        """
        Cluster related studies.

        Args:
            studies: List of study records

        Returns:
            List of study clusters
        """
        if len(studies) < self.min_cluster_size:
            return []

        clusters = []

        # Author-based clustering
        author_clusters = self._cluster_by_authors(studies)
        clusters.extend(author_clusters)

        # Topic-based clustering (simplified)
        topic_clusters = self._cluster_by_topics(studies)
        clusters.extend(topic_clusters)

        return clusters

    def _cluster_by_authors(self, studies: List[Dict[str, Any]]) -> List[StudyCluster]:
        """Cluster studies by author overlap."""
        clusters = []
        clustered_studies = set()

        for i, study in enumerate(studies):
            if study.get("id", "") in clustered_studies:
                continue

            study_authors = set(self._normalize_authors(study.get("authors", [])))
            if not study_authors:
                continue

            cluster_studies = [study]
            related_ids = []
            max_overlap = 0
            shared_authors_set = set()

            for j, other_study in enumerate(studies[i + 1:], i + 1):
                if other_study.get("id", "") in clustered_studies:
                    continue

                other_authors = set(
                    self._normalize_authors(other_study.get("authors", []))
                )
                if not other_authors:
                    continue

                # Check for author overlap
                overlap = len(study_authors & other_authors)
                if overlap >= self.min_author_overlap:
                    cluster_studies.append(other_study)
                    related_ids.append(other_study.get("id", ""))
                    clustered_studies.add(other_study.get("id", ""))

                    # Track maximum overlap for confidence calculation
                    if overlap > max_overlap:
                        max_overlap = overlap
                        shared_authors_set = study_authors & other_authors

            # Create cluster if minimum size is met
            if len(cluster_studies) >= self.min_cluster_size:
                confidence = (
                    min(1.0, max_overlap / len(study_authors)) if study_authors else 0.5
                )

                cluster = StudyCluster(
                    cluster_id=f"auth_cluster_{len(clusters) + 1}",
                    primary_study_id=study.get("id", ""),
                    related_study_ids=related_ids,
                    cluster_type="author_overlap",
                    confidence=confidence,
                    metadata={
                        "shared_authors": list(shared_authors_set),
                        "cluster_size": len(cluster_studies),
                        "max_overlap": max_overlap,
                    },
                )
                clusters.append(cluster)
                clustered_studies.add(study.get("id", ""))

        return clusters

    def _cluster_by_topics(self, studies: List[Dict[str, Any]]) -> List[StudyCluster]:
        """Cluster studies by topic similarity (simplified implementation)."""
        # This is a simplified implementation
        # In a full implementation, you would use more sophisticated NLP techniques
        clusters = []

        # Group studies by common keywords in titles / abstracts
        keyword_groups = defaultdict(list)

        for study in studies:
            keywords = self._extract_keywords(study)
            for keyword in keywords:
                keyword_groups[keyword].append(study)

        # Create clusters from keyword groups
        for keyword, group_studies in keyword_groups.items():
            if len(group_studies) >= self.min_cluster_size:
                primary_study = group_studies[0]
                related_ids = [s.get("id", "") for s in group_studies[1:]]

                cluster = StudyCluster(
                    cluster_id=f"topic_cluster_{keyword}_{len(clusters) + 1}",
                    primary_study_id=primary_study.get("id", ""),
                    related_study_ids=related_ids,
                    cluster_type="topic_similarity",
                    confidence=0.7,  # Simplified confidence score
                    metadata={
                        "shared_keyword": keyword,
                        "cluster_size": len(group_studies),
                    },
                )
                clusters.append(cluster)

        return clusters

    def _normalize_authors(self, authors: List[str]) -> List[str]:
        """Normalize author names for comparison."""
        normalized = []
        for author in authors:
            if author:
                # Simple normalization-just lowercase and strip
                normalized.append(author.lower().strip())
        return normalized

    def _extract_keywords(self, study: Dict[str, Any]) -> Set[str]:
        """Extract keywords from study title and abstract."""
        keywords = set()

        # Extract from title
        title = study.get("title", "")
        if title:
            # Simple keyword extraction-split on common separators
            title_words = re.findall(r"\b\w{4,}\b", title.lower())
            keywords.update(title_words)

        # Extract from abstract
        abstract = study.get("abstract", "")
        if abstract:
            # Extract meaningful words from abstract
            abstract_words = re.findall(r"\b\w{5,}\b", abstract.lower())
            keywords.update(abstract_words[:10])  # Limit to first 10 words

        # Filter out common stop words
        stop_words = {
            "study",
            "analysis",
            "research",
            "method",
            "result",
            "conclusion",
            "background",
            "objective",
            "design",
            "setting",
            "participant",
        }
        keywords = keywords-stop_words

        return keywords


if __name__ == "__main__":
    # Test the deduplication utilities

    # Sample studies for testing
    test_studies = [
        {
            "id": "study_001",
            "title": "Effects of AI on Medical Diagnosis",
            "authors": ["Smith, J.", "Johnson, A."],
            "year": 2023,
            "doi": "10.1000 / test1",
            "source": "pubmed",
        },
        {
            "id": "study_002",
            "title": "Effects of AI on Medical Diagnosis",  # Exact duplicate
            "authors": ["Smith, J.", "Johnson, A."],
            "year": 2023,
            "doi": "10.1000 / test1",
            "source": "semantic_scholar",
        },
        {
            "id": "study_003",
            "title": "AI Applications in Healthcare Diagnostics",  # Similar title
            "authors": ["Brown, M.", "Davis, K."],
            "year": 2023,
            "source": "crossref",
        },
        {
            "id": "study_004",
            "title": "Machine Learning for Cancer Detection",
            "authors": ["Smith, J.", "Wilson, R."],  # Shared author
            "year": 2022,
            "source": "pubmed",
        },
    ]

    # Test deduplication
    deduplicator = StudyDeduplicator()
    dedup_results = deduplicator.deduplicate_studies(test_studies)

    print("Deduplication Results:")
    print(f"Original studies: {len(test_studies)}")
    print(f"Unique studies: {len(dedup_results['unique_studies'])}")
    print(f"Duplicates removed: {dedup_results['duplicates_removed']}")
    print(f"Duplicate pairs found: {len(dedup_results['duplicate_pairs'])}")

    for match in dedup_results["duplicate_pairs"]:
        print(
            f"  {match.match_type}: {match.study1_id} -> {match.study2_id} (confidence: {match.confidence:.2f})"
        )

    print("\nDeduplication Summary:")
    print(json.dumps(dedup_results["deduplication_summary"], indent=2))

    # Test clustering
    clusterer = StudyClusterer()
    clusters = clusterer.cluster_studies(test_studies)

    print("\nClustering Results:")
    print(f"Clusters found: {len(clusters)}")

    for cluster in clusters:
        print(
            f"  {cluster.cluster_type}: {cluster.primary_study_id} + {len(cluster.related_study_ids)} related"
        )
        print(f"    Confidence: {cluster.confidence:.2f}")
        print(f"    Metadata: {cluster.metadata}")
