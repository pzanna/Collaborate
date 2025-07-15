# Chat Application Design Guide - Slack/Teams Style Interface

## Overview

This guide outlines specific design patterns and UI components for creating a Slack/Teams-inspired chat interface for the Collaborate AI Platform. The goal is to leverage familiar chat application patterns to create an intuitive, engaging user experience.

## 🎨 Visual Design Reference

### Layout Inspiration

**Slack Desktop Layout:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Workspace Header: "AI Collaboration" | Search | Notifications | Profile │
├─────────────┬───────────────────────────────────────────────────────────┤
│ Left Panel  │ Main Chat Area                                            │
│             │ ┌─────────────────────────────────────────────────────────┐ │
│ 📁 Projects │ │ # conversation-name    👥 2 AIs     🔧 ⭐ 📌 ℹ️        │ │
│ • Research  │ ├─────────────────────────────────────────────────────────┤ │
│ • Dev Work  │ │ Chat Messages (with infinite scroll)                   │ │
│             │ │                                                         │ │
│ 💬 Recent   │ │ ┌─────────────────────────────────┐         10:30 AM  │ │
│ • AI Help*  │ │ │ 👤 You                          │                    │ │
│ • Code Rev  │ │ │ Can you help me debug this?     │                    │ │
│ • Planning  │ │ └─────────────────────────────────┘                    │ │
│             │ │ ┌─────────────────────────────────┐  🟢 OpenAI  10:31 │ │
│ 🤖 AI Team  │ │ │ 🤖 OpenAI                       │                    │ │
│ 🟢 OpenAI   │ │ │ I'd be happy to help! Can you   │                    │ │
│ 🟢 xAI      │ │ │ share the error message?        │  ❤️ 👍            │ │
│             │ │ └─────────────────────────────────┘                    │ │
│ + New Chat  │ │ ┌─────────────────────────────────┐  🟢 xAI     10:32 │ │
│             │ │ │ 🤖 xAI                          │                    │ │
│             │ │ │ Also, what's your setup? IDE,   │                    │ │
│             │ │ │ Node version, etc.?             │                    │ │
│             │ │ └─────────────────────────────────┘                    │ │
│             │ ├─────────────────────────────────────────────────────────┤ │
│             │ │ ┌─────────────────────────────────────┐ 📎 😊 🎤 ⚡   │ │
│             │ │ │ Message @openai @xai...             │ [ Send ]       │ │
│             │ │ └─────────────────────────────────────┘                │ │
│             │ └─────────────────────────────────────────────────────────┘ │
└─────────────┴───────────────────────────────────────────────────────────┘
```

## 💬 Chat Message Components

### Message Types & Styling

#### User Messages (Right-aligned, like Slack)

```typescript
interface UserMessageBubble {
  alignment: "right"
  backgroundColor: "#1264a3" // Slack blue
  textColor: "white"
  maxWidth: "70%"
  borderRadius: "18px 18px 4px 18px"
  padding: "12px 16px"
  marginBottom: "8px"

  components: {
    avatar: SmallUserAvatar | null // Hidden for consecutive messages
    timestamp: "10:30 AM" // On hover or new message group
    status: "sending" | "sent" | "delivered" | "failed"
    actions: [Edit, Delete, React] // On hover
  }
}
```

#### AI Messages (Left-aligned, like other users)

```typescript
interface AIMessageBubble {
  alignment: "left"
  backgroundColor: "#f8f9fa" // Light gray
  textColor: "#1d1c1d" // Dark text
  maxWidth: "70%"
  borderRadius: "18px 18px 18px 4px"
  padding: "12px 16px"
  marginBottom: "8px"

  components: {
    avatar: ProviderAvatar // Always shown for AI messages
    providerBadge: "AI" | "Bot"
    username: "OpenAI" | "xAI"
    timestamp: "10:31 AM"
    status: "typing" | "streaming" | "complete"
    actions: [React, Reply, Copy, Share] // On hover
    reactions: EmojiReactionBar // Below message
  }
}
```

#### System Messages (Centered, minimal)

```typescript
interface SystemMessageBubble {
  alignment: "center"
  backgroundColor: "transparent"
  textColor: "#868686" // Muted gray
  fontSize: "13px"
  fontStyle: "italic"

