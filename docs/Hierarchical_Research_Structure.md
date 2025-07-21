# Hierarchical Research Structure

## Overview

The Eunice research platform now uses a clear, hierarchical structure for organizing research work:

**Project → Research Topic → Plan → Tasks**

This provides better organization, clearer separation of concerns, and more intuitive navigation.

## Hierarchy Definition

### 1. Project

- **Purpose**: Top-level organizational unit for research initiatives
- **Examples**: "AI Safety Research", "Climate Change Analysis", "Market Research Study"
- **Contains**: Multiple research topics
- **Database**: `projects` table (existing)

### 2. Research Topic

- **Purpose**: Specific area of investigation within a project
- **Examples**: "AI Ethics Frameworks", "Bias Detection Methods", "Regulatory Compliance"
- **Contains**: Multiple research plans
- **Database**: `research_topics` table (new)

### 3. Research Plan

- **Purpose**: Structured approach to investigate a research topic
- **Examples**: "Comprehensive Literature Review", "Comparative Analysis", "Stakeholder Survey"
- **Contains**: Multiple tasks
- **Database**: `research_plans` table (new)

### 4. Task

- **Purpose**: Individual executable units of work within a plan
- **Examples**: "Search academic papers", "Analyze policy documents", "Generate summary report"
- **Types**: research, analysis, synthesis, validation
- **Database**: `research_tasks` table (updated)

## Example Hierarchy

```
📁 AI Safety Research Project
├── 📋 AI Ethics Frameworks (Research Topic)
│   ├── 📝 Comprehensive Literature Review (Plan)
│   │   ├── ⚡ Search academic papers (Task)
│   │   ├── ⚡ Analyze framework categories (Task)
│   │   └── ⚡ Generate comparative analysis (Task)
│   └── 📝 Industry Standards Analysis (Plan)
│       ├── ⚡ Research IEEE standards (Task)
│       └── ⚡ Compare with ISO guidelines (Task)
└── 📋 Bias Detection Methods (Research Topic)
    └── 📝 Algorithm Assessment Plan (Plan)
        ├── ⚡ Review detection algorithms (Task)
        ├── ⚡ Test on sample datasets (Task)
        └── ⚡ Benchmark performance (Task)
```

## API Structure

### New V2 API Endpoints

The new hierarchical API follows RESTful patterns:

```
# Research Topics
GET    /api/v2/projects/{project_id}/topics
POST   /api/v2/projects/{project_id}/topics
GET    /api/v2/topics/{topic_id}
PUT    /api/v2/topics/{topic_id}
DELETE /api/v2/topics/{topic_id}

# Research Plans
GET    /api/v2/topics/{topic_id}/plans
POST   /api/v2/topics/{topic_id}/plans
GET    /api/v2/plans/{plan_id}
PUT    /api/v2/plans/{plan_id}
DELETE /api/v2/plans/{plan_id}

# Tasks
GET    /api/v2/plans/{plan_id}/tasks
POST   /api/v2/plans/{plan_id}/tasks
GET    /api/v2/tasks/{task_id}
PUT    /api/v2/tasks/{task_id}
DELETE /api/v2/tasks/{task_id}

# Hierarchical Navigation
GET    /api/v2/projects/{project_id}/hierarchy
```

### Backward Compatibility

Legacy V1 endpoints remain available with deprecation warnings:

```
# Legacy endpoints (deprecated)
POST   /api/research/start              -> Use /api/v2/plans/{plan_id}/tasks
GET    /api/research/task/{task_id}     -> Use /api/v2/tasks/{task_id}
GET    /api/research-tasks              -> Use /api/v2/tasks/search
```

## Database Schema

### New Tables

```sql
-- Research Topics
CREATE TABLE research_topics (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    metadata TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (id)
);

-- Research Plans
CREATE TABLE research_plans (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    plan_type TEXT DEFAULT 'comprehensive',
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    estimated_cost REAL DEFAULT 0.0,
    actual_cost REAL DEFAULT 0.0,
    plan_structure TEXT DEFAULT '{}',
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (topic_id) REFERENCES research_topics (id)
);

-- Updated Tasks Table
ALTER TABLE research_tasks ADD COLUMN plan_id TEXT;
ALTER TABLE research_tasks ADD COLUMN task_type TEXT DEFAULT 'research';
ALTER TABLE research_tasks ADD COLUMN task_order INTEGER DEFAULT 0;
```

