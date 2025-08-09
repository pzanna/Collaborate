#!/usr/bin/env python3
"""
API Gateway (MCP Client) — Eunice Research Platform
Version: v0.5.    # Auto-configure based on environment if no config found
    config = DEFAULT_CFG.copy()
    
    # In container environment, auto-detect other Eunice services
    if os.getenv("KUBERNETES_SERVICE_HOST") or os.getenv("DOCKER_HOST") or os.path.exists("/.dockerenv"):
        logger.info("Container environment detected, applying container-specific MCP configuration")
        config["servers"] = {
            "database": {"transport": "http", "url": "http://database-service:8010/mcp/"},
            # Note: Only database service currently has MCP server implementation
            # Other services would need MCP servers added to enable these:
            # "network": {"transport": "http", "url": "http://network-service:8008/mcp/"},
            # "memory": {"transport": "http", "url": "http://memory-service:8009/mcp/"},
            # "auth": {"transport": "http", "url": "http://auth-service:8013/mcp/"},
        }
        config['_source'] = 'auto-detected-container'
    else:
        config['_source'] = 'default'
    
    return configd compliant, client-side multiplexing)

This service exposes a thin FastAPI layer and maintains one MCP client session per server.
- No hub/broker. The gateway is the MCP *client*.
- Uses python-sdk (ClientSession + streamable HTTP / stdio transports).
- Provides a single invoke surface for agents: POST /mcp/invoke
- Exposes /health with discovered tools per server.
"""

import asyncio
import contextlib
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ---- MCP SDK imports ----
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import stdio_client, StdioServerParameters

logger = logging.getLogger("eunice.api_gateway")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# -----------------------------
# Request/Response Models
# -----------------------------

class InvokeRequest(BaseModel):
    """Request model for MCP tool invocation."""
    server: str = Field(..., description="MCP server identifier")
    tool: str = Field(..., description="Tool name to invoke")
    params: dict = Field(default_factory=dict, description="Tool parameters")
    timeout: float = Field(default=60.0, description="Timeout in seconds")

# -----------------------------
# Configuration
# -----------------------------

DEFAULT_CFG = {
    "servers": {
        # Example HTTP server (preferred for inter-container communication)
        # Note: In containers, use service names as hostnames
        # "database": {"transport": "http", "url": "http://database-service:8010/mcp"},
        # "network": {"transport": "http", "url": "http://network-service:8008/mcp"},
        # "memory": {"transport": "http", "url": "http://memory-service:8009/mcp"},
        # "auth": {"transport": "http", "url": "http://auth-service:8013/mcp"},
        # 
        # Example stdio server (for local/development)
        # "local_tool": {"transport": "stdio", "cmd": ["python", "-m", "tools.local_server"]},
    }
}


def load_config() -> dict:
    """Load minimal MCP client config from env JSON or file path."""
    cfg_env = os.getenv("MCP_CFG_JSON")
    if cfg_env:
        try:
            return json.loads(cfg_env)
        except Exception as e:
            logger.warning("Invalid MCP_CFG_JSON: %s", e)
    
    # Try multiple config file locations for container/development flexibility
    config_paths = [
        os.getenv("MCP_CFG_FILE", "/etc/eunice/mcp.json"),  # Production container path
        "/app/config/mcp.json",  # Container config directory
        "./config/mcp.json",     # Development path
        "./mcp.json"             # Fallback
    ]
    
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    config['_source'] = path  # Track config source
                    logger.info("Loaded MCP config from: %s", path)
                    return config
            except Exception as e:
                logger.warning("Invalid MCP config file at %s: %s", path, e)
    
    # Auto-configure based on environment if no config found
    config = DEFAULT_CFG.copy()
    
    # In container environment, auto-detect other Eunice services
    if os.getenv("KUBERNETES_SERVICE_HOST") or os.getenv("DOCKER_HOST") or os.path.exists("/.dockerenv"):
        logger.info("Container environment detected, applying container-specific MCP configuration")
        config["servers"] = {
            "database": {"transport": "http", "url": "http://database-service:8010/mcp/"},
            "network": {"transport": "http", "url": "http://network-service:8008/mcp/"},
            "memory": {"transport": "http", "url": "http://memory-service:8009/mcp/"},
            "auth": {"transport": "http", "url": "http://auth-service:8013/mcp/"},
        }
        config['_source'] = 'auto-detected-container'
    else:
        config['_source'] = 'default'
    
    return config


# -----------------------------
# MCP Client plumbing
# -----------------------------

@dataclass
class _SessionHolder:
    session: Optional[ClientSession] = None
    cm: Any = None  # context manager handle for transport


