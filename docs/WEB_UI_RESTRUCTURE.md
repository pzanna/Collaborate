# Web UI Restructure - Layout and Naming Improvements

## Overview

This document outlines the comprehensive restructuring of the Web UI to address layout issues and inconsistent naming conventions.

## Key Changes Made

### 1. **Separated Workspaces**

- **Chat Workspace** (`/chat`): Dedicated space for AI conversations
- **Research Workspace** (`/research`): Dedicated space for research tasks and analysis
- **Projects View** (`/projects`): Project management interface
- **System Health** (`/health`): Monitoring and diagnostics

### 2. **Unified Naming Convention**

- **"Chat"** - For all conversational AI interactions
- **"Research"** - For structured research and analysis tasks
- **"Projects"** - For organizing work into logical groups
- **"Sessions"** - For individual research or chat instances

### 3. **Improved Layout Structure**

#### MainLayout (`components/layout/MainLayout.tsx`)

- Replaced `ChatLayout` with more generic `MainLayout`
- Better sidebar collapse behavior (16px collapsed, 320px expanded)
- Consistent navigation across all workspaces

#### Sidebar (`components/layout/Sidebar.tsx`)

- Collapsible sidebar with icon-only mode
- Clear navigation between workspaces
- Consistent terminology: "Chat", "Research", "Projects"
- Shows AI provider status at bottom
- Quick actions for creating new chats

#### Header (`components/layout/Header.tsx`)

- Contextual page titles with icons
- Workspace-specific quick actions
- Connection status indicator
- Consistent "New Chat" button

### 4. **Component Structure**

```
src/
├── components/
│   ├── layout/
│   │   ├── MainLayout.tsx       # Main app layout
│   │   ├── Sidebar.tsx          # Navigation sidebar
│   │   └── Header.tsx           # Top navigation bar
│   ├── chat/
│   │   ├── ChatWorkspace.tsx    # Clean chat interface
│   │   ├── MessageList.tsx      # Message display
│   │   └── MessageInput.tsx     # Chat input
│   ├── research/
│   │   ├── ResearchWorkspace.tsx # Research interface
│   │   └── ResearchResults.tsx   # Results display
│   └── projects/
│       └── ProjectsView.tsx      # Project management
```

### 5. **Routing Structure**

```
/                          -> Redirects to /chat
/chat                     -> Chat workspace (empty state)
/chat/:conversationId     -> Specific conversation
/research                 -> Research workspace (empty state)
/research/:sessionId      -> Specific research session
/projects                 -> Projects management
/health                   -> System health dashboard
```

### 6. **UX Improvements**

#### No More Overlapping Functions

- Chat and Research are now completely separate workspaces
- Each workspace has dedicated UI tailored to its purpose
- No mixed terminology or conflicting actions

#### Clear Visual Hierarchy

- **Chat Workspace**: Simple message list + input
- **Research Workspace**: Task panel + results panel + research input
- **Projects**: List view with management actions
- **Health**: System monitoring dashboard

#### Consistent Interactions

- All "New" buttons use consistent language
- Navigation is predictable across workspaces
- Status indicators are standardized

### 7. **Benefits**

1. **Better User Experience**

   - Clear separation of concerns
   - No more confusion between chat and research
   - Consistent navigation patterns

2. **Improved Maintainability**

   - Cleaner component structure
   - Better code organization
   - Easier to extend with new features

3. **Enhanced Scalability**
   - Modular workspace design
   - Easy to add new workspaces
   - Consistent layout patterns

## Migration Notes

### Breaking Changes

- Route `/conversation/:id` changed to `/chat/:conversationId`
- `ChatLayout` replaced with `MainLayout`
- `ConversationView` split into `ChatWorkspace` and `ResearchWorkspace`

### State Management

- Chat and Research state remain in the same Redux slices
- Navigation state improved with consistent path checking
- Sidebar state now properly handles collapse/expand

### Components

- Old overlapping components have been separated
- New workspace-specific components created
- Better prop interfaces and type safety

## Future Enhancements

1. **Research Workspace Enhancements**

   - Add research templates
   - Better result visualization
   - Export capabilities

2. **Chat Workspace Improvements**

   - Thread management
   - Message search
   - Conversation summaries

3. **Project Integration**
   - Filter conversations by project
   - Project-specific research sessions
   - Better project organization

## Testing Considerations

1. **Navigation Testing**

   - Verify all routes work correctly
   - Test sidebar collapse/expand behavior
   - Confirm workspace switching

2. **State Management**

   - Ensure WebSocket connections properly clean up
   - Test conversation/research session switching
   - Verify Redux state consistency

3. **Responsive Design**
   - Test on mobile devices
   - Verify sidebar behavior on small screens
   - Check header layout on different screen sizes