## Migration Process

### Automatic Migration

The system includes an automatic migration that:

1. **Creates new tables** for topics and plans
2. **Migrates existing data** by creating default topics and plans
3. **Updates task references** to link to the new plan structure
4. **Preserves all existing data** while adding the new hierarchy

### Running Migration

```bash
# Automatic migration on startup
python web_server.py  # Migration runs automatically

# Manual migration (if needed)
python hierarchical_migration.py data/eunice.db
```

### Migration Results

For existing projects with research tasks:

- Creates a default topic: "General Research"
- Creates a default plan: "Comprehensive Research Plan"
- Links all existing tasks to the default plan
- Preserves all task data and functionality

## Frontend Navigation

### New Navigation Flow

1. **Projects List** → Select project
2. **Project Detail** → View topics, plans overview
3. **Topic Detail** → View plans within topic
4. **Plan Detail** → View tasks within plan, execute research
5. **Task Detail** → View execution results, progress

### URL Structure

```
/projects                           # Projects list
/projects/{project_id}              # Project detail
/projects/{project_id}/topics       # Topics list
/topics/{topic_id}                  # Topic detail
/topics/{topic_id}/plans           # Plans list
/plans/{plan_id}                   # Plan detail
/plans/{plan_id}/tasks             # Tasks list
/tasks/{task_id}                   # Task detail
```

## Benefits

### 1. Better Organization

- Clear separation between investigation areas (topics) and approaches (plans)
- Logical grouping of related work
- Easier to find and manage research efforts

### 2. Reusable Plans

- Plans can be templates applied to multiple topics
- Standard research methodologies can be packaged as reusable plans
- Consistency across similar research efforts

### 3. Granular Tracking

- Progress tracking at project, topic, plan, and task levels
- Cost tracking aggregated up the hierarchy
- Status monitoring across all levels

### 4. Improved Scalability

- Supports complex projects with multiple investigation areas
- Better performance with focused queries
- Cleaner data model for large-scale research

### 5. Enhanced User Experience

- Intuitive drill-down navigation
- Contextual breadcrumbs showing current location
- Clear mental model of research organization

## Usage Examples

### Creating a Research Workflow

```typescript
// 1. Create research topic
const topic = await api.createResearchTopic(projectId, {
  name: "AI Ethics Frameworks",
  description: "Investigate existing AI ethics frameworks and standards",
})

// 2. Create research plan
const plan = await api.createResearchPlan(topic.id, {
  name: "Comprehensive Literature Review",
  description: "Systematic review of academic and industry frameworks",
  plan_type: "comprehensive",
})

// 3. Create tasks within the plan
const searchTask = await api.createTask(plan.id, {
  name: "Search Academic Literature",
  task_type: "research",
  query: "AI ethics frameworks academic literature",
  task_order: 1,
})

const analysisTask = await api.createTask(plan.id, {
  name: "Analyze Framework Categories",
  task_type: "analysis",
  task_order: 2,
})
```

### Navigation Example

```typescript
// Navigate through hierarchy
const project = await api.getProject(projectId)
const topics = await api.getProjectTopics(projectId)
const plans = await api.getTopicPlans(topicId)
const tasks = await api.getPlanTasks(planId)

// Get complete hierarchy view
const hierarchy = await api.getProjectHierarchy(projectId)
```

## Migration Checklist

- [x] Database schema updated
- [x] Data models created
- [x] Migration script implemented
- [x] API endpoints designed
- [ ] Frontend components updated
- [ ] Documentation updated
- [ ] Testing completed
- [ ] Migration deployed

## Next Steps

1. **Complete API Implementation**: Finish implementing the database operations for the new endpoints
2. **Update Frontend Components**: Create new React components for the hierarchical navigation
3. **Testing**: Comprehensive testing of migration and new functionality
4. **Documentation**: Update all user-facing documentation
5. **Training**: Update any training materials or user guides

The hierarchical structure provides a much clearer and more scalable approach to organizing research work, making it easier for users to understand and navigate their research projects.
