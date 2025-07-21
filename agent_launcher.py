#!/usr/bin/env python3
"""
Agent Launcher for Eunice
Launches and manages multiple research agents
"""

import asyncio
import os
import sys
import signal
import logging
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    # Set up logging
    log_path = os.getenv("EUNICE_LOG_PATH", "logs")
    log_level = os.getenv("EUNICE_LOG_LEVEL", "INFO")
    
    # Ensure log directory exists
    Path(log_path).mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(log_path, 'agents.log')),
        ]
    )

logger = logging.getLogger(__name__)


class AgentLauncher:
    """Manages the lifecycle of all research agents."""
    
    def __init__(self):
        self.agents = []
        self.running = False
        
    async def start_all_agents(self):
        """Start all research agents."""
        try:
            # Ensure logs directory exists
            os.makedirs("logs", exist_ok=True)
            
            # Import config manager
            from src.config.config_manager import ConfigManager
            config_manager = ConfigManager()
            
            # Import all agent classes
            from src.agents.retriever_agent import RetrieverAgent
            from src.agents.planning_agent import PlanningAgent
            from src.agents.executor_agent import ExecutorAgent
            from src.agents.memory_agent import MemoryAgent
            
            # Create and initialize agents
            agent_classes = [
                ("Retriever", RetrieverAgent),
                ("Planning", PlanningAgent),
                ("Executor", ExecutorAgent),
                ("Memory", MemoryAgent)
            ]
            
            for name, agent_class in agent_classes:
                try:
                    logger.info(f"Starting {name} Agent...")
                    agent = agent_class(config_manager)
                    
                    # Initialize the agent
                    success = await agent.initialize()
                    if success:
                        # Start the agent
                        asyncio.create_task(agent.run())
                        self.agents.append(agent)
                        logger.info(f"✓ {name} Agent started successfully")
                    else:
                        logger.error(f"✗ Failed to initialize {name} Agent")
                        
                except Exception as e:
                    logger.error(f"✗ Failed to start {name} Agent: {e}")
                    continue
            
            if self.agents:
                logger.info(f"✅ Started {len(self.agents)} research agents")
                self.running = True
                return True
            else:
                logger.error("❌ No agents could be started")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start agents: {e}")
            return False
    
    async def stop_all_agents(self):
        """Stop all research agents."""
        logger.info("Stopping all research agents...")
        self.running = False
        
        # Stop all agents
        for agent in self.agents:
            try:
                await agent.stop()
                logger.info(f"✓ Stopped {agent.agent_type} agent")
            except Exception as e:
                logger.error(f"Error stopping {agent.agent_type} agent: {e}")
        
        self.agents.clear()
        logger.info("All agents stopped")
    
    async def run_forever(self):
        """Run agents until interrupted."""
        if not await self.start_all_agents():
            return
        
        try:
            # Keep running until interrupted
            while self.running:
                await asyncio.sleep(1)
                
                # Check if any agents have stopped unexpectedly
                for agent in self.agents[:]:  # Copy list to avoid modification during iteration
                    if not agent.is_running:
                        logger.warning(f"Agent {agent.agent_type} stopped unexpectedly")
                        self.agents.remove(agent)
                
                # If all agents stopped, exit
                if not self.agents:
                    logger.error("All agents have stopped")
                    break
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.stop_all_agents()


def setup_signal_handlers(launcher):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        launcher.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point."""
    launcher = AgentLauncher()
    setup_signal_handlers(launcher)
    
    logger.info("🤖 Starting Research Agents...")
    await launcher.run_forever()
    logger.info("🛑 Agent launcher stopped")


if __name__ == "__main__":
    asyncio.run(main())
