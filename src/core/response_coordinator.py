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
        self.inactivity_turns = 2           # turns since provider last spoke to be considered inactive
        self.baton_bonus = 0.50            # bonus for @mentioned or cued providers
        self.max_consecutive_responses = 2  # cap streaks from the same provider
        self.random_jitter = 0.05           # ± jitter for non‑determinism
        self.context_limit = 50             # max messages to consider for context limit
        
        # Natural conversation flow parameters
        self.close_score_threshold = 0.15   # threshold for allowing multiple responses
        self.urgent_response_threshold = 0.6 # threshold for urgent/interruption responses
        self.conversation_energy_weight = 0.3 # weight for conversation momentum
        self.enable_interruptions = True    # allow conversational interruptions
        self.enable_multi_response = True   # allow multiple AIs to respond when appropriate

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
        """Return an ordered list of providers using enhanced natural flow algorithm."""
        
        # Step 1: Check for immediate conversation repair needs
        repair_provider = self.detect_conversation_repair_needs(context)
        if repair_provider and repair_provider in available_providers:
            return [repair_provider]
        
        # Step 2: Analyze user message - classify intent & detect @mentions/baton cues
        intent = self._classify_intent(message.content)
        explicit_mentions = self._extract_mentions(message.content, available_providers)
        
        # Step 3: Check for interruption opportunities
        interruption_scores = self.detect_interruption_opportunity(message, context)
        
        # Step 4: Calculate conversational momentum
        momentum_scores = self.calculate_conversational_momentum(message, context)
        
        # Step 5: Score each provider with enhanced natural flow factors
        provider_scores: Dict[str, float] = {}
        vetoed_providers: set[str] = set()
        
        for provider in available_providers:
            # 5a: Base semantic relevance score
            base_score = self._calculate_semantic_relevance(message, provider, context)
            
            # 5b: Add inactivity boost
            base_score += self._calculate_inactivity_boost(provider, context)
            
            # 5c: Add baton bonus if @mentioned or cued
            if provider in explicit_mentions:
                base_score += self.baton_bonus
            
            # 5d: Add interruption opportunity score
            base_score += interruption_scores.get(provider, 0.0)
            
            # 5e: Add conversational momentum
            base_score += momentum_scores.get(provider, 0.0) * 0.3
            
            # 5f: Add random jitter (reduced to allow for more natural factors)
            base_score += random.uniform(-self.random_jitter/2, self.random_jitter/2)
            
            # 5g: Check veto conditions
            veto = (
                self._check_repetition_veto(message, provider, context) or
                self._check_context_limit_veto(provider, context)
            )
            
            if veto:
                vetoed_providers.add(provider)
            else:
                provider_scores[provider] = max(0.0, min(1.0, base_score))
        
        # Step 6: Build speaking queue with natural flow considerations
        speaking_queue = self._build_natural_speaking_queue(
            provider_scores, explicit_mentions, available_providers, 
            vetoed_providers, context, intent
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
        """Generate natural collaboration context hints for AI providers.
        
        Args:
            provider: The provider that will receive this context
            history: Recent conversation history including AI responses
            
        Returns:
            Natural collaboration hint string to append to system prompt
        """
        if not history:
            return ""
        
        # Analyze conversation dynamics
        other_ai_messages = []
        user_messages = []
        for msg in history[-5:]:  # Look at last 5 messages
            if msg.participant not in ("user", provider) and msg.participant in ["openai", "xai"]:
                other_ai_messages.append(msg)
            elif msg.participant == "user":
                user_messages.append(msg)
        
        if not other_ai_messages and not user_messages:
            return ""
        
        # Generate natural collaboration hints
        hints = []
        
        # Analyze the conversation energy and flow
        conversation_energy = self._assess_conversation_energy(history)
        
        # Check what the other AI recently said
        last_ai_msg = other_ai_messages[-1] if other_ai_messages else None
        if last_ai_msg:
            content_lower = last_ai_msg.content.lower()
            provider_mentioned = f"@{provider}" in content_lower or provider in content_lower
            
            # Detect conversation patterns
            if provider_mentioned or any(
                phrase in content_lower
                for phrase in ["what do you think", "your turn", "thoughts", "input", "perspective"]
            ):
                hints.append(
                    f"Respond directly to {last_ai_msg.participant}'s question or comment."
                )
                if conversation_energy == "high":
                    hints.append("Keep your response concise since the conversation is moving quickly.")
                
            elif re.search(r'\b(disagree|different|alternative|however|but)\b', content_lower):
                hints.append(
                    f"{last_ai_msg.participant} offered a different perspective. You can agree, disagree, or add nuance."
                )
                
            elif re.search(r'\b(build|expand|add|furthermore|also)\b', content_lower):
                hints.append(
                    f"Build upon {last_ai_msg.participant}'s ideas with your own insights."
                )
                
            else:
                # General response to other AI
                snippet = self._short_snippet(last_ai_msg.content)
                hints.append(
                    f"{last_ai_msg.participant} said: '{snippet}'. Feel free to respond naturally as you would in a conversation."
                )
        
        # Check user's recent patterns
        if user_messages:
            last_user_msg = user_messages[-1]
            if re.search(r'\b(confused|unclear|don\'t understand)\b', last_user_msg.content.lower()):
                hints.append("The user seems confused - provide clear, helpful clarification.")
            elif "?" in last_user_msg.content and len(last_user_msg.content.split()) < 10:
                hints.append("This is a direct question - give a focused, direct answer.")
        
        # Conversation flow guidance
        if conversation_energy == "low":
            hints.append("Feel free to ask follow-up questions to engage the conversation.")
        elif conversation_energy == "high":
            hints.append("The conversation is active - be responsive and build on what's been said.")
        
        # Natural conversation behaviors
        natural_behaviors = [
            "Use the other AI's name when directly responding to them",
            "Feel free to disagree respectfully or offer alternative perspectives",
            "Ask questions if something needs clarification",
            "Acknowledge good points made by others"
        ]
        
        # Provider-specific collaboration style
        if provider == "openai":
            hints.append("Bring analytical rigor and technical depth to complement creative insights.")
            if last_ai_msg and "creative" in last_ai_msg.content.lower():
                hints.append("Help evaluate or implement the creative ideas being discussed.")
        elif provider == "xai":
            hints.append("Offer innovative angles and creative approaches to complement analytical insights.")
            if last_ai_msg and any(word in last_ai_msg.content.lower() for word in ["technical", "code", "algorithm"]):
                hints.append("Consider the broader implications or alternative approaches to the technical discussion.")
        
        # Add one natural behavior tip
        hints.append(random.choice(natural_behaviors))
        
        if hints:
            collaboration_hint = "COLLABORATION CONTEXT: " + " ".join(hints)
            return collaboration_hint
        
        return ""

    def _assess_conversation_energy(self, history: List[Message]) -> str:
        """Assess the energy level of the conversation."""
        if len(history) < 3:
            return "low"
        
        recent_messages = history[-6:]  # Look at last 6 messages
        
        # Count different participants in recent messages
        participants = set(msg.participant for msg in recent_messages)
        
        # Count rapid exchanges (messages within short intervals)
        rapid_exchanges = 0
        for i in range(1, len(recent_messages)):
            # Simple heuristic - short messages or frequent participant changes
            if (len(recent_messages[i].content.split()) < 15 or 
                recent_messages[i].participant != recent_messages[i-1].participant):
                rapid_exchanges += 1
        
        # Determine energy level
        if len(participants) >= 3 and rapid_exchanges >= 3:
            return "high"
        elif len(participants) >= 2 and rapid_exchanges >= 2:
            return "medium"
        else:
            return "low"

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
            if re.search(r'\b(code|program|function|algorithm|debug|error|implementation|technical)', content_lower):
                keyword_score += 0.2
        elif provider == "xai":
            # Creative content boost  
            if re.search(r'\b(creative|idea|design|innovative|brainstorm|user|experience)', content_lower):
                keyword_score += 0.2
        
        # Multi-expertise detection - boost both if request explicitly asks for multiple perspectives
        if re.search(r'\b(both|different|multiple|various|all|perspectives|approaches|viewpoints)\b', content_lower):
            keyword_score += 0.25
        
        # Questions asking for comparison or pros/cons
        if re.search(r'\b(pros? and cons?|compare|versus|vs|trade-?offs?|advantages?)\b', content_lower):
            keyword_score += 0.3
        
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

    def _short_snippet(self, text: str, word_limit: int = 12) -> str:
        """Return a short snippet of text for context hints."""
        words = re.findall(r"\w+", text)
        snippet = " ".join(words[:word_limit])
        if len(words) > word_limit:
            snippet += "..."
        return snippet

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
            "close_score_threshold": self.close_score_threshold,
            "urgent_response_threshold": self.urgent_response_threshold,
            "conversation_energy_weight": self.conversation_energy_weight,
            "enable_interruptions": self.enable_interruptions,
            "enable_multi_response": self.enable_multi_response,
            "response_coordination": True,
            "workflow_version": "V3-Natural",
        }

    # ---------------------------------------------------------------------
    # Conversational Dynamics - Natural Flow Enhancements
    # ---------------------------------------------------------------------
    
    def detect_interruption_opportunity(
        self, message: Message, context: List[Message]
    ) -> Dict[str, float]:
        """Detect if message creates natural interruption opportunities."""
        content_lower = message.content.lower()
        
        interruption_scores = {}
        
        # Strong interruption cues
        strong_cues = [
            r'wait', r'actually', r'hold on', r'but', r'however',
            r'on the other hand', r'i disagree', r'that\'s not right'
        ]
        
        # Question that begs immediate response
        urgent_question_patterns = [
            r'what do you think\?', r'right\?', r'correct\?', 
            r'am i wrong\?', r'does that make sense\?'
        ]
        
        # Incomplete thought patterns
        incomplete_patterns = [
            r'\.\.\.', r'but i think', r'although', r'unless'
        ]
        
        for provider in ["openai", "xai"]:
            score = 0.0
            
            # Check for strong interruption cues
            for pattern in strong_cues:
                if re.search(pattern, content_lower):
                    score += 0.3
            
            # Check for urgent questions
            for pattern in urgent_question_patterns:
                if re.search(pattern, content_lower):
                    score += 0.4
                    
            # Check for incomplete thoughts
            for pattern in incomplete_patterns:
                if re.search(pattern, content_lower):
                    score += 0.2
            
            # Reduce score if provider was last speaker (avoid immediate back-and-forth)
            if context and context[-1].participant == provider:
                score *= 0.5
            
            interruption_scores[provider] = min(1.0, score)
        
        return interruption_scores

    def detect_conversation_repair_needs(
        self, context: List[Message]
    ) -> Optional[str]:
        """Detect if conversation needs repair (clarification, misunderstanding)."""
        if len(context) < 2:
            return None
            
        recent_messages = context[-3:]
        
        # Look for confusion indicators
        confusion_patterns = [
            r'i don\'t understand', r'unclear', r'confusing',
            r'what do you mean', r'could you clarify', r'lost me',
            r'confused', r'explain.*more.*clearly', r'don\'t get it'
        ]
        
        for msg in recent_messages:
            content_lower = msg.content.lower()
            for pattern in confusion_patterns:
                if re.search(pattern, content_lower):
                    # Find who can best clarify
                    if msg.participant == "user":
                        # User is confused - get the AI who last explained something technical
                        for prev_msg in reversed(context[:-1]):
                            if prev_msg.participant in ["openai", "xai"]:
                                # Prefer the one who was explaining the confusing topic
                                return prev_msg.participant
                    elif msg.participant in ["openai", "xai"]:
                        # AI is confused - get the other AI to help
                        return "xai" if msg.participant == "openai" else "openai"
        
        return None

    def calculate_conversational_momentum(
        self, message: Message, context: List[Message]
    ) -> Dict[str, float]:
        """Calculate natural conversation momentum for each provider."""
        momentum_scores = {}
        
        for provider in ["openai", "xai"]:
            score = 0.0
            
            # Check if provider was mentioned in last few messages
            for msg in context[-3:]:
                if f"@{provider}" in msg.content.lower() or provider in msg.content.lower():
                    score += 0.3
            
            # Check for topic continuity
            if self._has_topic_continuity(message, provider, context):
                score += 0.2
            
            # Check for unanswered questions directed at provider
            if self._has_unanswered_questions(provider, context):
                score += 0.4
            
            # Check conversation energy - rapid back-and-forth indicates high engagement
            if self._has_high_conversation_energy(context):
                score += 0.1
            
            momentum_scores[provider] = min(1.0, score)
            
        return momentum_scores

    def _has_topic_continuity(
        self, message: Message, provider: str, context: List[Message]
    ) -> bool:
        """Check if provider's expertise aligns with ongoing topic thread."""
        if provider not in self.provider_profiles:
            return False
            
        profile_keywords = self.provider_profiles[provider]["keywords"]
        
        # Check current message and last 2 messages for topic keywords
        recent_content = message.content.lower()
        for msg in context[-2:]:
            recent_content += " " + msg.content.lower()
        
        keyword_matches = sum(1 for keyword in profile_keywords if keyword in recent_content)
        return keyword_matches >= 2

    def _has_unanswered_questions(self, provider: str, context: List[Message]) -> bool:
        """Check if there are questions directed at provider that remain unanswered."""
        for msg in reversed(context[-5:]):  # Check last 5 messages
            content_lower = msg.content.lower()
            if (f"@{provider}" in content_lower or provider in content_lower) and "?" in content_lower:
                # Found a question for this provider, check if answered
                msg_index = context.index(msg)
                subsequent_messages = context[msg_index + 1:]
                
                # Check if provider responded after this question
                provider_responded = any(m.participant == provider for m in subsequent_messages)
                if not provider_responded:
                    return True
        return False

    def _has_high_conversation_energy(self, context: List[Message]) -> bool:
        """Detect if conversation has high energy (rapid exchanges)."""
        if len(context) < 4:
            return False
            
        # Check if last 4 messages were from different participants
        participants = [msg.participant for msg in context[-4:]]
        unique_participants = len(set(participants))
        
        # High energy if multiple participants are actively engaged
        return unique_participants >= 2 and len(participants) >= 3

    def _build_natural_speaking_queue(
        self,
        provider_scores: Dict[str, float],
        explicit_mentions: List[str],
        available_providers: List[str],
        vetoed_providers: set[str],
        context: List[Message],
        intent: str
    ) -> List[str]:
        """Build speaking queue using natural conversation flow principles."""
        
        queue: List[str] = []

        # ------------------------------------------------------------------
        # 1. Explicit mentions always take priority (as in human conversation)
        # ------------------------------------------------------------------
        for provider in explicit_mentions:
            if provider in available_providers and provider not in vetoed_providers:
                queue.append(provider)

        # ------------------------------------------------------------------
        # 2. Natural self-selection based on conversation flow
        # ------------------------------------------------------------------
        if not queue:  # Only if no explicit mentions
            
            # Check for urgent response needs (questions, interruptions)
            urgent_threshold = 0.6
            urgent_providers = [
                provider for provider, score in provider_scores.items()
                if score >= urgent_threshold and provider not in vetoed_providers
            ]
            
            if urgent_providers:
                # Sort by score for urgent responses
                urgent_providers.sort(key=lambda p: provider_scores[p], reverse=True)
                queue.extend(urgent_providers[:1])  # Take only the most urgent
            
            else:
                # Normal conversation flow - allow multiple responses if scores are close
                qualified_providers = {
                    provider: score
                    for provider, score in provider_scores.items()
                    if score >= self.base_threshold and provider not in vetoed_providers
                }
                
                if qualified_providers:
                    # Sort by score
                    sorted_providers = sorted(
                        qualified_providers.keys(),
                        key=lambda p: qualified_providers[p],
                        reverse=True
                    )
                    
                    # Allow both providers if scores are close (natural conversation)
                    top_score = qualified_providers[sorted_providers[0]]
                    for provider in sorted_providers:
                        score = qualified_providers[provider]
                        # Include if within close_score_threshold of top score OR if both scores are decent
                        if (top_score - score <= self.close_score_threshold) or (score >= 0.4):
                            queue.append(provider)
                        elif len(queue) == 0:  # Ensure at least one provider
                            queue.append(provider)
                        else:
                            break
                    
                    # Limit to 2 providers max to avoid overwhelming the user
                    queue = queue[:2]

        # ------------------------------------------------------------------
        # 3. Fallback - ensure someone responds
        # ------------------------------------------------------------------
        if not queue:
            non_vetoed = [p for p in available_providers if p not in vetoed_providers]
            if non_vetoed:
                # Choose based on context if available
                if context and len(context) > 0:
                    last_speaker = context[-1].participant
                    other_providers = [p for p in non_vetoed if p != last_speaker]
                    queue.append(other_providers[0] if other_providers else non_vetoed[0])
                else:
                    queue.append(non_vetoed[0])

        # ------------------------------------------------------------------
        # 4. Apply conversation-specific ordering
        # ------------------------------------------------------------------
        if len(queue) > 1:
            queue = self._apply_natural_ordering(queue, context, intent)

        return queue

    def _apply_natural_ordering(
        self, providers: List[str], context: List[Message], intent: str
    ) -> List[str]:
        """Apply natural conversation ordering principles."""
        
        if len(providers) <= 1:
            return providers
        
        # For questions, let the most relevant provider go first
        if intent == "question":
            # Keep current ordering (already sorted by relevance)
            return providers
        
        # For discussions, encourage back-and-forth
        if intent == "discussion" and context:
            last_speaker = context[-1].participant if context else None
            if last_speaker in ["openai", "xai"]:
                # Put the other AI first to encourage dialogue
                other_ai = "xai" if last_speaker == "openai" else "openai"
                if other_ai in providers:
                    providers = [other_ai] + [p for p in providers if p != other_ai]
        
        # For requests, let the most capable provider respond first
        if intent == "request":
            # Reorder based on provider strengths for the request type
            return providers  # Keep relevance-based ordering
        
        return providers
