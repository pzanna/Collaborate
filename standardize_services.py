#!/usr/bin/env python3
"""
Standardization script for Eunice Research Platform services and agents.

This script applies the standard service structure template to existing
services and agents, migrating them to the new consistent layout.

Usage:
    python standardize_services.py [service_name]
    python standardize_services.py --all
    python standardize_services.py --dry-run [service_name]
"""

import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add the templates directory to the path for imports
template_dir = Path(__file__).parent / "templates" / "standard-service"
sys.path.insert(0, str(template_dir.parent))

# Service and agent directories
SERVICES_DIR = Path("services")
AGENTS_DIR = Path("agents")
TEMPLATE_DIR = Path("templates/standard-service")

# Known services and agents to standardize
SERVICES = [
    "api-gateway",
    "auth-service", 
    "database",
    "mcp-server",
    "memory",
    "network"
]

AGENTS = [
    "research-manager"
]

# Service name mappings for standardization
SERVICE_NAME_MAPPING = {
    "api-gateway": "api_gateway",
    "auth-service": "auth_service",
    "mcp-server": "mcp_server",
    "research-manager": "research_manager"
}

logger = logging.getLogger(__name__)


class ServiceStandardizer:
    """
    Handles standardization of individual services and agents.
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize standardizer.
        
        Args:
            dry_run: If True, only show what would be done without making changes
        """
        self.dry_run = dry_run
        self.changes_made = []
        self.backup_dir = Path("backups")
    
    def standardize_service(self, service_path: Path, service_type: str = "service") -> bool:
        """
        Standardize a single service or agent.
        
        Args:
            service_path: Path to the service directory
            service_type: Type of service ("service" or "agent")
            
        Returns:
            True if standardization was successful, False otherwise
        """
        service_name = service_path.name
        logger.info(f"Standardizing {service_type}: {service_name}")
        
        if self.dry_run:
            logger.info(f"DRY RUN: Would standardize {service_name}")
            self._analyze_service(service_path, service_name)
            return True
        
        try:
            # Create backup
            backup_path = self._create_backup(service_path)
            logger.info(f"Created backup at: {backup_path}")
            
            # Analyze current structure
            current_structure = self._analyze_service(service_path, service_name)
            
            # Apply standard structure
            self._apply_standard_structure(service_path, service_name, current_structure)
            
            # Migrate existing code
            self._migrate_existing_code(service_path, service_name, current_structure)
            
            # Update configuration files
            self._update_configuration(service_path, service_name)
            
            # Update Docker files
            self._update_docker_files(service_path, service_name)
            
            # Create or update tests
            self._setup_tests(service_path, service_name)
            
            logger.info(f"Successfully standardized {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to standardize {service_name}: {e}")
            if not self.dry_run:
                self._restore_backup(service_path, backup_path)
            return False
    
    def _create_backup(self, service_path: Path) -> Path:
        """Create backup of the service before modification."""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(exist_ok=True)
        
        backup_name = f"{service_path.name}_backup_{int(__import__('time').time())}"
        backup_path = self.backup_dir / backup_name
        
        shutil.copytree(service_path, backup_path)
        return backup_path
    
    def _restore_backup(self, service_path: Path, backup_path: Path):
        """Restore service from backup."""
        logger.info(f"Restoring {service_path.name} from backup")
        if service_path.exists():
            shutil.rmtree(service_path)
        shutil.copytree(backup_path, service_path)
    
    def _analyze_service(self, service_path: Path, service_name: str) -> Dict:
        """
        Analyze current service structure.
        
        Returns:
            Dictionary containing current structure information
        """
        structure = {
            "has_src_dir": (service_path / "src").exists(),
            "main_files": [],
            "config_files": [],
            "docker_files": [],
            "requirements_files": [],
            "startup_scripts": [],
            "test_files": [],
            "other_files": []
        }
        
        # Find main entry points
        for pattern in ["main.py", "*.py"]:
            for file in service_path.glob(pattern):
                if file.is_file() and not file.name.startswith('.'):
                    structure["main_files"].append(file.name)
        
        # Find configuration files
        for pattern in ["config.json", "config.yaml", "config.yml", "*.conf"]:
            for file in service_path.glob(pattern):
                if file.is_file():
                    structure["config_files"].append(file.name)
        
        # Find Docker files
        for pattern in ["Dockerfile*", "docker-compose*.yml"]:
            for file in service_path.glob(pattern):
                if file.is_file():
                    structure["docker_files"].append(file.name)
        
        # Find requirements files
        for pattern in ["requirements*.txt", "pyproject.toml", "setup.py"]:
            for file in service_path.glob(pattern):
                if file.is_file():
                    structure["requirements_files"].append(file.name)
        
        # Find startup scripts
        for pattern in ["start*.sh", "run*.sh", "*.sh"]:
            for file in service_path.glob(pattern):
                if file.is_file() and file.stat().st_mode & 0o111:
                    structure["startup_scripts"].append(file.name)
        
        # Find test files
        test_dir = service_path / "tests"
        if test_dir.exists():
            for file in test_dir.rglob("*.py"):
                structure["test_files"].append(str(file.relative_to(service_path)))
        
        logger.info(f"Current structure of {service_name}:")
        for key, value in structure.items():
            if value:
                logger.info(f"  {key}: {value}")
        
        return structure
    
    def _apply_standard_structure(self, service_path: Path, service_name: str, current_structure: Dict):
        """Apply the standard directory structure."""
        logger.info(f"Applying standard structure to {service_name}")
        
        # Create standard directories
        dirs_to_create = [
            "src",
            "config", 
            "tests",
            "logs"
        ]
        
        for dir_name in dirs_to_create:
            dir_path = service_path / dir_name
            if not dir_path.exists():
                dir_path.mkdir(exist_ok=True)
                logger.info(f"Created directory: {dir_name}")
    
    def _migrate_existing_code(self, service_path: Path, service_name: str, current_structure: Dict):
        """Migrate existing code to standard structure."""
        logger.info(f"Migrating existing code for {service_name}")
        
        src_dir = service_path / "src"
        
        # Move Python files to src/ if not already there
        if not current_structure["has_src_dir"]:
            for main_file in current_structure["main_files"]:
                if main_file.endswith('.py'):
                    source = service_path / main_file
                    target = src_dir / main_file
                    
                    if source.exists() and source != target:
                        shutil.move(str(source), str(target))
                        logger.info(f"Moved {main_file} to src/")
        
        # Copy template files if they don't exist
        template_files = {
            "src/config.py": self._customize_template_file("src/config.py", service_name),
            "src/models.py": self._customize_template_file("src/models.py", service_name),
            "src/health_check.py": self._customize_template_file("src/health_check.py", service_name),
            "src/utils.py": self._customize_template_file("src/utils.py", service_name),
        }
        
        for target_path, content in template_files.items():
            target_file = service_path / target_path
            if not target_file.exists():
                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Created {target_path} from template")
    
    def _update_configuration(self, service_path: Path, service_name: str):
        """Update configuration files."""
        logger.info(f"Updating configuration for {service_name}")
        
        config_dir = service_path / "config"
        
        # Create config.json
        config_content = self._create_service_config(service_name)
        config_file = config_dir / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_content, f, indent=2)
        logger.info("Created config/config.json")
        
        # Create logging.json
        logging_content = self._create_logging_config(service_name)
        logging_file = config_dir / "logging.json"
        with open(logging_file, 'w', encoding='utf-8') as f:
            json.dump(logging_content, f, indent=2)
        logger.info("Created config/logging.json")
        
        # Create .env.example
        env_content = self._create_env_example(service_name)
        env_file = service_path / ".env.example"
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        logger.info("Created .env.example")
    
    def _update_docker_files(self, service_path: Path, service_name: str):
        """Update Docker files."""
        logger.info(f"Updating Docker files for {service_name}")
        
        # Create Dockerfile
        dockerfile_content = self._customize_template_file("Dockerfile", service_name)
        dockerfile = service_path / "Dockerfile"
        with open(dockerfile, 'w', encoding='utf-8') as f:
            f.write(dockerfile_content)
        logger.info("Updated Dockerfile")
        
        # Create startup scripts
        start_content = self._customize_template_file("start.sh", service_name)
        start_file = service_path / "start.sh"
        with open(start_file, 'w', encoding='utf-8') as f:
            f.write(start_content)
        start_file.chmod(0o755)
        logger.info("Created start.sh")
        
        start_dev_content = self._customize_template_file("start-dev.sh", service_name)
        start_dev_file = service_path / "start-dev.sh"
        with open(start_dev_file, 'w', encoding='utf-8') as f:
            f.write(start_dev_content)
        start_dev_file.chmod(0o755)
        logger.info("Created start-dev.sh")
    
    def _setup_tests(self, service_path: Path, service_name: str):
        """Set up test structure."""
        logger.info(f"Setting up tests for {service_name}")
        
        tests_dir = service_path / "tests"
        
        # Create test files from templates
        test_files = {
            "conftest.py": self._customize_template_file("tests/conftest.py", service_name),
            "test_config.py": self._customize_template_file("tests/test_config.py", service_name),
            "test_health_check.py": self._customize_template_file("tests/test_health_check.py", service_name),
        }
        
        for filename, content in test_files.items():
            test_file = tests_dir / filename
            if not test_file.exists():
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Created tests/{filename}")
    
    def _customize_template_file(self, template_path: str, service_name: str) -> str:
        """
        Customize template file content for specific service.
        
        Args:
            template_path: Path to template file
            service_name: Name of the service
            
        Returns:
            Customized file content
        """
        template_file = TEMPLATE_DIR / template_path
        if not template_file.exists():
            logger.warning(f"Template file not found: {template_path}")
            return ""
        
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace placeholder with actual service name
        standardized_name = SERVICE_NAME_MAPPING.get(service_name, service_name.replace('-', '_'))
        content = content.replace("SERVICE_NAME_PLACEHOLDER", standardized_name)
        
        return content
    
    def _create_service_config(self, service_name: str) -> Dict:
        """Create service-specific configuration."""
        standardized_name = SERVICE_NAME_MAPPING.get(service_name, service_name.replace('-', '_'))
        
        return {
            "service": {
                "name": standardized_name,
                "version": "1.0.0",
                "description": f"Eunice {service_name} service",
                "environment": "development"
            },
            "server": {
                "host": "0.0.0.0",
                "port": 8000,
                "debug": False
            },
            "database": {
                "url": "postgresql://eunice:eunice@localhost:5432/eunice",
                "echo": False,
                "pool_size": 10,
                "max_overflow": 20
            },
            "mcp": {
                "server_url": "ws://mcp-server:8081",
                "timeout": 30,
                "retry_attempts": 3
            },
            "logging": {
                "level": "INFO",
                "file": "/app/logs/service.log",
                "max_file_size": "100MB",
                "backup_count": 5
            },
            "health_check": {
                "enabled": True,
                "interval": 30,
                "timeout": 10
            },
            "security": {
                "cors_origins": ["*"],
                "cors_methods": ["GET", "POST", "PUT", "DELETE"],
                "cors_headers": ["*"]
            }
        }
    
    def _create_logging_config(self, service_name: str) -> Dict:
        """Create logging configuration."""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
                },
                "simple": {
                    "format": "%(levelname)s - %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "simple",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "detailed",
                    "filename": "/app/logs/service.log",
                    "maxBytes": 104857600,
                    "backupCount": 5
                }
            },
            "loggers": {
                service_name.replace('-', '_'): {
                    "level": "DEBUG",
                    "handlers": ["console", "file"],
                    "propagate": False
                }
            },
            "root": {
                "level": "INFO",
                "handlers": ["console"]
            }
        }
    
    def _create_env_example(self, service_name: str) -> str:
        """Create .env.example file."""
        standardized_name = SERVICE_NAME_MAPPING.get(service_name, service_name.replace('-', '_')).upper()
        
        return f"""# {service_name} Service Environment Variables

# Service Configuration
SERVICE_NAME={service_name.replace('-', '_')}
SERVICE_VERSION=1.0.0
SERVICE_ENVIRONMENT=development
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000
SERVICE_DEBUG=false

# Database Configuration
DATABASE_URL=postgresql://eunice:eunice@localhost:5432/eunice

# MCP Server Configuration
MCP_SERVER_URL=ws://mcp-server:8081

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/service.log

# Security Configuration (if applicable)
JWT_SECRET=your-jwt-secret-here
API_KEY=your-api-key-here

# External API Configuration (if applicable)
EXTERNAL_API_URL=https://api.example.com
EXTERNAL_API_KEY=your-external-api-key-here

# Configuration File Override
CONFIG_FILE=/app/config/config.json
"""