class MCPClient:
    """Single MCP session for one server (http or stdio)."""
    def __init__(self, server_id: str, cfg: dict):
        self.server_id = server_id
        self.cfg = cfg
        self._holder = _SessionHolder()

    async def connect(self, max_retries: int = 3, retry_delay: float = 2.0):
        """Connect to MCP server with retry logic for container environments."""
        transport = self.cfg.get("transport")
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if transport == "http":
                    url = self.cfg.get("url")
                    if not url:
                        raise ValueError(f"{self.server_id}: http transport requires url")
                    self._holder.cm = streamablehttp_client(url)
                elif transport == "stdio":
                    cmd = self.cfg.get("cmd")
                    if not cmd:
                        raise ValueError(f"{self.server_id}: stdio transport requires cmd")
                    params = StdioServerParameters(command=cmd[0], args=cmd[1:], env=self.cfg.get("env"))
                    self._holder.cm = stdio_client(params)
                else:
                    raise ValueError(f"{self.server_id}: unsupported transport {transport}")

                read, write, *_ = await self._holder.cm.__aenter__()
                self._holder.session = ClientSession(read, write)
                if self._holder.session:
                    await self._holder.session.initialize()
                    logger.info("Successfully connected to MCP server: %s", self.server_id)
                    return
                else:
                    raise RuntimeError(f"{self.server_id}: failed to create session")
                    
            except Exception as e:
                last_error = e
                logger.warning(
                    "Failed to connect to MCP server %s (attempt %d/%d): %s", 
                    self.server_id, attempt + 1, max_retries, e
                )
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(
                        "Failed to connect to MCP server %s after %d attempts: %s",
                        self.server_id, max_retries, last_error
                    )
                    raise last_error

    async def list_tools(self) -> list[str]:
        if not self._holder.session:
            raise RuntimeError(f"{self.server_id}: not connected")
        resp = await self._holder.session.list_tools()
        return [t.name for t in resp.tools]

    async def call(self, tool: str, arguments: dict, timeout: float = 60.0) -> dict:
        if not self._holder.session:
            raise RuntimeError(f"{self.server_id}: not connected")
        result = await asyncio.wait_for(self._holder.session.call_tool(tool, arguments=arguments), timeout=timeout)
        
        # Handle both legacy and new structured output format
        if hasattr(result, 'structuredContent') and result.structuredContent is not None:
            return result.structuredContent
        elif result.content and len(result.content) > 0:
            # Return first content item if available
            first_content = result.content[0]
            if hasattr(first_content, 'text'):
                return {"result": first_content.text}
            else:
                return {"result": str(first_content)}
        else:
            return {"result": "No content returned"}

    async def close(self):
        with contextlib.suppress(Exception):
            if self._holder.session:
                await self._holder.session.close()
            if self._holder.cm:
                await self._holder.cm.__aexit__(None, None, None)


class MCPMux:
    """Holds N MCPClient instances and routes calls by server_id."""
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}

    async def start(self, cfg: dict):
        """Start all MCP clients with enhanced error handling for containers."""
        tasks = []
        
        # Get connection parameters from config or environment
        max_retries = int(os.getenv("MCP_MAX_RETRIES", cfg.get("client", {}).get("max_retries", 3)))
        retry_delay = float(os.getenv("MCP_RETRY_DELAY", cfg.get("client", {}).get("retry_delay", 2.0)))
        
        for sid, scfg in cfg.get("servers", {}).items():
            c = MCPClient(sid, scfg)
            self.clients[sid] = c
            
            # Create connection task with custom retry parameters
            task = asyncio.create_task(
                c.connect(max_retries=max_retries, retry_delay=retry_delay),
                name=f"connect-{sid}"
            )
            tasks.append(task)
        
        if tasks:
            # Gather results but don't fail if some connections fail
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log connection results
            for i, (sid, result) in enumerate(zip(cfg.get("servers", {}).keys(), results)):
                if isinstance(result, Exception):
                    logger.error("Failed to connect to MCP server %s: %s", sid, result)
                    # Remove failed client from active clients
                    self.clients.pop(sid, None)
                else:
                    logger.info("Successfully connected to MCP server: %s", sid)

    async def list_all(self) -> Dict[str, list[str]]:
        out = {}
        for sid, c in self.clients.items():
            try:
                out[sid] = await c.list_tools()
            except Exception as e:
                out[sid] = [f"ERROR: {e}"]
        return out

    async def invoke(self, server: str, tool: str, params: dict, timeout: float = 60.0) -> dict:
        if server not in self.clients:
            raise KeyError(f"Unknown server '{server}'")
        return await self.clients[server].call(tool, params, timeout=timeout)

    async def close(self):
        await asyncio.gather(*(c.close() for c in self.clients.values()), return_exceptions=True)


