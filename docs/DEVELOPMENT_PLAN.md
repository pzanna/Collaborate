# 🚀 Development Plan: Research Manager MCP Implementation

**Project**: Multi-AI Research System with Custom MCP Integration  
**Author**: Paul  
**Created**: 18 July 2025  
**Status**: Planning  
**Version**: 1.0

---

## 📋 Executive Summary

**Objective**: Complete replacement of the existing SimplifiedCoordinator with a Python-based Message Control Protocol (MCP) system that orchestrates specialized AI agents for research tasks.

**Key Decision**: Use Python for the entire backend stack (no Go) to maintain consistency and reduce complexity.

**Architecture**: Standalone Python MCP server + FastAPI backend + React frontend

---

## 🎯 Design Recommendations

### **1. Effort & Supportability Analysis**

| Approach              | Effort    | Supportability | Recommendation           |
| --------------------- | --------- | -------------- | ------------------------ |
| **Go MCP Server**     | High      | Medium         | ❌ Requires Go expertise |
| **Python MCP Server** | Medium    | High           | ✅ **RECOMMENDED**       |
| **Hybrid Approach**   | Very High | Low            | ❌ Too complex           |

**Rationale**: Python-only approach reduces technical debt, leverages existing team expertise, and maintains consistency with the current codebase.

### **2. Architecture Decision**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │  FastAPI Backend│    │  Python MCP     │
│                 │◄───►│                 │◄───►│  Server         │
│  - UI Components│    │  - REST API     │    │  - Agent Router │
│  - State Mgmt   │    │  - WebSocket    │    │  - Task Queue   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                              ┌─────────────────┐
                                              │  Research Agents│
                                              │  - Retriever    │
                                              │  - Reasoner     │
                                              │  - Executor     │
                                              │  - Memory       │
                                              └─────────────────┘
```

---

## 📊 Implementation Phases

### **Phase 1: MCP Server Foundation**

**Duration**: 3-4 days  
**Status**: ⏳ Planned

#### Deliverables:

- [ ] Python MCP server (`src/mcp/server.py`)
- [ ] Message protocols (`src/mcp/protocols.py`)
- [ ] Agent registry (`src/mcp/registry.py`)
- [ ] Task queue system (`src/mcp/queue.py`)
- [ ] Basic logging and monitoring

#### Technical Details:

```python
# Core MCP Message Structure
@dataclass
class ResearchAction:
    task_id: str
    context_id: str
    agent_type: str
    action: str
    payload: Dict[str, Any]
    priority: int = 1
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
```

#### Files to Create:

- `src/mcp/__init__.py`
- `src/mcp/server.py`
- `src/mcp/protocols.py`
- `src/mcp/registry.py`
- `src/mcp/queue.py`
- `src/mcp/client.py`

#### Configuration:

- [x] Extended `config/default_config.json` with MCP server settings
- [x] Added agent configurations and capabilities
- [x] Defined research task parameters

---

### **Phase 2: Research Manager Implementation**

**Duration**: 2-3 days  
**Status**: ⏳ Planned

#### Deliverables:

- [ ] Research Manager (`src/core/research_manager.py`)
- [ ] Task orchestration logic
- [ ] Context management
- [ ] Error handling and retries

#### Technical Details:

```python
class ResearchManager:
    """Orchestrates research tasks across multiple AI agents"""

    async def process_research_query(self, query: str, context_id: str) -> AsyncGenerator:
        """Main entry point for research tasks"""
        # 1. Analyze query and determine required agents
        # 2. Create task pipeline
        # 3. Coordinate agent execution
        # 4. Stream results back to user
```

#### Files to Create:

- `src/core/research_manager.py`
- `src/core/task_planner.py`
- `src/core/context_manager.py`

---

### **Phase 3: Agent Implementation**

**Duration**: 4-5 days  
**Status**: ⏳ Planned

#### Deliverables:

- [ ] Internet Search Agent (Retriever)
- [ ] Reasoning Agent
- [ ] Execution Agent
- [ ] Memory Agent
- [ ] Agent base class and interfaces

#### Agent Details:

**Internet Search Agent (Priority 1)**:

- DuckDuckGo API integration
- Web scraping capabilities
- Content extraction and summarization
- Search result ranking

**Reasoning Agent**:

- Chain-of-thought reasoning
- Analysis and synthesis
- Correlation finding
- Hypothesis generation

**Execution Agent**:

- Code execution (sandboxed)
- API calls
- Data processing
- File operations

**Memory Agent**:

- Context persistence
- Knowledge graph maintenance
- Previous conversation recall
- Learning from interactions

#### Files to Create:

- `src/agents/__init__.py`
- `src/agents/base.py`
- `src/agents/retriever.py`
- `src/agents/reasoner.py`
- `src/agents/executor.py`
- `src/agents/memory.py`
- `src/agents/tools/search.py`
- `src/agents/tools/web_scraper.py`

---

### **Phase 4: FastAPI Integration**

**Duration**: 1 day  
**Status**: ✅ **COMPLETE**

#### Deliverables:

- [x] Replace existing coordinator with MCP client
- [x] Update WebSocket handlers
- [x] Modify conversation endpoints
- [x] Add research task endpoints

#### Technical Details:

**New FastAPI Endpoints:**

- `POST /api/research/start` - Start research task
- `GET /api/research/task/{task_id}` - Get task status
- `DELETE /api/research/task/{task_id}` - Cancel task
- `WS /api/research/stream/{task_id}` - Real-time progress streaming

**Enhanced Chat Integration:**

- Research query detection (`research:`, `find:`, `search:`, `analyze:`)
- Automatic task creation and progress streaming
- Seamless integration with existing chat flow

**MCP Client Integration:**

- Lifecycle management in FastAPI
- Automatic connection to MCP server
- Graceful error handling when MCP unavailable

#### Files Modified:

- `web_server.py` - Added research endpoints and MCP integration
- `src/core/research_manager.py` - Fixed imports for integration
- `src/mcp/client.py` - Fixed imports for integration

#### Test Results:

- ✅ All integration tests passed
- ✅ Research endpoints functional
- ✅ WebSocket streaming working
- ✅ Backward compatibility maintained

---

### **Phase 5: Frontend Integration**

**Duration**: 2-3 days  
**Status**: ⏳ Planned

#### Deliverables:

- [ ] Research mode UI components
- [ ] Task progress visualization
- [ ] Agent status indicators
- [ ] Results display components

#### Files to Modify:

- `frontend/src/components/chat/ConversationView.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/store/slices/chatSlice.ts`

---

### **Phase 6: Testing & Polish**

**Duration**: 2-3 days  
**Status**: ⏳ Planned

#### Deliverables:

- [ ] Unit tests for all components
- [ ] Integration tests
- [ ] End-to-end research task tests
- [ ] Performance optimization
- [ ] Documentation updates

---

## 🛠 Technical Specifications

### **MCP Server Requirements**

```python
# Server Configuration
MCP_SERVER_CONFIG = {
    "host": "127.0.0.1",
    "port": 9000,
    "max_concurrent_tasks": 10,
    "task_timeout": 300,  # 5 minutes
    "retry_attempts": 3,
    "log_level": "INFO"
}
```

### **Agent Communication Protocol**

```python
# Agent Registration
{
    "agent_type": "retriever",
    "capabilities": ["web_search", "document_extraction"],
    "max_concurrent": 3,
    "timeout": 60
}

