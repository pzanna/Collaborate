#!/usr/bin/env python3
"""
Agent Launcher - Starts all research agents

This script starts all the research agents (Retriever, Reasoner, Executor, Memory)
that connect to the MCP server to handle research tasks.
"""

import asyncio
import logging
import signal
import sys
import os
from pathlib import Path
from typing import List

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/agents.log'),
        logging.StreamHandler()
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
            from src.agents.reasoner_agent import ReasonerAgent
            from src.agents.executor_agent import ExecutorAgent
            from src.agents.memory_agent import MemoryAgent
            
            # Create and initialize agents
            agent_classes = [
                ("Retriever", RetrieverAgent),
                ("Reasoner", ReasonerAgent),
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
