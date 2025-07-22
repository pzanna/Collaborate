"""
Persona Registry

This module manages the registration and lifecycle of persona agents,
providing a central interface for accessing specialized expertise.
"""

import logging
from typing import Dict, List, Optional, Type, Any
from enum import Enum

from ..config.config_manager import ConfigManager
from ..mcp.protocols import ResearchAction, AgentResponse
from .neurobiologist_agent import NeurologistPersonaAgent


class PersonaType(Enum):
    """Available persona types."""
    NEUROBIOLOGIST = "neurobiologist"
    COMPUTATIONAL_NEUROSCIENTIST = "computational_neuroscientist"
    BIOMEDICAL_SYSTEMS_ENGINEER = "biomedical_systems_engineer"
    AI_ML_ENGINEER = "ai_ml_engineer"
    ANIMAL_BIOLOGIST = "animal_biologist"
    TECHNICAL_WRITER = "technical_writer"
    RESEARCH_MANAGER = "research_manager"


class PersonaRegistry:
    """
    Registry for managing persona agents.
    
    This class handles the registration, initialization, and coordination
    of specialized persona agents for expert consultation.
    """
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize the persona registry."""
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Registry of persona agent classes
        self._persona_classes: Dict[PersonaType, Type] = {
            PersonaType.NEUROBIOLOGIST: NeurologistPersonaAgent,
            # Add other persona classes as they are implemented
        }
        
        # Active persona agent instances
        self._active_personas: Dict[PersonaType, Any] = {}
        
        # Persona capabilities mapping
        self._persona_capabilities: Dict[PersonaType, List[str]] = {
            PersonaType.NEUROBIOLOGIST: [
                "neuron_preparation", "electrophysiology", "cell_culture",
                "neural_interfacing", "bio_digital_systems", "neural_analysis",
                "experimental_protocols", "biosafety_ethics"
            ]
        }
    
    async def initialize_persona(self, persona_type: PersonaType) -> bool:
        """
        Initialize a specific persona agent.
        
        Args:
            persona_type: The type of persona to initialize
            
        Returns:
            bool: True if initialization successful
        """
        try:
            if persona_type in self._active_personas:
                self.logger.info(f"Persona {persona_type.value} already initialized")
                return True
            
            if persona_type not in self._persona_classes:
                self.logger.error(f"Persona class not found for {persona_type.value}")
                return False
            
            # Create and initialize the persona agent
            persona_class = self._persona_classes[persona_type]
            persona_agent = persona_class(self.config_manager)
            
            # Initialize the agent
            success = await persona_agent.initialize()
            if success:
                self._active_personas[persona_type] = persona_agent
                self.logger.info(f"Successfully initialized {persona_type.value} persona")
                return True
            else:
                self.logger.error(f"Failed to initialize {persona_type.value} persona")
                return False
                
        except Exception as e:
            self.logger.error(f"Error initializing {persona_type.value} persona: {e}")
            return False
    
    async def initialize_all_personas(self) -> Dict[PersonaType, bool]:
        """
        Initialize all available persona agents.
        
        Returns:
            Dict mapping persona types to initialization success status
        """
        results = {}
        for persona_type in self._persona_classes.keys():
            results[persona_type] = await self.initialize_persona(persona_type)
        
        successful_count = sum(1 for success in results.values() if success)
        self.logger.info(f"Initialized {successful_count}/{len(results)} persona agents")
        
        return results
    
    async def consult_persona(self, persona_type: PersonaType, 
                             action: ResearchAction) -> Optional[AgentResponse]:
        """
        Consult a specific persona agent.
        
        Args:
            persona_type: The type of persona to consult
            action: The research action/consultation request
            
        Returns:
            AgentResponse or None if persona not available
        """
        try:
            if persona_type not in self._active_personas:
                # Try to initialize the persona if not already active
                if not await self.initialize_persona(persona_type):
                    self.logger.error(f"Cannot consult {persona_type.value}: not initialized")
                    return None
            
            persona_agent = self._active_personas[persona_type]
            response = await persona_agent.process_action(action)
            
            self.logger.info(f"Consultation with {persona_type.value} completed: {response.status}")
            return response
            
        except Exception as e:
            self.logger.error(f"Error consulting {persona_type.value}: {e}")
            return None
    
    async def find_best_persona(self, expertise_area: str) -> Optional[PersonaType]:
        """
        Find the best persona for a specific expertise area.
        
        Args:
            expertise_area: The area of expertise needed
            
        Returns:
            PersonaType or None if no suitable persona found
        """
        for persona_type, capabilities in self._persona_capabilities.items():
            if expertise_area.lower() in [cap.lower() for cap in capabilities]:
                return persona_type
        
        # If no exact match, return a general-purpose persona
        # For now, default to neurobiologist for biological queries
        if any(term in expertise_area.lower() for term in ['bio', 'neuro', 'cell', 'neural']):
            return PersonaType.NEUROBIOLOGIST
        
        return None
    
    async def get_persona_status(self, persona_type: PersonaType) -> Optional[Dict[str, Any]]:
        """
        Get the status of a specific persona agent.
        
        Args:
            persona_type: The persona type to check
            
        Returns:
            Status dictionary or None if persona not active
        """
        if persona_type not in self._active_personas:
            return None
        
        persona_agent = self._active_personas[persona_type]
        return await persona_agent.health_check()
    
    async def get_all_persona_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get the status of all active persona agents.
        
        Returns:
            Dictionary mapping persona names to their status
        """
        status_dict = {}
        for persona_type, persona_agent in self._active_personas.items():
            try:
                status = await persona_agent.health_check()
                status_dict[persona_type.value] = status
            except Exception as e:
                status_dict[persona_type.value] = {
                    'error': str(e),
                    'status': 'error'
                }
        
        return status_dict
    
    def get_available_personas(self) -> List[str]:
        """Get list of available persona types."""
        return [persona_type.value for persona_type in self._persona_classes.keys()]
    
    def get_persona_capabilities(self, persona_type: PersonaType) -> List[str]:
        """Get the capabilities of a specific persona type."""
        return self._persona_capabilities.get(persona_type, [])
    
    async def shutdown_persona(self, persona_type: PersonaType) -> bool:
        """
        Shutdown a specific persona agent.
        
        Args:
            persona_type: The persona type to shutdown
            
        Returns:
            bool: True if shutdown successful
        """
        try:
            if persona_type in self._active_personas:
                persona_agent = self._active_personas[persona_type]
                await persona_agent.stop()
                del self._active_personas[persona_type]
                self.logger.info(f"Shutdown {persona_type.value} persona")
                return True
            else:
                self.logger.warning(f"Persona {persona_type.value} not active")
                return False
        except Exception as e:
            self.logger.error(f"Error shutting down {persona_type.value}: {e}")
            return False
    
    async def shutdown_all_personas(self) -> Dict[PersonaType, bool]:
        """
        Shutdown all active persona agents.
        
        Returns:
            Dict mapping persona types to shutdown success status
        """
        results = {}
        for persona_type in list(self._active_personas.keys()):
            results[persona_type] = await self.shutdown_persona(persona_type)
        
        return results
