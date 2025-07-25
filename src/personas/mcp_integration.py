"""
MCP Persona Integration

This module integrates persona agents with the MCP server,
allowing other agents and systems to request expert consultations.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from ..config.config_manager import ConfigManager
from ..mcp.protocols import AgentResponse, ResearchAction
from .persona_registry import PersonaRegistry, PersonaType


class PersonaMCPIntegration:
    """
    Integration layer between persona agents and the MCP server.

    This class provides a standardized interface for requesting
    expert consultations from persona agents via the MCP protocol.
    """

    def __init__(self, config_manager: ConfigManager):
        """Initialize the persona MCP integration."""
        self.config_manager = config_manager

        # Ensure logging is properly configured for AI API calls
        config_manager.setup_logging()

        self.logger = logging.getLogger(__name__)
        self.persona_registry = PersonaRegistry(config_manager)
        self.consultation_history: Dict[str, Dict[str, Any]] = {}

    async def initialize(self) -> bool:
        """
        Initialize the persona MCP integration.

        Returns:
            bool: True if initialization successful
        """
        try:
            # Initialize core personas
            core_personas = [PersonaType.NEUROBIOLOGIST]

            results = {}
            for persona_type in core_personas:
                results[persona_type] = await self.persona_registry.initialize_persona(
                    persona_type
                )

            successful = sum(1 for success in results.values() if success)
            total = len(results)

            self.logger.info(
                f"Persona MCP integration initialized: {successful}/{total} personas ready"
            )
            return successful > 0

        except Exception as e:
            self.logger.error(f"Failed to initialize persona MCP integration: {e}")
            return False

    async def request_expert_consultation(
        self,
        expertise_area: str,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        preferred_persona: Optional[str] = None,
    ) -> AgentResponse:
        """
        Request an expert consultation from a persona agent.

        Args:
            expertise_area: The area of expertise needed
            query: The consultation query
            context: Additional context information
            preferred_persona: Preferred persona type (optional)

        Returns:
            AgentResponse: The expert consultation response
        """
        try:
            # Determine which persona to consult
            if preferred_persona:
                try:
                    persona_type = PersonaType(preferred_persona)
                except ValueError:
                    self.logger.warning(f"Unknown persona type: {preferred_persona}")
                    persona_type = await self.persona_registry.find_best_persona(
                        expertise_area
                    )
            else:
                persona_type = await self.persona_registry.find_best_persona(
                    expertise_area
                )

            if not persona_type:
                return self._create_no_persona_response(expertise_area, query)

            # Create research action for the consultation
            action = ResearchAction(
                task_id=f"consultation_{uuid.uuid4().hex[:8]}",
                context_id=f"persona_consultation_{uuid.uuid4().hex[:8]}",
                agent_type=persona_type.value,
                action="expert_consultation",
                payload={
                    "query": query,
                    "context": context or {},
                    "expertise_area": expertise_area,
                },
                priority="normal",
                created_at=datetime.now(),
            )

            # Record consultation request
            self.consultation_history[action.task_id] = {
                "persona_type": persona_type.value,
                "expertise_area": expertise_area,
                "query": query,
                "requested_at": datetime.now(),
                "status": "requested",
            }

            # Consult the persona
            self.logger.info(
                f"Requesting consultation from {persona_type.value} for {expertise_area}"
            )
            response = await self.persona_registry.consult_persona(persona_type, action)

            if response:
                # Update consultation history
                self.consultation_history[action.task_id].update(
                    {
                        "status": "completed",
                        "completed_at": datetime.now(),
                        "response_status": response.status,
                    }
                )

                return response
            else:
                # Handle consultation failure
                error_response = self._create_consultation_error_response(
                    action, persona_type
                )
                self.consultation_history[action.task_id].update(
                    {
                        "status": "failed",
                        "completed_at": datetime.now(),
                        "error": "Persona consultation failed",
                    }
                )
                return error_response

        except Exception as e:
            self.logger.error(f"Error in expert consultation request: {e}")
            return self._create_generic_error_response(str(e))

    async def get_persona_capabilities(self) -> Dict[str, Any]:
        """
        Get information about available personas and their capabilities.

        Returns:
            Dictionary containing persona information
        """
        try:
            available_personas = {}

            for persona_type in PersonaType:
                capabilities = self.persona_registry.get_persona_capabilities(
                    persona_type
                )
                status = await self.persona_registry.get_persona_status(persona_type)

                available_personas[persona_type.value] = {
                    "capabilities": capabilities,
                    "status": status.get("status") if status else "not_initialized",
                    "active": persona_type.value
                    in [p.value for p in self.persona_registry._active_personas.keys()],
                }

            return {
                "available_personas": available_personas,
                "total_personas": len(PersonaType),
                "active_personas": len(self.persona_registry._active_personas),
            }

        except Exception as e:
            self.logger.error(f"Error getting persona capabilities: {e}")
            return {"error": str(e)}

    async def get_consultation_history(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get recent consultation history.

        Args:
            limit: Maximum number of consultations to return

        Returns:
            Dictionary containing consultation history
        """
        try:
            # Sort consultations by request time (most recent first)
            sorted_consultations = sorted(
                self.consultation_history.items(),
                key=lambda x: x[1]["requested_at"],
                reverse=True,
            )

            # Limit results
            recent_consultations = dict(sorted_consultations[:limit])

            # Calculate statistics
            total_consultations = len(self.consultation_history)
            completed_consultations = sum(
                1
                for c in self.consultation_history.values()
                if c["status"] == "completed"
            )

            return {
                "recent_consultations": recent_consultations,
                "statistics": {
                    "total_consultations": total_consultations,
                    "completed_consultations": completed_consultations,
                    "success_rate": (
                        completed_consultations / total_consultations
                        if total_consultations > 0
                        else 0
                    ),
                },
            }

        except Exception as e:
            self.logger.error(f"Error getting consultation history: {e}")
            return {"error": str(e)}

    def _create_no_persona_response(
        self, expertise_area: str, query: str
    ) -> AgentResponse:
        """Create a response when no suitable persona is found."""
        return AgentResponse(
            task_id=f"no_persona_{uuid.uuid4().hex[:8]}",
            context_id="persona_consultation_error",
            agent_type="persona_integration",
            status="error",
            error=f"No suitable persona found for expertise area: {expertise_area}",
            completed_at=datetime.now(),
        )

    def _create_consultation_error_response(
        self, action: ResearchAction, persona_type: PersonaType
    ) -> AgentResponse:
        """Create a response when consultation fails."""
        return AgentResponse(
            task_id=action.task_id,
            context_id=action.context_id,
            agent_type=persona_type.value,
            status="error",
            error=f"Consultation with {persona_type.value} failed",
            completed_at=datetime.now(),
        )

    def _create_generic_error_response(self, error_message: str) -> AgentResponse:
        """Create a generic error response."""
        return AgentResponse(
            task_id=f"error_{uuid.uuid4().hex[:8]}",
            context_id="persona_consultation_error",
            agent_type="persona_integration",
            status="error",
            error=error_message,
            completed_at=datetime.now(),
        )

    async def shutdown(self) -> bool:
        """
        Shutdown the persona MCP integration.

        Returns:
            bool: True if shutdown successful
        """
        try:
            await self.persona_registry.shutdown_all_personas()
            self.logger.info("Persona MCP integration shutdown complete")
            return True
        except Exception as e:
            self.logger.error(f"Error during persona MCP integration shutdown: {e}")
            return False