# Task Message
{
    "task_id": "uuid4",
    "context_id": "conversation_uuid",
    "agent_type": "retriever",
    "action": "web_search",
    "payload": {
        "query": "AI research papers 2024",
        "max_results": 10
    },
    "priority": 1
}
```

### **Database Schema Updates**

```sql
-- New tables for research tasks
CREATE TABLE research_tasks (
    id TEXT PRIMARY KEY,
    context_id TEXT NOT NULL,
    query TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    result TEXT
);

CREATE TABLE agent_actions (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    result TEXT,
    FOREIGN KEY (task_id) REFERENCES research_tasks(id)
);
```

---

## 📦 Dependencies

### **New Python Packages**

```txt
# MCP Server
asyncio-mqtt>=0.16.0
aiohttp>=3.9.0
websockets>=12.0

# Internet Search
duckduckgo-search>=4.0.0
beautifulsoup4>=4.12.0
requests>=2.31.0
selenium>=4.15.0  # For dynamic content

# Agent Framework
pydantic>=2.5.0
tenacity>=8.2.0  # For retries
celery>=5.3.0  # For task queue (optional)

# Security
python-dotenv>=1.0.0
cryptography>=41.0.0
```

---

## 🚀 Startup Integration

### **Updated start_web.sh**

```bash
#!/bin/bash

echo "🚀 Starting Collaborate Research Platform..."

# Start MCP server
echo "🔧 Starting MCP server..."
python -m src.mcp.server &
MCP_PID=$!

# Start FastAPI backend
echo "🖥️  Starting backend server..."
python web_server.py --reload &
BACKEND_PID=$!

# Start React frontend
echo "⚛️  Starting frontend..."
cd frontend && npm start &
FRONTEND_PID=$!

# Cleanup function
cleanup() {
    echo "Stopping services..."
    kill $MCP_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM
```

---

## 📈 Success Metrics

### **Phase Completion Criteria**

- [ ] **Phase 1**: MCP server starts and accepts connections
- [ ] **Phase 2**: Research Manager can create and route tasks
- [ ] **Phase 3**: Internet search agent returns relevant results
- [ ] **Phase 4**: FastAPI integration streams results to frontend
- [ ] **Phase 5**: Frontend displays research progress and results
- [ ] **Phase 6**: End-to-end research task completes successfully

### **Performance Targets**

- Task response time: < 5 seconds for simple queries
- Agent response time: < 30 seconds for complex searches
- Concurrent tasks: Support 10+ simultaneous research tasks
- Memory usage: < 500MB for MCP server

---

## 🔧 Development Environment

### **Setup Requirements**

1. Python 3.11+
2. Node.js 18+
3. SQLite 3
4. Chrome/Chromium (for web scraping)

### **Development Commands**

```bash
# Install dependencies
pip install -r requirements.txt
cd frontend && npm install

# Run tests
pytest src/tests/
npm test

# Start development
chmod +x start_web.sh
./start_web.sh
```

---

## 🎯 Next Steps

1. **Immediate**: Start Phase 1 - MCP Server Foundation
2. **This Week**: Complete Phases 1-2 (MCP + Research Manager)
3. **Next Week**: Implement Internet Search Agent (Phase 3)
4. **Week 3**: Integration and Testing (Phases 4-6)

---

## 📝 Notes & Design Changes

### **Design Decisions Made**:

- ✅ Python-only backend for consistency
- ✅ Standalone MCP server (not dockerized)
- ✅ Complete replacement of existing coordinator
- ✅ Internet search as first tool implementation

### **Open Questions**:

- Search API rate limits and caching strategy
- Agent failure handling and fallback mechanisms
- Context persistence across browser sessions
- Security considerations for web scraping

### **Future Considerations**:

- gRPC integration for better performance
- Agent plugin system for extensibility
- Distributed agent deployment
- Advanced reasoning capabilities

---

**Last Updated**: 18 July 2025  
**Next Review**: After Phase 1 completion