def main():
    """Main entry point for the standardization script."""
    parser = argparse.ArgumentParser(description="Standardize Eunice services and agents")
    parser.add_argument("service", nargs="?", help="Specific service/agent to standardize")
    parser.add_argument("--all", action="store_true", help="Standardize all services and agents")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    standardizer = ServiceStandardizer(dry_run=args.dry_run)
    
    # Determine what to standardize
    targets = []
    
    if args.all:
        # Add all services
        for service_name in SERVICES:
            service_path = SERVICES_DIR / service_name
            if service_path.exists():
                targets.append((service_path, "service"))
        
        # Add all agents
        for agent_name in AGENTS:
            agent_path = AGENTS_DIR / agent_name
            if agent_path.exists():
                targets.append((agent_path, "agent"))
    
    elif args.service:
        # Find specific service or agent
        service_path = SERVICES_DIR / args.service
        agent_path = AGENTS_DIR / args.service
        
        if service_path.exists():
            targets.append((service_path, "service"))
        elif agent_path.exists():
            targets.append((agent_path, "agent"))
        else:
            logger.error(f"Service or agent '{args.service}' not found")
            return 1
    
    else:
        parser.print_help()
        return 1
    
    # Standardize targets
    success_count = 0
    total_count = len(targets)
    
    for target_path, target_type in targets:
        if standardizer.standardize_service(target_path, target_type):
            success_count += 1
    
    # Report results
    logger.info(f"Standardization complete: {success_count}/{total_count} successful")
    
    if args.dry_run:
        logger.info("This was a dry run - no changes were made")
    
    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
