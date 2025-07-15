import React, { useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { RootState } from '../../store/store';
import { setConversations, setCurrentConversation } from '../../store/slices/chatSlice';
import { setProjects } from '../../store/slices/projectsSlice';
import { formatDistanceToNow } from 'date-fns';
import {
  ChatBubbleLeftIcon,
  FolderIcon,
  PlusIcon,
  StarIcon,
} from '@heroicons/react/24/outline';
import {
  StarIcon as StarIconSolid,
} from '@heroicons/react/24/solid';

const Sidebar: React.FC = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  
  const { conversations, currentConversationId } = useSelector(
    (state: RootState) => state.chat
  );
  const { projects, selectedProjectId } = useSelector(
    (state: RootState) => state.projects
  );

  useEffect(() => {
    // Load initial data
    loadProjects();
    loadConversations();
  }, []);

  const loadProjects = async () => {
    try {
      const response = await fetch('/api/projects');
      const projects = await response.json();
      dispatch(setProjects(projects));
    } catch (error) {
      console.error('Failed to load projects:', error);
    }
  };

  const loadConversations = async () => {
    try {
      const response = await fetch('/api/conversations');
      const conversations = await response.json();
      dispatch(setConversations(conversations));
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const handleConversationClick = (conversationId: string) => {
    dispatch(setCurrentConversation(conversationId));
    navigate(`/conversation/${conversationId}`);
  };

  const recentConversations = conversations.slice(0, 10);

  return (
    <div className="flex flex-col h-full">
      {/* Workspace header */}
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">
          🤝 Collaborate AI
        </h2>
        <p className="text-sm text-gray-500">
          Multi-AI Chat Platform
        </p>
      </div>

      {/* Navigation sections */}
      <div className="flex-1 overflow-y-auto">
        {/* Quick Actions */}
        <div className="p-4 border-b border-gray-200">
          <button
            onClick={() => {
              // TODO: Implement new conversation modal
              console.log('New conversation');
            }}
            className="w-full bg-blue-500 hover:bg-blue-600 text-white px-3 py-2 rounded-md text-sm font-medium flex items-center justify-center space-x-2"
          >
            <PlusIcon className="h-4 w-4" />
            <span>New Conversation</span>
          </button>
        </div>

        {/* Starred Conversations */}
        <div className="p-4 border-b border-gray-200">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">
            ⭐ Starred
          </h3>
          <div className="space-y-1">
            <div className="text-sm text-gray-400 italic">
              No starred conversations yet
            </div>
          </div>
        </div>

        {/* Recent Conversations */}
        <div className="p-4 border-b border-gray-200">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">
            💬 Recent Chats
          </h3>
          <div className="space-y-1">
            {recentConversations.length > 0 ? (
              recentConversations.map((conversation) => (
                <button
                  key={conversation.id}
                  onClick={() => handleConversationClick(conversation.id)}
                  className={`w-full text-left p-2 rounded-md hover:bg-gray-100 transition-colors ${
                    currentConversationId === conversation.id
                      ? 'bg-blue-50 border border-blue-200'
                      : ''
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <ChatBubbleLeftIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {conversation.title}
                      </p>
                      <p className="text-xs text-gray-500">
                        {conversation.message_count} messages • {' '}
                        {formatDistanceToNow(new Date(conversation.updated_at), {
                          addSuffix: true,
                        })}
                      </p>
                    </div>
                    {conversation.message_count > 0 && (
                      <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0" />
                    )}
                  </div>
                </button>
              ))
            ) : (
              <div className="text-sm text-gray-400 italic">
                No conversations yet
              </div>
            )}
          </div>
        </div>

        {/* Projects */}
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
              📁 Projects
            </h3>
            <button
              onClick={() => navigate('/projects')}
              className="text-xs text-blue-500 hover:text-blue-600"
            >
              View all
            </button>
          </div>
          <div className="space-y-1">
            {projects.slice(0, 5).map((project) => (
              <button
                key={project.id}
                onClick={() => {
                  // TODO: Filter conversations by project
                  console.log('Select project:', project.id);
                }}
                className="w-full text-left p-2 rounded-md hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <FolderIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {project.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {project.conversation_count} conversations
                    </p>
                  </div>
                </div>
              </button>
            ))}
            
            {projects.length === 0 && (
              <div className="text-sm text-gray-400 italic">
                No projects yet
              </div>
            )}
          </div>
        </div>

        {/* AI Status */}
        <div className="p-4 border-t border-gray-200">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">
            🤖 AI Providers
          </h3>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">OpenAI</span>
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-green-500 rounded-full" />
                <span className="text-xs text-gray-500">online</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">xAI</span>
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-green-500 rounded-full" />
                <span className="text-xs text-gray-500">online</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