  examples: [
    "🎯 Response queue: OpenAI → xAI",
    "🔗 OpenAI handed off to xAI",
    "✅ Conversation completed",
    "🚨 Connection restored"
  ]
}
```

## 🚀 Interactive Elements

### Typing Indicators (Slack-style)

```typescript
interface TypingIndicator {
  display: "🤖 OpenAI is typing..."
  position: "bottom_of_chat"
  animation: {
    dots: ThreeBouncingDots
    duration: "1.4s infinite"
    color: "#868686"
  }
  timeout: 30000 // Hide after 30s if no message
}
```

### Message Reactions (Slack/Teams pattern)

```typescript
interface MessageReactions {
  quickReactions: ["❤️", "👍", "👎", "😊", "😮", "🎉"]
  reactionPicker: EmojiPickerModal
  reactionBar: {
    display: "❤️ 2 👍 1" // Count per emoji
    onClick: AddOrRemoveReaction
    maxVisible: 5 // Then show "+2 more"
  }
}
```

### @Mention System (Slack-style)

```typescript
interface MentionSystem {
  trigger: "@"
  autocomplete: {
    options: [
      { name: "openai"; avatar: OpenAIAvatar; status: "online" },
      { name: "xai"; avatar: XAIAvatar; status: "online" }
    ]
    styling: DropdownWithArrowNavigation
  }

  mentionStyling: {
    backgroundColor: "#1264a3"
    textColor: "white"
    borderRadius: "3px"
    padding: "1px 4px"
    fontWeight: "bold"
  }
}
```

## 📱 Navigation Patterns

### Left Sidebar (Slack Pattern)

```typescript
interface LeftSidebar {
  sections: [
    {
      title: "⭐ Starred"
      collapsible: true
      items: StarredConversation[]
    },
    {
      title: "📁 Projects"
      collapsible: true
      items: ProjectFolder[]
      actions: {
        hover: ShowCreateProjectButton
        rightClick: [Create, Join, Settings]
      }
    },
    {
      title: "💬 Direct Messages"
      collapsible: false
      items: RecentConversation[]
      showUnreadBadges: true
    },
    {
      title: "🤖 AI Team"
      collapsible: true
      items: [
        { name: "OpenAI"; status: "online"; responseTime: "~2s" },
        { name: "xAI"; status: "online"; responseTime: "~3s" }
      ]
    }
  ]
}
```

### Conversation List Items

```typescript
interface ConversationListItem {
  layout: {
    avatar: ProviderAvatars | ProjectIcon
    title: ConversationName
    preview: LastMessagePreview // "You: Can you help..." or "OpenAI: Sure..."
    timestamp: RelativeTime // "2m" or "Yesterday"
    unreadBadge: number | null
    statusIndicator: "online" | "away" | "offline"
  }

  states: {
    normal: NormalStyling
    unread: { fontWeight: "bold"; backgroundColor: "#f8f9fa" }
    active: { backgroundColor: "#1264a3"; textColor: "white" }
    muted: { opacity: 0.6; hideNotifications: true }
  }

  interactions: {
    click: OpenConversation
    rightClick: [Pin, Mute, Archive, Delete]
    hover: ShowQuickActions
  }
}
```

## 🎛️ Input Area (Teams/Slack Style)

### Rich Text Input

```typescript
interface RichTextInput {
  placeholder: "Message AI Team..."

  toolbar: {
    formatting: [Bold, Italic, Code, CodeBlock, BulletList, Link]
    position: "above_input" // Like Teams
    showOnFocus: true
  }

  features: {
    mentionSupport: "@openai @xai"
    emojiSupport: ":smile: :rocket:"
    fileUpload: DragAndDrop
    pasteSupport: SmartPasteFormatting
    keyboardShortcuts: {
      send: "Enter"
      newLine: "Shift+Enter"
      mention: "@"
      emoji: ":"
    }
  }

  actionBar: {
    attachFile: FileUploadButton
    emoji: EmojiPickerButton
    mention: MentionButton
    send: SendButton
    voiceMessage: VoiceRecorderButton // Future
  }
}
```

## 🔍 Search Functionality (Slack Pattern)

### Global Search (Ctrl+K)

```typescript
interface GlobalSearch {
  trigger: ["Ctrl+K", "Cmd+K"]

