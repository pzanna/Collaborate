"""
Neurobiologist Persona Agent

This module implements a specialized AI agent that embodies the expertise
of a neurobiologist for expert consultation via the MCP server.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ..agents.base_agent import BaseAgent
from ..ai_clients.openai_client import AIProviderConfig, OpenAIClient
from ..config.config_manager import ConfigManager
from ..mcp.protocols import AgentResponse, ResearchAction


class NeurologistPersonaAgent(BaseAgent):
    """
    Specialized AI agent embodying neurobiologist expertise.

    This agent provides expert consultation on:
    - In vitro cerebral neuron preparation and maintenance
    - Electrophysiology and neural interfacing
    - Bio - digital hybrid systems
    - Neural activity analysis and interpretation
    """

    def __init__(self, config_manager: ConfigManager):
        """Initialize the Neurobiologist persona agent."""
        super().__init__("neurobiologist_persona", config_manager)
        self.ai_client: Optional[OpenAIClient] = None
        self.system_prompt = self._load_system_prompt()
        self.expertise_areas = [
            "neuron_preparation",
            "electrophysiology",
            "cell_culture",
            "neural_interfacing",
            "bio_digital_systems",
            "neural_analysis",
            "experimental_protocols",
            "biosafety_ethics",
        ]

    def _get_capabilities(self) -> List[str]:
        """Define the capabilities of this persona agent."""
        return [
            "expert_consultation",
            "protocol_design",
            "data_interpretation",
            "experimental_guidance",
            "safety_assessment",
            "literature_synthesis",
        ]

    def _get_agent_config(self) -> Dict[str, Any]:
        """Get agent - specific configuration."""
        return {
            "max_concurrent": 5,  # Can handle multiple consultations
            "timeout": 120,  # Complex analyses may take longer
            "model": "gpt - 4.1 - mini",
            "temperature": 0.1,  # More deterministic for scientific accuracy
        }

    def _load_system_prompt(self) -> str:
        """Load the comprehensive system prompt for the neurobiologist persona."""
        return """You are an expert neurobiologist specialising in in vitro cerebral neuron preparation, maintenance,
        and interfacing with computer systems. Your remit includes:

- Extraction / derivation (primary tissue, iPSC - derived neurons, organoids)
- Culture formulation, environmental control, viability / phenotyping assays
- Electrophysiology (MEA / patch clamp), opto / chemogenetics, hybrid chemical–electrical interfaces
- Mapping biological activity onto computational frameworks (ANNs, reservoir computing, neuromorphic models)
 and interpreting bidirectional signalling

## Core Objectives

- Provide scientifically rigorous, reference - backed explanations of neuroanatomy, cell biology,
electrophysiology, and plasticity
- Propose step - by - step experimental protocols (materials, concentrations, timings, QC checkpoints,
 troubleshooting)
- Interpret supplied data (spike trains,
    calcium imaging traces,
    metabolic readouts) for patterns such as efficiency,
    adaptability,
    learning - like behaviour
- Bridge biology ↔ computation: suggest encoding of stimuli,
    decoding of responses,
    and comparison metrics (e.g.,
    energy per inference,
    latency,
    noise tolerance) with ANNs
- Prioritise biosafety, ethics, sterility, and reproducibility; flag hazards, ambiguous steps, or missing controls

## Behavioural Guidelines

- **Accuracy & Citations**: Ground claims in established literature. Cite primary or high - quality secondary sources.
If uncertain, state so and suggest verification.
- **Evidence - Based Hypothesising**: Separate speculation from consensus; justify novel mechanisms with analogous
findings.
- **Detail & Clarity**: Use British English, SI units, and clear formatting (tables for recipes, bullet lists for
steps).
 Include critical parameters (temperature, CO₂ %, osmolarity, pH, plating density).
- **Computational Integration**: Recommend data structures and preprocessing for interfacing;
 suggest modelling paradigms aligned with observed biology; propose biological experiments for ANN analogues.
- **Safety & Ethics**: Remind users about biosafety levels, ethical approvals, species - specific regulations,
 waste disposal, and use of human - derived materials.
- **Reproducibility & Controls**: Always propose controls, replication numbers, statistical tests,
 and documentation practices.
- **Constraint Sensitivity**: Adapt recommendations to limited budgets / equipment or restricted reagent availability;
 propose safe alternatives.
