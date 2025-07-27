"""
Database Service Client for API Gateway
Provides HTTP client to interact with the dedicated database service container.
This replaces direct database access with HTTP calls to the database service.
API Gateway is ONLY ALLOWED TO READ from the database service.
"""
import logging
from typing import Dict, List, Optional, Any
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class DatabaseServiceClient:
    def __init__(self, base_url: str = "http://eunice-database-service:8011"):
        """
        Initialize the database service client.
        
        Args:
            base_url: The base URL of the database service
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the database service."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"Database service health check failed: {e}")
            raise HTTPException(status_code=503, detail="Database service unavailable")
        except httpx.HTTPStatusError as e:
            logger.error(f"Database service health check error: {e}")
            raise HTTPException(status_code=503, detail="Database service unhealthy")
    
    async def get_projects(self, status_filter: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all projects with optional filtering.
        
        Args:
            status_filter: Filter by project status (currently not implemented in DB service)
            limit: Limit number of results (currently not implemented in DB service)
            
        Returns:
            List of project dictionaries
        """
        try:
            # Note: Current database service doesn't support status_filter or limit
            # but we maintain the API for future compatibility
            response = await self.client.get(f"{self.base_url}/projects")
            response.raise_for_status()
            projects = response.json()
            
            # Apply client-side filtering if needed (temporary until DB service supports it)
            # Handle case where limit might be a FastAPI Query object or integer
            limit_int = None
            if limit is not None:
                if isinstance(limit, int):  # Direct integer value
                    limit_int = limit
                elif hasattr(limit, 'default'):  # FastAPI Query object
                    limit_int = limit.default if limit.default is not None else None
            
            if limit_int is not None and len(projects) > limit_int:
                projects = projects[:limit_int]
                
            # Convert to the format expected by the API Gateway
            return [self._convert_project_format(project) for project in projects]
            
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch projects: {e}")
            raise HTTPException(status_code=503, detail="Database service unavailable")
        except httpx.HTTPStatusError as e:
            logger.error(f"Database service error: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="Database service error")
    
    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific project by ID.
        
        Args:
            project_id: The project ID
            
        Returns:
            Project dictionary or None if not found
        """
        try:
            # Convert string project_id to integer for the database service
            try:
                project_id_int = int(project_id)
            except ValueError:
                logger.warning(f"Invalid project ID format: {project_id}")
                return None
                
            response = await self.client.get(f"{self.base_url}/projects/{project_id_int}")
            
            if response.status_code == 404:
                return None
                
            response.raise_for_status()
            project = response.json()
            
            # Convert to the format expected by the API Gateway
            return self._convert_project_format(project)
            
        except httpx.RequestError as e:
            logger.error(f"Failed to fetch project {project_id}: {e}")
            raise HTTPException(status_code=503, detail="Database service unavailable")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Database service error: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="Database service error")
    
    async def create_project(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new project.
        
        Args:
            name: Project name
            description: Project description
            
        Returns:
            Created project dictionary
        """
        try:
            project_data = {
                "name": name,
                "description": description
            }
            
            response = await self.client.post(
                f"{self.base_url}/projects",
                json=project_data
            )
            response.raise_for_status()
            project = response.json()
            
            # Convert to the format expected by the API Gateway
            return self._convert_project_format(project)
            
        except httpx.RequestError as e:
            logger.error(f"Failed to create project: {e}")
            raise HTTPException(status_code=503, detail="Database service unavailable")
        except httpx.HTTPStatusError as e:
            logger.error(f"Project creation error: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="Project creation failed")
    
    def _convert_project_format(self, project: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert database service project format to API Gateway expected format.
        
        Args:
            project: Project data from database service
            
        Returns:
            Project data in API Gateway format
        """
        # Convert the database service format to match what the API Gateway expects
        return {
            "id": str(project["id"]),  # Convert to string as expected by API Gateway
            "name": project["name"],
            "description": project.get("description", ""),
            "status": "active",  # Default status since database service doesn't track this yet
            "created_at": project["created_at"],
            "updated_at": project["updated_at"],
            # Add any other fields that the API Gateway expects
            "metadata": {}
        }
    
    async def close(self):
        """Close the HTTP client connection."""
        if self.client:
            await self.client.aclose()
