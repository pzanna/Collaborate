"""Response Coordinator V3 – Orchestrates a natural three‑party chat between
user, GPT‑4.1‑mini (provider "openai") and Grok‑3‑mini‑beta (provider "xai").

Key features
------------
• Intent classification and @mention/@baton cue detection
• Semantic relevance scoring with provider profiles
• Inactivity boost for re-engaging silent providers
• Baton bonus for explicitly mentioned or cued providers
• Random jitter for spontaneity
• Veto system (repetition check and context limit exceeded)
• Speaking queue with chaining cue detection for next turn
"""

import os
import sys
import re
import math
import random
from typing import List, Dict, Optional, Any
from collections import defaultdict

# Optional OpenAI dependency for embeddings
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Import project‑level data structures
try:
    from ..models.data_models import Message, ConversationSession
    from ..config.config_manager import ConfigManager
except ImportError:
    # Allow standalone execution when run outside package
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from models.data_models import Message, ConversationSession
    from config.config_manager import ConfigManager


class ResponseCoordinator:
    """Orchestrates a 3‑way conversation among user + 2 AI providers using V3 workflow."""

    # Regex to detect baton hand‑off (case‑insensitive)
    _BATON_PAT = re.compile(
        r"@(?P<mention>\w+)|\b(?:your turn|what do you think|thoughts),?\s+(?P<cued>\w+)",
        re.I,
    )

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

        # Tunable parameters
        self.base_threshold = 0.30          # baseline relevance threshold
        self.inactivity_boost = 0.25        # added to score if provider silent > inactivity_turns
        self.inactivity_turns = 4           # turns since provider last spoke to be considered inactive
        self.baton_bonus = 0.50            # bonus for @mentioned or cued providers
        self.max_consecutive_responses = 2  # cap streaks from the same provider
        self.random_jitter = 0.05           # ± jitter for non‑determinism
        self.context_limit = 50             # max messages to consider for context limit

        # Speaking queue for multi-turn conversations
        self.speaking_queue: List[str] = []
        self.last_speaker: Optional[str] = None

        # Provider‑specific profiles for semantic relevance
        self.provider_profiles = {
            "openai": {
                "keywords": [
                    "code", "programming", "development", "debug", "algorithm",
                    "implementation", "technical", "analysis", "research", "logic",
                    "function", "class", "variable", "syntax", "error", "optimize"
                ],
                "weight": 0.8,
                "description": "Technical assistant specializing in programming, development, and analytical tasks"
            },
            "xai": {
                "keywords": [
                    "creative", "brainstorm", "idea", "innovative", "approach",
                    "opinion", "strategy", "perspective", "imagine", "artistic",
                    "design", "concept", "vision", "inspiration", "original"
                ],
                "weight": 0.8,
                "description": "Creative assistant specializing in ideation, strategy, and innovative thinking"
            },
        }

    # ---------------------------------------------------------------------
    # Public API - V3 Workflow Implementation
    # ---------------------------------------------------------------------
    def coordinate_responses(
        self,
        message: Message,
        context: List[Message],
        available_providers: List[str],
    ) -> List[str]:
        """Return an ordered list of providers using V3 workflow algorithm."""
        
        # Step 1: Analyze user message - classify intent & detect @mentions/baton cues
        intent = self._classify_intent(message.content)
        explicit_mentions = self._extract_mentions(message.content, available_providers)
        
        # Step 2: Score each provider
        provider_scores: Dict[str, float] = {}
        vetoed_providers: set[str] = set()
        
        for provider in available_providers:
            # 2a: Base semantic relevance score
            base_score = self._calculate_semantic_relevance(message, provider, context)
            
            # 2b: Add inactivity boost
            base_score += self._calculate_inactivity_boost(provider, context)
            
            # 2c: Add baton bonus if @mentioned or cued
            if provider in explicit_mentions:
                base_score += self.baton_bonus
            
            # 2d: Add random jitter
            base_score += random.uniform(-self.random_jitter, self.random_jitter)
            
            # 2e: Check veto conditions
            veto = (
                self._check_repetition_veto(message, provider, context) or
                self._check_context_limit_veto(provider, context)
            )
            
            if veto:
                vetoed_providers.add(provider)
            else:
                provider_scores[provider] = max(0.0, min(1.0, base_score))
        
        # Step 3: Build speaking queue
        speaking_queue = self._build_speaking_queue(
            provider_scores, explicit_mentions, available_providers, vetoed_providers
        )
        
        return speaking_queue

    def process_ai_response(
        self, 
        response: str, 
        speaker: str, 
        available_providers: List[str]
    ) -> Optional[str]:
        """Process AI response and detect chaining cues for next turn.
        
        Args:
            response: The AI's response content
            speaker: The provider that gave the response
            available_providers: List of available providers
            
        Returns:
            Provider that should be prepended to queue for next turn, or None
        """
        # Step 5: Update last speaker and detect chaining cue
        self.last_speaker = speaker
        
        # Run detect_chaining_cue on the reply
        cued_provider = self.detect_chaining_cue(response, available_providers)
        
        # If a cue exists and the cued provider != previous speaker
        if cued_provider and cued_provider != speaker:
            return cued_provider
        
        return None

    def update_speaking_queue(self, prepend_provider: str) -> None:
        """Prepend a provider to the speaking queue for the next turn."""
        if prepend_provider in self.speaking_queue:
            self.speaking_queue.remove(prepend_provider)
        self.speaking_queue.insert(0, prepend_provider)

    def detect_chaining_cue(
        self, response: str, available_providers: List[str]
    ) -> Optional[str]:
        """Return provider cued by an AI response, else None."""
        m = self._BATON_PAT.search(response)
        if not m:
            return None
        target = (m.group("mention") or m.group("cued") or "").lower()
        for provider in available_providers:
            if provider.lower() == target:
                return provider
        return None

    def _add_collaboration_context(
        self, provider: str, history: List[Message]
    ) -> str:
        """Generate collaboration context hints for AI providers.
        
        Args:
            provider: The provider that will receive this context
            history: Recent conversation history including AI responses
            
        Returns:
            Collaboration hint string to append to system prompt
        """
        if not history:
            return ""
        
        # Find recent AI messages from other providers
        other_ai_messages = []
        for msg in history[-5:]:  # Look at last 5 messages
            if msg.participant not in ("user", provider) and msg.participant in ["openai", "xai"]:
                other_ai_messages.append(msg)
        
        if not other_ai_messages:
            return ""
        
        # Generate collaboration hints based on context
        hints = []
        
        # Check if other AI asked for this provider's input
        last_ai_msg = other_ai_messages[-1] if other_ai_messages else None
        if last_ai_msg:
            content_lower = last_ai_msg.content.lower()
            provider_mentioned = f"@{provider}" in content_lower or provider in content_lower
            
            if provider_mentioned or any(phrase in content_lower for phrase in [
                "what do you think", "your turn", "thoughts", "input", "perspective"
            ]):
                hints.append(f"Build upon or respond to {last_ai_msg.participant}'s previous message.")
        
        # Encourage building on previous ideas
        if len(other_ai_messages) >= 2:
            hints.append("Consider the previous AI responses and add your unique perspective.")
        elif other_ai_messages:
            hints.append(f"You can reference or build upon {other_ai_messages[-1].participant}'s response if relevant.")
        
        # Provider-specific collaboration style
        if provider == "openai":
            hints.append("Focus on technical accuracy and provide analytical insights to complement creative ideas.")
        elif provider == "xai":
            hints.append("Bring creative perspectives and innovative approaches to technical discussions.")
        
        if hints:
            collaboration_hint = "COLLABORATION CONTEXT: " + " ".join(hints)
            return collaboration_hint
        
        return ""

    # ---------------------------------------------------------------------
    # V3 Workflow Helper Methods
    # ---------------------------------------------------------------------
    def _classify_intent(self, content: str) -> str:
        """Classify the intent of a user message."""
        content_lower = content.lower()
        
        # Question patterns
        if re.search(r'\b(how|what|why|when|where|can you|could you|\?)', content_lower):
            return "question"
        
        # Request patterns  
        if re.search(r'\b(please|help|assist|create|make|build|generate)', content_lower):
            return "request"
        
        # Discussion patterns
        if re.search(r'\b(think|opinion|thoughts|discuss|consider)', content_lower):
            return "discussion"
        
        return "general"

    def _calculate_semantic_relevance(
        self, message: Message, provider: str, context: List[Message]
    ) -> float:
        """Calculate semantic relevance score based on provider profile."""
        if provider not in self.provider_profiles:
            return 0.2  # baseline relevance
        
        profile = self.provider_profiles[provider]
        content_lower = message.content.lower()
        
        # Keyword matching
        keywords = profile["keywords"]
        keyword_hits = sum(1 for keyword in keywords if keyword in content_lower)
        keyword_score = (keyword_hits / len(keywords)) * profile["weight"]
        
        # Question boost (both providers can answer questions)
        question_boost = 0.3 if re.search(r'\b(how|what|why|when|where|\?)', content_lower) else 0.0
        
        # Provider-specific boosts
        if provider == "openai":
            # Technical content boost
            if re.search(r'\b(code|program|function|algorithm|debug|error)', content_lower):
                keyword_score += 0.2
        elif provider == "xai":
            # Creative content boost  
            if re.search(r'\b(creative|idea|design|innovative|brainstorm)', content_lower):
                keyword_score += 0.2
        
        return min(1.0, keyword_score + question_boost)

    def _calculate_inactivity_boost(self, provider: str, context: List[Message]) -> float:
        """Calculate inactivity boost for providers that haven't spoken recently."""
        turns_since = self._turns_since_last(provider, context)
        if turns_since >= self.inactivity_turns:
            return self.inactivity_boost
        return 0.0

    def _check_repetition_veto(
        self, message: Message, provider: str, context: List[Message]
    ) -> bool:
        """Check if provider should be vetoed due to repetitive responses."""
        # Check if provider has responded to very similar queries recently
        if len(context) < 2:
            return False
        
        recent_provider_msgs = [
            m for m in context[-5:] 
            if m.participant == provider
        ]
        
        if len(recent_provider_msgs) < 2:
            return False
        
        # Check for high similarity between recent responses
        for msg in recent_provider_msgs[-2:]:
            similarity = self._calculate_text_similarity(
                message.content.lower(), 
                msg.content.lower()
            )
            if similarity > 0.85:
                return True
        
        return False

    def _check_context_limit_veto(self, provider: str, context: List[Message]) -> bool:
        """Check if provider should be vetoed due to context limits."""
        # Simple implementation: veto if provider has spoken too much recently
        if len(context) < self.context_limit:
            return False
        
        recent_context = context[-self.context_limit:]
        provider_messages = [m for m in recent_context if m.participant == provider]
        
        # Veto if provider has more than 60% of recent messages
        return len(provider_messages) > (self.context_limit * 0.6)

    def _build_speaking_queue(
        self,
        provider_scores: Dict[str, float],
        explicit_mentions: List[str],
        available_providers: List[str],
        vetoed_providers: set[str]
    ) -> List[str]:
        """Build the speaking queue according to V3 algorithm."""
        
        queue: List[str] = []

        # ------------------------------------------------------------------
        # 1. Current speaker selects next (explicit mention / baton cue)
        # ------------------------------------------------------------------
        for provider in explicit_mentions:
            if provider in available_providers and provider not in vetoed_providers:
                queue.append(provider)

        # ------------------------------------------------------------------
        # 2. Self‑selection by providers meeting relevance threshold
        # ------------------------------------------------------------------
        qualified_providers = {
            provider: score
            for provider, score in provider_scores.items()
            if score >= self.base_threshold and provider not in vetoed_providers
        }

        # Remove already queued explicit mentions
        for provider in queue:
            qualified_providers.pop(provider, None)

        if queue:
            # Add remaining qualified providers sorted by score
            remaining = sorted(
                qualified_providers.keys(),
                key=lambda p: qualified_providers[p],
                reverse=True,
            )
            queue.extend(remaining)
            return queue

        # ------------------------------------------------------------------
        # 3. If no one self‑selects, choose highest scoring available provider
        # ------------------------------------------------------------------
        if qualified_providers:
            best_provider = max(qualified_providers.keys(),
                                key=lambda p: qualified_providers[p])
            queue.append(best_provider)
        else:
            # Fallback to any non‑vetoed provider
            non_vetoed = [p for p in available_providers if p not in vetoed_providers]
            if non_vetoed:
                queue.append(non_vetoed[0])

        return queue

    # ---------------------------------------------------------------------
    # Redundancy & similarity checks
    # ---------------------------------------------------------------------
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using embeddings or word overlap."""
        if OPENAI_AVAILABLE:
            try:
                import openai
                vecs = openai.embeddings.create(
                    model="text-embedding-3-small", 
                    input=[text1[:4096], text2[:4096]]
                ).data
                v1, v2 = vecs[0].embedding, vecs[1].embedding
                dot = sum(a * b for a, b in zip(v1, v2))
                norm = lambda v: math.sqrt(sum(x * x for x in v)) + 1e-9
                return dot / (norm(v1) * norm(v2))
            except Exception:
                pass  # fall back to word overlap

        # Word‑overlap fallback
        words1, words2 = set(re.findall(r"\w+", text1)), set(re.findall(r"\w+", text2))
        if not words1 or not words2:
            return 0.0
        return len(words1 & words2) / len(words1 | words2)

    # ---------------------------------------------------------------------
    # Conversation state helpers
    # ---------------------------------------------------------------------
    def _turns_since_last(self, provider: str, context: List[Message]) -> int:
        """Count turns since provider last spoke."""
        for idx, msg in enumerate(reversed(context), 1):
            if msg.participant == provider:
                return idx
        return len(context) + 1  # provider never spoke

    def _has_too_many_consecutive_responses(
        self, provider: str, context: List[Message]
    ) -> bool:
        """Check if provider has exceeded consecutive response limit."""
        streak = 0
        for msg in reversed(context):
            if msg.participant == provider:
                streak += 1
            else:
                break
        return streak >= self.max_consecutive_responses

    # ---------------------------------------------------------------------
    # Mention / baton detection helpers
    # ---------------------------------------------------------------------
    def _extract_mentions(
        self, text: str, available_providers: List[str]
    ) -> List[str]:
        """Extract explicit provider mentions from text."""
        mentions = []
        
        # Check for @mentions and baton cues
        for match in self._BATON_PAT.finditer(text):
            candidate = (match.group("mention") or match.group("cued") or "").lower()
            if candidate in [p.lower() for p in available_providers]:
                # Find the actual provider name (case-sensitive)
                for provider in available_providers:
                    if provider.lower() == candidate:
                        mentions.append(provider)
                        break
        
        # De‑duplicate while preserving order
        seen = set()
        ordered = []
        for provider in mentions:
            if provider not in seen:
                ordered.append(provider)
                seen.add(provider)
        
        return ordered

    # ---------------------------------------------------------------------
    # Stats & configuration helpers (unchanged from V1)
    # ---------------------------------------------------------------------
    def get_response_stats(self, session: ConversationSession) -> Dict[str, Any]:
        stats = {
            "total_messages": len(session.messages),
            "user_messages": 0,
            "ai_responses": defaultdict(int),
            "response_rate": defaultdict(float),
        }
        for m in session.messages:
            if m.participant == "user":
                stats["user_messages"] += 1
            else:
                stats["ai_responses"][m.participant] += 1
        total_ai = sum(stats["ai_responses"].values())
        if total_ai:
            for provider, cnt in stats["ai_responses"].items():
                stats["response_rate"][provider] = cnt / total_ai
        return stats

    def update_settings(self, **kwargs):
        """Update coordinator settings."""
        self.base_threshold = float(kwargs.get("base_threshold", self.base_threshold))
        self.inactivity_boost = float(kwargs.get("inactivity_boost", self.inactivity_boost))
        self.inactivity_turns = int(kwargs.get("inactivity_turns", self.inactivity_turns))
        self.baton_bonus = float(kwargs.get("baton_bonus", self.baton_bonus))
        self.max_consecutive_responses = int(
            kwargs.get("max_consecutive_responses", self.max_consecutive_responses)
        )
        self.random_jitter = float(kwargs.get("random_jitter", self.random_jitter))
        self.context_limit = int(kwargs.get("context_limit", self.context_limit))

    def get_configuration(self) -> Dict[str, Any]:
        """Get current coordinator configuration."""
        return {
            "base_threshold": self.base_threshold,
            "inactivity_boost": self.inactivity_boost,
            "inactivity_turns": self.inactivity_turns,
            "baton_bonus": self.baton_bonus,
            "max_consecutive_responses": self.max_consecutive_responses,
            "random_jitter": self.random_jitter,
            "context_limit": self.context_limit,
            "response_coordination": True,
            "workflow_version": "V3",
        }
