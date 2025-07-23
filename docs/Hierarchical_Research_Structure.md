# Hierarchical Research Structure

## Overview

The Eunice research platform now uses a clear, hierarchical structure for organizing research work:

**_Project → Research Topic → Research Plan → Task_**

Each research project contains multiple topics, each topic contains one or more research plans, and each plan is made up of individual tasks. This hierarchy ensures a logical flow from broad initiatives down to actionable work items.

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

```plaintext
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

```plaintext
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

## Database Schema

### Tables

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
```

## Frontend Navigation

### Navigation Flow

1. **Projects List** → Select project
2. **Project Detail** → View topics, plans overview
3. **Topic Detail** → View plans within topic
4. **Plan Detail** → View tasks within plan, execute research
5. **Task Detail** → View execution results, progress

### URL Structure

```bash
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

## Next Steps

The hierarchical structure provides a much clearer and more scalable approach to organizing research work, making it easier for users to understand and navigate their research projects.
