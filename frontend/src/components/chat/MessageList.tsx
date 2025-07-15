import React, { useEffect, useRef } from 'react';
import { Message } from '../../store/slices/chatSlice';
import { formatDistanceToNow } from 'date-fns';

interface MessageListProps {
  messages: Message[];
  isStreaming: boolean;
}

const MessageList: React.FC<MessageListProps> = ({ messages, isStreaming }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const getAvatarColor = (participant: string) => {
    switch (participant) {
      case 'openai':
        return 'bg-green-500';
      case 'xai':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getParticipantName = (participant: string) => {
    switch (participant) {
      case 'openai':
        return 'OpenAI';
      case 'xai':
        return 'xAI';
      default:
        return 'You';
    }
  };

  const TypingIndicator = () => (
    <div className="flex space-x-1">
      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
    </div>
  );

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 chat-scroll">
      {messages.map((message, index) => {
        const isUser = message.participant === 'user';
        const isStreaming = message.streaming;

        return (
          <div
            key={message.id}
            className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-xs lg:max-w-md xl:max-w-lg ${isUser ? 'order-2' : 'order-1'}`}>
              {/* Message bubble */}
              <div
                className={`px-4 py-2 rounded-lg ${
                  isUser
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                {/* AI provider name */}
                {!isUser && (
                  <div className="flex items-center space-x-2 mb-1">
                    <div className={`w-4 h-4 rounded-full ${getAvatarColor(message.participant)} flex items-center justify-center`}>
                      <span className="text-xs text-white font-bold">
                        {message.participant === 'openai' ? 'AI' : 'X'}
                      </span>
                    </div>
                    <span className="text-xs font-semibold">
                      {getParticipantName(message.participant)}
                    </span>
                    {isStreaming && (
                      <span className="text-xs text-gray-500">(typing...)</span>
                    )}
                  </div>
                )}

                {/* Message content */}
                <div className="chat-message whitespace-pre-wrap">
                  {message.content}
                  {isStreaming && (
                    <span className="inline-block w-2 h-4 bg-current animate-pulse ml-1" />
                  )}
                </div>

                {/* Timestamp */}
                <div className={`text-xs mt-1 ${isUser ? 'text-blue-100' : 'text-gray-500'}`}>
                  {formatDistanceToNow(new Date(message.timestamp), { addSuffix: true })}
                </div>
              </div>
            </div>

            {/* Avatar */}
            {!isUser && (
              <div className={`order-1 mr-3 mt-1 ${getAvatarColor(message.participant)} w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0`}>
                <span className="text-white text-sm font-bold">
                  {message.participant === 'openai' ? 'AI' : 'X'}
                </span>
              </div>
            )}
          </div>
        );
      })}

      {/* Streaming indicator */}
      {isStreaming && (
        <div className="flex justify-start">
          <div className="flex items-center space-x-2 px-4 py-2 bg-gray-100 rounded-lg">
            <TypingIndicator />
            <span className="text-sm text-gray-600">AI is thinking...</span>
          </div>
        </div>
      )}

      {/* Scroll target */}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;
