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

interface TokenFormProps {
  onTokenSubmit: (token: string) => void;
}

const TokenForm: React.FC<TokenFormProps> = ({ onTokenSubmit }) => {
  const [token, setToken] = useState('');
  const [email, setEmail] = useState('');
  const [isRequesting, setIsRequesting] = useState(false);
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [displayToken, setDisplayToken] = useState('');
  const [displayMessage, setDisplayMessage] = useState('');

  const handleRequestToken = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage('');
    setIsRequesting(true);
    
    try {
      const response = await axios.post('/api/request-token', { email });
      const data = response.data;
      
      // Check if token is directly returned (no email configuration)
      if (data.display_token && data.token) {
        setDisplayToken(data.token);
        setDisplayMessage(data.message || '令牌已生成。请保存此令牌，它不会通过电子邮件发送。');
        
        // Automatically use this token
        onTokenSubmit(data.token.toUpperCase());
      } else {
        // Normal flow - token sent by email
        setShowTokenInput(true);
      }
    } catch (error) {
      setErrorMessage('请求令牌时出错。请稍后重试。');
    } finally {
      setIsRequesting(false);
    }
  };

  const handleTokenSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (token.trim()) {
      onTokenSubmit(token.trim().toUpperCase());
    }
  };

  if (displayToken) {
    return (
      <div className="token-form">
        <h2>您的访问令牌</h2>
        <p>{displayMessage}</p>
        
        <div className="token-display">
          <div className="token">{displayToken}</div>
          <p className="token-warning">请立即复制并保存此令牌，关闭此页面后将无法再次查看！</p>
        </div>
        
        <button onClick={() => onTokenSubmit(displayToken)}>
          继续访问
        </button>
      </div>
    );
  }

  return (
    <div className="token-form">
      {!showTokenInput ? (
        <form onSubmit={handleRequestToken}>
          <h2>请求访问令牌</h2>
          <p>请输入您的电子邮件地址以获取访问令牌。</p>
          
          <div className="form-group">
            <label htmlFor="email">电子邮件地址</label>
            <input 
              type="email" 
              id="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="请输入您的电子邮件" 
              required
            />
          </div>
          
          {errorMessage && <div className="error-message">{errorMessage}</div>}
          
          <button type="submit" disabled={isRequesting}>
            {isRequesting ? '处理中...' : '请求令牌'}
          </button>
        </form>
      ) : (
        <form onSubmit={handleTokenSubmit}>
          <h2>输入访问令牌</h2>
          <p>请检查您的电子邮件 ({email}) 获取您的访问令牌。</p>
          
          <div className="form-group">
            <label htmlFor="token">访问令牌</label>
            <input 
              type="text" 
              id="token" 
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="输入6位令牌" 
              maxLength={6}
              required
            />
          </div>
          
          <button type="submit">提交</button>
        </form>
      )}
    </div>
  );
};

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [token, setToken] = useState<string | null>(null);
  const [tokenError, setTokenError] = useState<boolean>(false);
  
  // Check for token in localStorage on component mount
  useEffect(() => {
    const savedToken = localStorage.getItem('wine_ai_token');
    if (savedToken) {
      setToken(savedToken);
    }
  }, []);
  
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
  
  const handleTokenSubmit = (newToken: string) => {
    setToken(newToken);
    localStorage.setItem('wine_ai_token', newToken);
    setTokenError(false);
  };
  
  const handleSendMessage = async (text: string) => {
    if (!text.trim() || !token) return;
    
    // Add user message
    addMessage(text, 'user');
    setIsLoading(true);
    
    try {
      // Send request to server with token
      const response = await axios.post('/api/query', 
        { query: text },
        { 
          headers: { 'X-API-Token': token },
          validateStatus: (status) => status < 500 // Don't throw on 401
        }
      );
      
      // Handle 401 Unauthorized (invalid token)
      if (response.status === 401) {
        setTokenError(true);
        addMessage('您的访问令牌已过期或无效。请获取新令牌。', 'ai');
        return;
      }
      
      // Add AI response
      addMessage(response.data.answer, 'ai');
    } catch (error) {
      console.error('Error querying the Wine AI:', error);
      addMessage('很抱歉，在处理您的问题时遇到了错误。请重试。', 'ai');
    } finally {
      setIsLoading(false);
    }
  };
  
  // If no token or token error, show token form
  if (!token || tokenError) {
    return <TokenForm onTokenSubmit={handleTokenSubmit} />;
  }
  
  return (
    <div className="chat-interface">
      <MessageList messages={messages} isLoading={isLoading} />
      <MessageInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
};

export default ChatInterface; 