  modal: {
    placeholder: "Search conversations, messages..."
    recentSearches: RecentQuery[]
    quickFilters: ["from:openai", "in:project-name", "has:link"]
  }

  results: {
    sections: [
      { title: "Recent"; items: RecentConversation[] },
      { title: "Messages"; items: MessageResult[] },
      { title: "Files"; items: FileResult[] }
    ]
    highlighting: SearchTermHighlight
    keyboardNavigation: ArrowKeys
  }
}
```

## 📱 Mobile Optimizations

### Mobile Chat Layout

```typescript
interface MobileLayout {
  navigation: {
    type: "bottom_tabs" // Like WhatsApp
    tabs: ["Chats", "AI Team", "Settings"]
  }

  chatInterface: {
    header: {
      backButton: true
      conversationTitle: true
      participants: AvatarStack
      actions: [Call, VideoCall, Info]
    }

    messageArea: {
      pullToRefresh: true
      infiniteScroll: true
      touchOptimized: true
    }

    input: {
      autoExpand: true
      voiceButton: true
      attachButton: true
      sendButton: true
    }
  }

  gestures: {
    swipeLeft: "back_to_conversation_list"
    swipeRight: "open_sidebar"
    longPress: "select_message"
    doubleTap: "quick_react"
  }
}
```

## 🎨 Design System

### Color Palette (Slack-inspired)

```css
:root {
  /* Primary colors */
  --primary-blue: #1264a3;
  --primary-pink: #e01e5a;

  /* Status colors */
  --online-green: #2eb67d;
  --away-yellow: #ecb22e;
  --busy-red: #e01e5a;
  --offline-gray: #868686;

  /* Background colors */
  --bg-primary: #ffffff;
  --bg-secondary: #f8f9fa;
  --bg-tertiary: #e1e1e1;
  --bg-hover: #f4f4f4;

  /* Text colors */
  --text-primary: #1d1c1d;
  --text-secondary: #868686;
  --text-inverse: #ffffff;
}
```

### Typography Scale

```css
.chat-typography {
  --message-text: 14px/1.46 "Lato", sans-serif;
  --username: 15px/1.33 "Lato", sans-serif;
  --timestamp: 12px/1.33 "Lato", sans-serif;
  --input-text: 14px/1.46 "Lato", sans-serif;
  --sidebar-text: 14px/1.28 "Lato", sans-serif;
}
```

## 🔄 Animation Guidelines

### Micro-interactions

```css
.chat-animations {
  /* Message appearance */
  .message-enter {
    animation: slideUp 200ms ease-out;
  }

  /* Typing indicator */
  .typing-dots {
    animation: bounce 1.4s infinite;
  }

  /* Hover states */
  .message-hover-actions {
    animation: fadeIn 150ms ease-out;
  }

  /* Sidebar toggle */
  .sidebar-toggle {
    transition: transform 250ms ease-out;
  }

  /* Message reactions */
  .reaction-pop {
    animation: pop 300ms cubic-bezier(0.68, -0.55, 0.265, 1.55);
  }
}
```

## 📋 Implementation Checklist

### Phase 1: Core Chat UI

- [ ] Left sidebar with collapsible sections
- [ ] Message bubbles with proper alignment
- [ ] Rich text input with @mentions
- [ ] Typing indicators and presence status
- [ ] Basic emoji reactions

### Phase 2: Advanced Chat Features

- [ ] Message threading and replies
- [ ] Global search with Ctrl+K
- [ ] File attachments and drag-drop
- [ ] Notification badges and unread management
- [ ] Mobile-responsive layout

### Phase 3: Real-time Enhancements

- [ ] Live message streaming
- [ ] Connection status indicators
- [ ] Voice messages (future)
- [ ] Advanced search filters
- [ ] Custom emoji and reactions

---

This chat application design guide ensures the Collaborate AI Platform feels familiar and intuitive to users who are already comfortable with Slack, Teams, or other modern chat applications, while adding the unique real-time AI collaboration features that make it special.