# -----------------------------
# FastAPI surface
# -----------------------------

from contextlib import asynccontextmanager

_mux: Optional[MCPMux] = None
_cfg: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mux, _cfg
    _cfg = load_config()
    _mux = MCPMux()
    await _mux.start(_cfg)
    logger.info("MCP client sessions started for servers: %s", list(_mux.clients.keys()))
    yield
    await _mux.close()

app = FastAPI(lifespan=lifespan)  # Define the FastAPI app instance with lifespan handler


@app.get("/health")
async def health():
    """Enhanced health check with container environment awareness."""
    logger.info("Performing health check on MCP servers")
    if not _mux:
        raise HTTPException(503, "MCP not initialised")
    
    # Basic connectivity check using direct HTTP calls to avoid session issues
    import aiohttp
    import asyncio as aio
    
    servers_status = {}
    tools = {}
    logger.info("Performing health check on MCP servers")
    # Check each server's health status using direct HTTP
    for server_id, client in _mux.clients.items():
        try:
            # Get the server URL from client config
            server_url = client.cfg.get("url", "")
            if server_url:
                # Make direct HTTP call to list tools
                logger.info("Checking health of server %s at %s", server_id, server_url)
                async with aiohttp.ClientSession() as session:
                    headers = {
                        "Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream"
                    }
                    data = {
                        "jsonrpc": "2.0",
                        "id": "1",
                        "method": "tools/list",
                        "params": {}
                    }
                    
                    timeout = aiohttp.ClientTimeout(total=5.0)
                    async with session.post(server_url, json=data, headers=headers, timeout=timeout) as response:
                        logger.info("Received response from server %s: %s", server_id, response.status)
                        if response.status == 200:
                            # Handle streamable HTTP response
                            content = await response.text()
                            
                            # Parse event-stream format
                            server_tools = []
                            if content.startswith("event: message"):
                                lines = content.split('\n')
                                for line in lines:
                                    if line.startswith("data: "):
                                        import json
                                        try:
                                            json_data = json.loads(line[6:])  # Remove "data: " prefix
                                            if "result" in json_data and "tools" in json_data["result"]:
                                                server_tools = [tool["name"] for tool in json_data["result"]["tools"]]
                                        except:
                                            pass
                            
                            servers_status[server_id] = {
                                "status": "healthy",
                                "tools_count": len(server_tools),
                                "tools": server_tools
                            }
                            tools[server_id] = server_tools
                        else:
                            servers_status[server_id] = {
                                "status": "error",
                                "error": f"HTTP {response.status}",
                                "tools_count": 0,
                                "tools": []
                            }
                            tools[server_id] = [f"ERROR: HTTP {response.status}"]
            else:
                servers_status[server_id] = {
                    "status": "error",
                    "error": "No URL configured",
                    "tools_count": 0,
                    "tools": []
                }
                tools[server_id] = ["ERROR: No URL configured"]
                
        except Exception as e:
            logger.exception("Direct health check failed for server %s: %s", server_id, e)
            servers_status[server_id] = {
                "status": "error",
                "error": str(e),
                "tools_count": 0,
                "tools": []
            }
            tools[server_id] = [f"ERROR: {e}"]
    
    # Container environment detection
    is_container = (
        os.getenv("KUBERNETES_SERVICE_HOST") is not None or 
        os.getenv("DOCKER_HOST") is not None or 
        os.path.exists("/.dockerenv")
    )
    
    return {
        "ok": True,
        "service": "api-gateway",
        "environment": "container" if is_container else "native",
        "servers": list(_mux.clients.keys()),
        "servers_status": servers_status,
        "tools": tools,
        "config_source": getattr(_cfg, '_source', 'default'),
        "mcp_version": "v0.5.1"
    }


@app.post("/mcp/invoke")
async def mcp_invoke(req: InvokeRequest):
    if not _mux:
        raise HTTPException(503, "MCP not initialised")
    try:
        result = await _mux.invoke(req.server, req.tool, req.params, timeout=req.timeout)
        return {"ok": True, "result": result}
    except KeyError as e:
        raise HTTPException(404, str(e))
    except asyncio.TimeoutError:
        raise HTTPException(504, "Tool call timed out")
    except Exception as e:
        logger.exception("Tool invocation failed for %s.%s: %s", req.server, req.tool, e)
        raise HTTPException(500, f"Invocation error: {e}")


def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
