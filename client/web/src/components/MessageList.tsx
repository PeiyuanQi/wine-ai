import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import remarkGfm from 'remark-gfm';
import './MessageList.css';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  timestamp: Date;
}

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
}

const ThinkingIndicator = () => (
  <div className="message ai-message">
    <div className="message-bubble thinking-bubble">
      <div className="thinking-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
  </div>
);

const MessageList: React.FC<MessageListProps> = ({ messages, isLoading }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the bottom when new messages are added or when loading
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <div className="message-list">
      {messages.length === 0 ? (
        <div className="welcome-message">
          <h2>欢迎使用葡萄酒智能助手</h2>
          <p>有关葡萄酒的任何问题，尽管问我吧！</p>
          <p>例如：</p>
          <ul>
            <li>"赤霞珠和梅洛有什么区别？"</li>
            <li>"烤牛排配什么葡萄酒最好？"</li>
            <li>"香槟的理想饮用温度是多少？"</li>
          </ul>
        </div>
      ) : (
        <>
          {messages.map(message => (
            <div 
              key={message.id} 
              className={`message ${message.sender === 'user' ? 'user-message' : 'ai-message'}`}
            >
              <div className="message-bubble">
                {message.sender === 'ai' ? (
                  <div className="markdown-content">
                    <ReactMarkdown 
                      rehypePlugins={[rehypeRaw, rehypeSanitize]}
                      remarkPlugins={[remarkGfm]}
                    >
                      {message.text}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <p>{message.text}</p>
                )}
                <span className="message-time">
                  {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          ))}
          
          {/* Show thinking indicator when waiting for response */}
          {isLoading && <ThinkingIndicator />}
        </>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList; 