- **Calibration & Validation**: Encourage calibration routines, media quality checks, and validation assays.

## Communication Style

- Concise but complete; avoid fluff
- Use section headers, numbered steps, and tables
- Offer decision trees when multiple routes exist
- Highlight "Critical" vs "Optional" steps

## Response Structure (Default Template)

1. **Context Recap** – Restate the problem / task (1–3 sentences)
2. **Biological Background / Rationale** – Key principles, mechanisms
3. **Protocol or Analysis Plan** – Granular steps (materials, quantities, timelines)
4. **Integration with Computation / ANNs** – Encoding / decoding, metrics, modelling suggestions
5. **Risk, Safety, and QC** – Hazards, sterility, controls, validation
6. **Next Actions / Decision Points** – What to do, measure, or choose next
7. **References** – Numbered list of cited works (author / year or DOI / PMID)

## When Data Are Provided

- Perform quantitative / qualitative analysis (e.g.,
    spike sorting,
    burst detection,
    ISI histograms,
    correlation with stimuli)
- Suggest additional analyses or visualisations to increase interpretability
- Compare to known benchmarks (synaptic fatigue, metabolic cost curves)

## If Information Is Missing or Ambiguous

- Explicitly list unknowns
- Offer minimal viable assumptions and safer alternatives
- Propose quick diagnostic experiments to close knowledge gaps

## Do / Don't Guidelines

**Do:**
- Suggest realistic timelines, note lot - to - lot variability, specify incubation times, give fallback reagents
- Mark speculative sections clearly ("Hypothesis:" / "Speculative mechanism:")

**Don't:**
- Hand - wave critical steps, recommend unsafe shortcuts, or conflate in vivo and in vitro contexts
 without noting differences
- Oversell results—acknowledge biological variability and noise

## Error Handling & Limits

- Redirect or state limitations if asked outside scope (e.g., clinical advice)
- For conflicting literature, summarise the split and provide balanced recommendations

## Style Tokens / Shortcuts

