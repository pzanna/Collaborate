"""
Cost Estimation and Control System for AI Operations

This module provides cost estimation, tracking, and control mechanisms
for managing token usage and operational costs across AI providers.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from ..config.config_manager import ConfigManager


class CostTier(Enum):
    """Cost tier classifications for task complexity"""

    LOW = "low"  # Simple queries, single agent
    MEDIUM = "medium"  # multi-agent, moderate complexity
    HIGH = "high"  # Complex research, parallel execution
    CRITICAL = "critical"  # Emergency stop threshold


@dataclass
class CostEstimate:
    """Cost estimation for a research task"""

    estimated_tokens: int
    estimated_cost_usd: float
    task_complexity: CostTier
    agent_count: int
    parallel_factor: int = 1
    confidence: float = 0.8
    reasoning: str = ""


@dataclass
class CostUsage:
    """Track actual cost usage for a session / task"""

    task_id: str
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    tokens_used: int = 0
    cost_usd: float = 0.0
    provider_breakdown: Dict[str, Dict[str, Union[int, float]]] = field(
        default_factory=dict
    )
    agent_breakdown: Dict[str, Dict[str, Union[int, float]]] = field(
        default_factory=dict
    )


class CostEstimator:
    """
    Estimates and tracks costs for AI operations.

    Provides cost estimation for research tasks, tracks actual usage,
    and implements cost control mechanisms.
    """

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.total_cost = 0.0
        self.cost_by_provider: Dict[str, float] = defaultdict(float)
        self.cost_by_model: Dict[str, float] = defaultdict(float)
        self.active_sessions: Dict[str, CostUsage] = {}
        self.daily_usage: Dict[str, float] = defaultdict(float)

        # Cost configurations (per 1K tokens in USD)
        self.token_costs = {
            "openai": {
                "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
                "gpt-4.1-mini": {
                    "input": 0.00015,
                    "output": 0.0006,
                },  # Assumed same as 4o-mini
                "gpt-4": {"input": 0.03, "output": 0.06},
                "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            },
            "xai": {
                "grok-3-mini-beta": {"input": 0.0002, "output": 0.0008},  # Estimated
                "grok-3": {"input": 0.002, "output": 0.004},  # Estimated
            },
        }

        # Cost control thresholds
        self.cost_thresholds = {
            "session_warning": 1.0,  # USD per session
            "session_limit": 5.0,  # USD per session
            "daily_warning": 10.0,  # USD per day
            "daily_limit": 50.0,  # USD per day
            "emergency_stop": 100.0,  # USD emergency stop
        }

        # Task complexity factors
        self.complexity_multipliers = {
            CostTier.LOW: 1.0,
            CostTier.MEDIUM: 2.5,
            CostTier.HIGH: 5.0,
            CostTier.CRITICAL: 10.0,
        }

    def estimate_cost(
        self,
        prompt: str,
        provider: str,
        model: str,
        max_tokens: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Estimate the cost of a single API call.

        Args:
            prompt: The input prompt.
            provider: The AI provider.
            model: The AI model.
            max_tokens: The maximum number of tokens to generate.
            metadata: Optional metadata for more accurate estimation.

        Returns:
            The estimated cost in USD.
        """
        try:
            input_tokens = len(
                prompt.split()
            )  # A simple approximation; a proper tokenizer is better
            output_tokens = max_tokens

            cost_info = self.token_costs.get(provider, {}).get(model)
            if not cost_info:
                self.logger.warning(
                    f"Cost info not found for provider {provider}, model {model}. Using default."
                )
                cost_info = {"input": 0.0001, "output": 0.0005}  # A generic default

            input_cost = (input_tokens / 1000) * cost_info["input"]
            output_cost = (output_tokens / 1000) * cost_info["output"]

            return input_cost + output_cost
        except Exception as e:
            self.logger.error(f"Error estimating cost: {e}")
            return 0.0

    def update_cost(
        self,
        prompt: str,
        response: str,
        provider: str,
        model: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Update the total cost with an actual API call's cost.

        Args:
            prompt: The input prompt.
            response: The generated response.
            provider: The AI provider.
            model: The AI model.
            metadata: Optional metadata.

        Returns:
            The cost of this specific call.
        """
        try:
            input_tokens = len(prompt.split())
            output_tokens = len(response.split())

            cost_info = self.token_costs.get(provider, {}).get(model)
            if not cost_info:
                self.logger.warning(
                    f"Cost info not found for provider {provider}, model {model}. Using default."
                )
                cost_info = {"input": 0.0001, "output": 0.0005}

            call_cost = ((input_tokens / 1000) * cost_info["input"]) + (
                (output_tokens / 1000) * cost_info["output"]
            )

            self.total_cost += call_cost
            self.cost_by_provider[provider] += call_cost
            self.cost_by_model[model] += call_cost

            return call_cost
        except Exception as e:
            self.logger.error(f"Error updating cost: {e}")
            return 0.0

    def get_total_cost(self) -> float:
        """Get the total accumulated cost."""
        return self.total_cost

    def get_cost_by_provider(self) -> Dict[str, float]:
        """Get the cost breakdown by provider."""
        return dict(self.cost_by_provider)

    def get_cost_by_model(self) -> Dict[str, float]:
        """Get the cost breakdown by model."""
        return dict(self.cost_by_model)

    def reset(self):
        """Reset all cost counters."""
        self.total_cost = 0.0
        self.cost_by_provider.clear()
        self.cost_by_model.clear()
        self.logger.info("Cost estimator has been reset.")

    def estimate_task_cost(
        self,
        query: str,
        agents: List[str],
        parallel_execution: bool = False,
        context_content: Optional[str] = None,
    ) -> CostEstimate:
        """
        Estimate cost for a research task.

        Args:
            query: Research query
            agents: List of agent types to be used
            parallel_execution: Whether agents run in parallel
            context_content: Existing conversation context as text

        Returns:
            CostEstimate: Detailed cost estimation
        """
        # Base token estimation
        query_tokens = self._estimate_tokens_for_text(query)
        context_tokens = 0

        if context_content:
            context_tokens = self._estimate_tokens_for_text(context_content)

        # Determine task complexity
        complexity = self._assess_task_complexity(query, agents, parallel_execution)

        # Calculate agent-specific costs
        agent_count = len(agents)
        parallel_factor = agent_count if parallel_execution else 1

        # Base estimation per agent
        base_tokens_per_agent = max(
            500, query_tokens * 2
        )  # Response typically 2x query
        system_prompt_tokens = 200  # Approximate system prompt size

        # Apply complexity multiplier
        complexity_multiplier = self.complexity_multipliers[complexity]

        # Total token estimation
        total_tokens = int(
            (query_tokens + context_tokens + system_prompt_tokens) * agent_count
            + base_tokens_per_agent * agent_count * complexity_multiplier
        )

        # Estimate cost (using primary provider pricing)
        primary_provider = self.config_manager.config.research_manager.provider
        primary_model = self.config_manager.config.research_manager.model

        cost_per_1k = self.token_costs.get(primary_provider, {}).get(primary_model, {})
        if not cost_per_1k:
            # Fallback to OpenAI gpt-4 pricing
            cost_per_1k = self.token_costs["openai"]["gpt-4"]

        # Assume 70% input, 30% output tokens
        input_tokens = int(total_tokens * 0.7)
        output_tokens = int(total_tokens * 0.3)

        estimated_cost = (input_tokens / 1000) * cost_per_1k["input"] + (
            output_tokens / 1000
        ) * cost_per_1k["output"]

        # Add reasoning
        reasoning = self._generate_cost_reasoning(
            query, agents, complexity, parallel_execution, total_tokens, estimated_cost
        )

        return CostEstimate(
            estimated_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            task_complexity=complexity,
            agent_count=agent_count,
            parallel_factor=parallel_factor,
            confidence=0.8 if complexity in [CostTier.LOW, CostTier.MEDIUM] else 0.6,
            reasoning=reasoning,
        )

    def start_cost_tracking(self, task_id: str, session_id: str) -> None:
        """Start tracking costs for a task."""
        self.active_sessions[task_id] = CostUsage(
            task_id=task_id, session_id=session_id, start_time=datetime.now()
        )
        self.logger.info(f"Started cost tracking for task {task_id}")

    def record_usage(
        self,
        task_id: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        agent_type: Optional[str] = None,
    ) -> None:
        """
        Record actual token usage and cost.

        Args:
            task_id: Task identifier
            provider: AI provider (openai, xai)
            model: Model name
            input_tokens: Input tokens used
            output_tokens: Output tokens used
            agent_type: Type of agent that made the call
        """
        if task_id not in self.active_sessions:
            self.logger.warning(f"Recording usage for untracked task {task_id}")
            return

        # Calculate cost
        cost_per_1k = self.token_costs.get(provider, {}).get(model, {})
        if not cost_per_1k:
            self.logger.warning(f"No cost data for {provider}/{model}, using fallback")
            cost_per_1k = self.token_costs["openai"]["gpt-4"]

        input_cost = (input_tokens / 1000) * cost_per_1k["input"]
        output_cost = (output_tokens / 1000) * cost_per_1k["output"]
        total_cost = input_cost + output_cost
        total_tokens = input_tokens + output_tokens

        # Update session tracking
        usage = self.active_sessions[task_id]
        usage.tokens_used += total_tokens
        usage.cost_usd += total_cost

        # Update provider breakdown
        if provider not in usage.provider_breakdown:
            usage.provider_breakdown[provider] = {"tokens": 0, "cost": 0.0}

        usage.provider_breakdown[provider]["tokens"] += total_tokens
        usage.provider_breakdown[provider]["cost"] += total_cost

        # Update agent breakdown
        if agent_type:
            if agent_type not in usage.agent_breakdown:
                usage.agent_breakdown[agent_type] = {"tokens": 0, "cost": 0.0}

            usage.agent_breakdown[agent_type]["tokens"] += total_tokens
            usage.agent_breakdown[agent_type]["cost"] += total_cost

        # Update daily usage
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.daily_usage:
            self.daily_usage[today] = 0.0
        self.daily_usage[today] += total_cost

        # Check thresholds
        self._check_cost_thresholds(usage)

        self.logger.info(
            f"Recorded usage for {task_id}: {total_tokens} tokens, ${total_cost:.4f}"
        )

    def end_cost_tracking(self, task_id: str) -> Optional[CostUsage]:
        """End cost tracking for a task and return final usage."""
        if task_id not in self.active_sessions:
            return None

        usage = self.active_sessions.pop(task_id)
        usage.end_time = datetime.now()

        self.logger.info(
            f"Completed cost tracking for {task_id}: "
            f"{usage.tokens_used} tokens, ${usage.cost_usd:.4f}"
        )

        return usage

    def should_proceed_with_task(
        self, estimate: CostEstimate, session_id: str
    ) -> tuple[bool, str]:
        """
        Check if task should proceed based on cost thresholds.

        Returns:
            (should_proceed, reason)
        """
        # Check session limits
        session_cost = self._get_session_cost(session_id)
        if (
            session_cost + estimate.estimated_cost_usd
            > self.cost_thresholds["session_limit"]
        ):
            return (
                False,
                (
                    f"Session cost limit exceeded: ${session_cost:.2f} + "
                    f"${estimate.estimated_cost_usd:.2f} > ${self.cost_thresholds['session_limit']}"
                ),
            )

        # Check daily limits
        today_cost = self._get_daily_cost()
        if (
            today_cost + estimate.estimated_cost_usd
            > self.cost_thresholds["daily_limit"]
        ):
            return (
                False,
                (
                    f"Daily cost limit exceeded: ${today_cost:.2f} + "
                    f"${estimate.estimated_cost_usd:.2f} > ${self.cost_thresholds['daily_limit']}"
                ),
            )

        # Check emergency stop
        if estimate.estimated_cost_usd > self.cost_thresholds["emergency_stop"]:
            return (
                False,
                f"Task cost exceeds emergency threshold: ${estimate.estimated_cost_usd:.2f}",
            )

        return True, "Cost within acceptable limits"

    def get_cost_recommendations(self, estimate: CostEstimate) -> Dict[str, Any]:
        """
        Get recommendations for cost optimization.

        Returns:
            Dict with optimization suggestions
        """
        recommendations = {
            "current_tier": estimate.task_complexity.value,
            "suggestions": [],
            "alternatives": {},
        }

        # Cost-based recommendations
        if estimate.estimated_cost_usd > 1.0:
            recommendations["suggestions"].append(
                "Consider breaking down into smaller sub-tasks"
            )

        if estimate.agent_count > 2:
            recommendations["suggestions"].append(
                "Evaluate if all agents are necessary-consider single-agent approach"
            )
            recommendations["alternatives"]["single_agent"] = {
                "estimated_cost": estimate.estimated_cost_usd * 0.4,
                "trade_offs": "Reduced parallel processing, simpler analysis",
            }

        if estimate.parallel_factor > 1:
            recommendations["suggestions"].append(
                "Sequential execution would reduce cost but increase time"
            )
            recommendations["alternatives"]["sequential"] = {
                "estimated_cost": estimate.estimated_cost_usd * 0.7,
                "trade_offs": "Longer execution time, reduced parallelism benefits",
            }

        if estimate.task_complexity == CostTier.HIGH:
            recommendations["suggestions"].append(
                "Use memory agent to avoid redundant information gathering"
            )

        return recommendations

    def get_usage_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get usage summary for session or all sessions."""
        if session_id:
            session_usage = [
                usage
                for usage in self.active_sessions.values()
                if usage.session_id == session_id
            ]
            total_cost = sum(usage.cost_usd for usage in session_usage)
            total_tokens = sum(usage.tokens_used for usage in session_usage)

            return {
                "session_id": session_id,
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "active_tasks": len(session_usage),
                "usage_breakdown": [
                    {
                        "task_id": usage.task_id,
                        "cost": usage.cost_usd,
                        "tokens": usage.tokens_used,
                        "duration": (datetime.now()-usage.start_time).total_seconds(),
                        "providers": usage.provider_breakdown,
                        "agents": usage.agent_breakdown,
                    }
                    for usage in session_usage
                ],
            }
        else:
            # All sessions summary
            all_sessions = list(self.active_sessions.values())
            return {
                "total_active_sessions": len(
                    set(usage.session_id for usage in all_sessions)
                ),
                "total_active_tasks": len(all_sessions),
                "total_cost": sum(usage.cost_usd for usage in all_sessions),
                "total_tokens": sum(usage.tokens_used for usage in all_sessions),
                "daily_usage": self.daily_usage.copy(),
                "thresholds": self.cost_thresholds.copy(),
            }

    def _estimate_tokens_for_text(self, text: str) -> int:
        """Estimate tokens for a text string."""
        # Rough approximation: ~4 characters per token
        return max(1, len(text) // 4)

    def _assess_task_complexity(
        self, query: str, agents: List[str], parallel_execution: bool
    ) -> CostTier:
        """Assess the complexity tier of a research task."""
        query_lower = query.lower()

        # High complexity indicators
        high_complexity_keywords = [
            "comprehensive",
            "detailed analysis",
            "compare multiple",
            "research study",
            "in-depth",
            "systematic review",
            "correlation",
            "statistical analysis",
        ]

        # Medium complexity indicators
        medium_complexity_keywords = [
            "analyze",
            "compare",
            "summarize",
            "explain",
            "relationship",
            "trend",
            "pattern",
        ]

        # Complexity factors
        complexity_score = 0

        # Query complexity
        if any(keyword in query_lower for keyword in high_complexity_keywords):
            complexity_score += 3
        elif any(keyword in query_lower for keyword in medium_complexity_keywords):
            complexity_score += 2
        else:
            complexity_score += 1

        # Agent count factor
        if len(agents) >= 4:
            complexity_score += 2
        elif len(agents) >= 2:
            complexity_score += 1

        # Parallel execution factor
        if parallel_execution:
            complexity_score += 1

        # Query length factor
        if len(query) > 200:
            complexity_score += 1

        # Determine tier
        if complexity_score >= 6:
            return CostTier.HIGH
        elif complexity_score >= 4:
            return CostTier.MEDIUM
        else:
            return CostTier.LOW

    def _get_session_cost(self, session_id: str) -> float:
        """Get current total cost for a session."""
        return sum(
            usage.cost_usd
            for usage in self.active_sessions.values()
            if usage.session_id == session_id
        )

    def _get_daily_cost(self) -> float:
        """Get total cost for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.daily_usage.get(today, 0.0)

    def _check_cost_thresholds(self, usage: CostUsage):
        """Check cost thresholds and log warnings."""
        session_cost = self._get_session_cost(usage.session_id)
        daily_cost = self._get_daily_cost()

        # Session warning
        if session_cost > self.cost_thresholds["session_warning"]:
            self.logger.warning(
                f"Session {usage.session_id} cost has exceeded warning threshold: ${session_cost:.2f}"
            )

        # Daily warning
        if daily_cost > self.cost_thresholds["daily_warning"]:
            self.logger.warning(
                f"Daily cost has exceeded warning threshold: ${daily_cost:.2f}"
            )

        # Emergency stop
        if daily_cost > self.cost_thresholds["emergency_stop"]:
            self.logger.critical(
                f"EMERGENCY STOP: Daily cost limit exceeded: ${daily_cost:.2f}"
            )
            # In a real system, this would trigger a system halt or notification
            # For now, we just log a critical error
            # raise Exception("Emergency cost limit reached")

    def _generate_cost_reasoning(
        self,
        query: str,
        agents: List[str],
        complexity: CostTier,
        parallel: bool,
        tokens: int,
        cost: float,
    ) -> str:
        """Generate a human-readable reasoning for the cost estimate."""
        reason = f"Cost estimate for query: '{query[:50]}...'\n"
        reason += f"- Task complexity assessed as: {complexity.value.upper()}\n"
        reason += f"- Number of agents involved: {len(agents)}\n"
        reason += f"- Parallel execution: {'Yes' if parallel else 'No'}\n"
        reason += f"- Estimated tokens: {tokens}\n"
        reason += f"- Estimated cost: ${cost:.4f}\n"
        return reason
