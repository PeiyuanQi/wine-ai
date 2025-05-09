import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import './ChatInterface.css';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  timestamp: Date;
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  
  const generateMessageId = () => Math.random().toString(36).substring(2, 11);
  
  const addMessage = (text: string, sender: 'user' | 'ai') => {
    const newMessage: Message = {
      id: generateMessageId(),
      text,
      sender,
      timestamp: new Date()
    };
    
    setMessages(prevMessages => [...prevMessages, newMessage]);
  };
  
  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;
    
    // Add user message
    addMessage(text, 'user');
    setIsLoading(true);
    
    try {
      // Send request to server - corrected endpoint from /api/query to /query
      const response = await axios.post('/api/query', { query: text });
      
      // Add AI response - note the response property is 'answer' not 'response'
      addMessage(response.data.answer, 'ai');
    } catch (error) {
      console.error('Error querying the Wine AI:', error);
      addMessage('很抱歉，在处理您的问题时遇到了错误。请重试。', 'ai');
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="chat-interface">
      <MessageList messages={messages} isLoading={isLoading} />
      <MessageInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
};

export default ChatInterface; 