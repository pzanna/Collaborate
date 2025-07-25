# Eunice Platform Cleanup Plan

## 🎯 Overview

This document outlines redundant files, outdated documentation, and unnecessary code that should be removed or consolidated following the literature agent restructuring and Phase 3 preparation.

## 📋 Files to Remove

### 1. Duplicate Documentation Files

#### Task Queue Implementation Summaries (DUPLICATE)

- ❌ **REMOVE**: `/docs/Task_Queue_Implementation_Summary.md` (192 lines)
- ✅ **KEEP**: `/docs/MCP/Task_Queue_Implementation_Summary.md` (174 lines)
- **Reason**: Same content, organized version in MCP directory is better

### 2. Obsolete Literature Agent Files

#### Original Literature Agent (REPLACED BY 4 NEW AGENTS)

- ❌ **REMOVE**: `/docs/Agents/Literature_Agent/` (entire directory)
  - `Literature_Agent_Documentation.md` (1,568 lines)
- **Reason**: Replaced by specialized Literature Search, Screening PRISMA, Synthesis Review, and Writer agents

#### Old Literature Agent Code (REPLACED)

- ❌ **REMOVE**: `/src/agents/literature/` (entire directory)
  - Contains old monolithic literature agent code
  - Now replaced by 4 specialized agent directories
- **Reason**: Architecture changed to 4-agent pipeline

### 3. Redundant Phase 3 Documentation

Since we have PHASE3_SERVICE_ARCHITECTURE.md with complete details:

- ❌ **CONSIDER CONSOLIDATING**:
  - `/docs/PHASE3_OVERVIEW.md` (high-level overview)
  - `/docs/PHASE3_IMPLEMENTATION_CHECKLIST.md` (implementation tasks)
- **Option**: Merge key content into PHASE3_MICROSERVICES_TRANSITION.md

### 4. Cache and Temporary Files

#### Python Cache Files

- ❌ **REMOVE**: `/__pycache__/` (entire directory)
  - Contains compiled Python bytecode
  - Should be regenerated automatically
  - Already in .gitignore

#### Log Files and Temporary Data

- ❌ **REMOVE**: `/dump.rdb` (Redis dump file)
  - Temporary Redis data file
  - Should not be in version control

### 5. Standalone Scripts (EVALUATE)

#### Root Level Scripts

- ❓ **EVALUATE**: `/agent_launcher.py`
  - Check if still used or replaced by new architecture
- ❓ **EVALUATE**: `/web_server.py`
  - Check if replaced by API Gateway implementation

## 🔄 Files to Consolidate

### 1. Phase 3 Documentation Consolidation

**Current Structure:**

```
docs/
├── PHASE3_OVERVIEW.md                    (high-level overview)
├── PHASE3_MICROSERVICES_TRANSITION.md    (comprehensive implementation guide)
├── PHASE3_SERVICE_ARCHITECTURE.md        (detailed service specs)
├── PHASE3_IMPLEMENTATION_CHECKLIST.md    (task checklist)
└── literature_agents_design.md           (design specification)
```

**Recommended Consolidation:**

1. **KEEP**: `PHASE3_MICROSERVICES_TRANSITION.md` as primary document
2. **KEEP**: `PHASE3_SERVICE_ARCHITECTURE.md` for technical reference
3. **MERGE INTO TRANSITION DOC**: Key content from PHASE3_OVERVIEW.md
4. **MERGE INTO TRANSITION DOC**: Checklist from PHASE3_IMPLEMENTATION_CHECKLIST.md
5. **KEEP**: `literature_agents_design.md` as specialized design reference

### 2. Architecture Documentation Structure

**Current Issues:**

- Multiple architecture documents with overlapping content
- Phase 2 status scattered across files

**Recommended:**

- Update `/docs/Architecture/Architecture.md` to reflect current Phase 2 completion
- Ensure Phase 3 plans are clearly separated from current architecture

## 🗂️ Recommended Directory Structure (Post-Cleanup)

```
docs/
├── Architecture/
│   ├── Architecture.md                   (current Phase 2 architecture)
│   └── Hierarchical_Research_Structure.md
├── Agents/                               (NEW 4-AGENT STRUCTURE)
│   ├── Literature_Search_Agent/
│   ├── Screening_PRISMA_Agent/
│   ├── Synthesis_Review_Agent/
│   ├── Writer_Agent/
│   ├── Planning_Agent/
│   ├── Executor_Agent/
│   ├── Research_Manager/
│   └── AI_Agent/
├── MCP/
│   └── Task_Queue_Implementation_Summary.md
├── API Gateway/
│   └── API_Gateway_Implementation_Summary.md
├── Database/
├── Personas/
├── Web UI/
├── PHASE2_STATUS.md                      (current status)
├── PHASE3_MICROSERVICES_TRANSITION.md   (consolidated Phase 3 guide)
├── PHASE3_SERVICE_ARCHITECTURE.md       (technical service specs)
└── literature_agents_design.md          (design specification)
```

## 🚀 Implementation Steps

### Step 1: Remove Redundant Files

```bash
# Remove duplicate task queue doc
rm docs/Task_Queue_Implementation_Summary.md

# Remove old literature agent documentation
rm -rf docs/Agents/Literature_Agent/

# Remove old literature agent code (AFTER VERIFICATION)
rm -rf src/agents/literature/

# Remove cache files
rm -rf __pycache__/
rm dump.rdb
```

### Step 2: Consolidate Phase 3 Documentation

1. Extract key content from PHASE3_OVERVIEW.md
2. Extract checklist items from PHASE3_IMPLEMENTATION_CHECKLIST.md  
3. Merge into PHASE3_MICROSERVICES_TRANSITION.md
4. Remove consolidated files

### Step 3: Update References

1. Update any README.md references to removed files
2. Update import statements that reference old literature agent
3. Update documentation links

### Step 4: Verification

1. Test that new 4-agent structure works without old literature agent
2. Verify no broken documentation links
3. Confirm all Phase 3 content is accessible

## ⚠️ Before Removal Checklist

- [ ] Verify new 4-agent literature pipeline is fully functional
- [ ] Confirm no active imports from `/src/agents/literature/`
- [ ] Check for any scripts that depend on old literature agent
- [ ] Backup any unique content from old documentation
- [ ] Test that removal doesn't break existing functionality

## 📊 Expected Impact

**Storage Savings:**

- ~1,700 lines of redundant documentation
- Multiple megabytes of cache files
- Cleaner repository structure

**Maintenance Benefits:**

- Single source of truth for Phase 3 planning
- Clear separation between old and new architecture
- Simplified agent documentation structure
- Reduced confusion about which agent documentation to use

**Risk Mitigation:**

- All removals should be done after verification
- Keep git history for recovery if needed
- Test thoroughly before finalizing cleanup

---

*This cleanup plan ensures the repository reflects the current 4-agent architecture while removing outdated and redundant content.*
