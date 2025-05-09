import React, { useState, KeyboardEvent, useRef } from 'react';
import './MessageInput.css';

interface MessageInputProps {
  onSendMessage: (text: string) => void;
  isLoading: boolean;
}

const MessageInput: React.FC<MessageInputProps> = ({ onSendMessage, isLoading }) => {
  const [message, setMessage] = useState('');
  const [isComposing, setIsComposing] = useState(false);

  const handleSubmit = () => {
    if (message.trim() && !isLoading) {
      onSendMessage(message);
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Don't trigger submit if we're in the middle of an IME composition
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="message-input">
      <textarea
        className="message-textarea"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        onCompositionStart={() => setIsComposing(true)}
        onCompositionEnd={() => setIsComposing(false)}
        placeholder="请输入您的葡萄酒问题..."
        disabled={isLoading}
      />
      <button 
        className="send-button"
        onClick={handleSubmit}
        disabled={isLoading || !message.trim()}
      >
        {isLoading ? '思考中...' : '发送'}
      </button>
    </div>
  );
};

export default MessageInput; 