- Use callouts like **Critical**, **Note**, **Troubleshoot**, **Alternative**, **Control** for readability
- Tables for media recipes, electrode layouts, stimulation paradigms
- Flowcharts for decision logic (e.g., contamination response, media optimisation)"""

    async def _initialize_agent(self) -> None:
        """Initialize AI client and persona - specific setup."""
        try:
            # Ensure logging is properly configured for AI API calls
            self.config.setup_logging()

            # Get OpenAI API key from configuration
            api_key = self.config.get_api_key("openai")

            if not api_key:
                raise ValueError("OpenAI API key not found in configuration")

            # Create AI provider config
            ai_config = AIProviderConfig(
                provider="openai",
                model=self.agent_config.get("model", "gpt - 4-turbo"),
                temperature=self.agent_config.get("temperature", 0.1),
                max_tokens=2000,
                system_prompt=self.system_prompt,
            )

            # Initialize AI client
            self.ai_client = OpenAIClient(api_key=api_key, config=ai_config)

            # Validate system prompt
            if not self.system_prompt:
                raise ValueError("System prompt not loaded")

            self.logger.info(
                f"Neurobiologist persona agent initialized with {len(self.expertise_areas)} expertise areas"
            )

        except Exception as e:
            self.logger.error(f"Failed to initialize neurobiologist persona: {e}")
            raise

    async def process_action(self, action: ResearchAction) -> AgentResponse:
        """
        Process a research action with neurobiologist expertise.

        Args:
            action: The research action to process

        Returns:
            AgentResponse: Expert response from neurobiologist perspective
        """
        try:
            self.logger.info(f"Processing neurobiologist consultation: {action.action}")

            # Validate action type
            if action.action not in [
                "expert_consultation",
                "protocol_design",
                "data_interpretation",
                "experimental_guidance",
            ]:
                return self._create_error_response(
                    action, f"Unsupported action type: {action.action}"
                )

            # Extract consultation parameters
            query = action.payload.get("query", "")
            context = action.payload.get("context", {})
            expertise_area = action.payload.get("expertise_area", "general")

            if not query:
                return self._create_error_response(
                    action, "Query parameter is required"
                )

            # Generate expert response
            response = await self._generate_expert_response(
                query, context, expertise_area
            )

            return AgentResponse(
                task_id=action.task_id,
                context_id=action.context_id,
                agent_type=self.agent_type,
                status="completed",
                result={
                    "expert_response": response,
                    "expertise_area": expertise_area,
                    "confidence": self._assess_confidence(expertise_area),
                    "recommendations": self._extract_recommendations(response),
                    "safety_notes": self._extract_safety_notes(response),
                },
                completed_at=datetime.now(),
            )

        except Exception as e:
            self.logger.error(f"Error processing neurobiologist consultation: {e}")
            return self._create_error_response(action, str(e))

    async def _generate_expert_response(
        self, query: str, context: Dict[str, Any], expertise_area: str
    ) -> str:
        """
        Generate expert response using AI client with neurobiologist persona.

        Args:
            query: The consultation query
            context: Additional context information
            expertise_area: Specific area of expertise

        Returns:
            str: Expert response
        """
        try:
            if not self.ai_client:
                raise RuntimeError("AI client not initialized")

            # Prepare enhanced prompt with context
            enhanced_prompt = self._prepare_enhanced_prompt(
                query, context, expertise_area
            )

            # Generate response using AI client
            response = self.ai_client.get_response(
                user_message=enhanced_prompt, system_prompt=self.system_prompt
            )

            return response

        except Exception as e:
            self.logger.error(f"Error generating expert response: {e}")
            raise

    def _prepare_enhanced_prompt(
        self, query: str, context: Dict[str, Any], expertise_area: str
    ) -> str:
        """Prepare an enhanced prompt with context and expertise focus."""
        prompt_parts = [
            f"## Expert Consultation Request\n\n**Expertise Area**: {expertise_area}\n"
        ]

        if context:
            prompt_parts.append("**Context Information**:")
            for key, value in context.items():
                prompt_parts.append(f"- **{key}**: {value}")
            prompt_parts.append("")

        prompt_parts.append(f"**Query**: {query}\n")
        prompt_parts.append(
            "Please provide a comprehensive expert response following your structured template."
        )

        return "\n".join(prompt_parts)

    def _assess_confidence(self, expertise_area: str) -> float:
        """Assess confidence level for the given expertise area."""
        # High confidence for core neurobiologist areas
        high_confidence_areas = [
            "neuron_preparation",
            "electrophysiology",
            "cell_culture",
        ]
        medium_confidence_areas = ["neural_interfacing", "bio_digital_systems"]

        if expertise_area in high_confidence_areas:
            return 0.95
        elif expertise_area in medium_confidence_areas:
            return 0.85
        else:
            return 0.75

    def _extract_recommendations(self, response: str) -> List[str]:
        """Extract key recommendations from the expert response."""
        # Simple extraction - in practice, this could be more sophisticated
        recommendations = []
        lines = response.split("\n")

        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["recommend", "suggest", "advise"]
            ):
                recommendations.append(line.strip())

        return recommendations[:5]  # Limit to top 5

    def _extract_safety_notes(self, response: str) -> List[str]:
        """Extract safety - related notes from the expert response."""
        safety_notes = []
        lines = response.split("\n")

        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["safety", "hazard", "caution", "warning", "biosafety"]
            ):
                safety_notes.append(line.strip())

        return safety_notes

    def _create_error_response(
        self, action: ResearchAction, error_message: str
    ) -> AgentResponse:
        """Create an error response for failed processing."""
        return AgentResponse(
            task_id=action.task_id,
            context_id=action.context_id,
            agent_type=self.agent_type,
            status="error",
            error=error_message,
            completed_at=datetime.now(),
        )

    async def _process_task_impl(self, task: ResearchAction) -> Dict[str, Any]:
        """
        Process a task (implemented by subclasses).

        Args:
            task: Research task to process

        Returns:
            Dict[str, Any]: Task result
        """
        # For persona agents, we delegate to process_action
        response = await self.process_action(task)
        return response.result or {}

    async def _cleanup_agent(self) -> None:
        """Clean up agent - specific resources (implemented by subclasses)."""
        try:
            # Clean up AI client if needed
            self.ai_client = None
            self.logger.info("Neurobiologist persona agent cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during neurobiologist persona cleanup: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for the persona agent."""
        health_status = {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "ai_client_available": self.ai_client is not None,
            "expertise_areas": self.expertise_areas,
            "capabilities": self.capabilities,
            "active_consultations": len(self.active_tasks),
        }

        return health_status
