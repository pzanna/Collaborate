"""
Simplified Multi-AI Chat System
Replaces the complex ResponseCoordinator with a natural group conversation approach
"""

import random
from typing import Any, List, Optional


class SimplifiedCoordinator:
    """Simple coordinator focusing on natural group conversations"""

    def __init__(self):
        # Simple, tunable parameters
        self.base_participation_chance = 0.4  # Base chance to participate
        self.max_recent_turns = 2  # Max consecutive turns
        self.mention_boost = 0.8  # Boost when mentioned
        self.question_boost = 0.3  # Boost for questions
        self.engagement_boost = 0.2  # Boost for engaging topics
        self.participants: List[str] = []
        self.turn_history: List[str] = []

    def register_participant(self, participant_id: str):
        """Register a new participant."""
        if participant_id not in self.participants:
            self.participants.append(participant_id)

    def select_participant(
        self, prompt: str, available_participants: List[str]
    ) -> Optional[str]:
        """Select a single participant to respond."""
        if not available_participants:
            return None

        # Simple selection logic: rotate through available participants
        # More sophisticated logic can be added here (e.g., based on prompt content)
        if not self.turn_history:
            # Start with the first available participant
            selected = available_participants[0]
        else:
            last_participant = self.turn_history[-1]
            try:
                last_index = available_participants.index(last_participant)
                next_index = (last_index + 1) % len(available_participants)
                selected = available_participants[next_index]
            except ValueError:
                # Last participant is no longer available, start from the beginning
                selected = available_participants[0]

        self.turn_history.append(selected)
        return selected

    def get_participating_providers(
        self,
        user_message: str,
        available_providers: List[str],
        recent_messages: List[Any],
    ) -> List[str]:
        """Determine which providers should participate based on simple rules"""

        participants = []
        message_lower = user_message.lower()

        # Check for direct mentions first (highest priority)
        for provider in available_providers:
            if f"@{provider}" in message_lower:
                return [provider]  # Only the mentioned provider responds

        # If no direct mentions, use participation scoring
        for provider in available_providers:
            participation_score = self.base_participation_chance

            # Boost for questions (everyone can answer)
            if any(
                indicator in message_lower
                for indicator in ["?", "how", "what", "why", "when", "where"]
            ):
                participation_score += self.question_boost

            # Boost for engaging topics
            engaging_words = [
                "think",
                "opinion",
                "idea",
                "approach",
                "solution",
                "help",
                "thoughts",
            ]
            if any(word in message_lower for word in engaging_words):
                participation_score += self.engagement_boost

            # Reduce if spoke too recently
            if self._spoke_recently(provider, recent_messages):
                participation_score *= 0.5

            # Add small random factor
            participation_score += random.uniform(0, 0.1)

            # Decide participation
            if participation_score > 0.5:
                participants.append(provider)

        # Ensure at least one provider responds
        if not participants and available_providers:
            # Pick someone who hasn't spoken recently
            recent_speakers = {
                msg.participant
                for msg in recent_messages[-3:]
                if hasattr(msg, "participant")
            }
            non_recent = [p for p in available_providers if p not in recent_speakers]
            participants = [non_recent[0] if non_recent else available_providers[0]]

        return participants

    def _spoke_recently(self, provider: str, recent_messages: List[Any]) -> bool:
        """Check if provider has dominated recent conversation"""
        last_messages = recent_messages[-self.max_recent_turns:]
        return len(last_messages) >= self.max_recent_turns and all(
            hasattr(msg, "participant") and msg.participant == provider
            for msg in last_messages
        )
