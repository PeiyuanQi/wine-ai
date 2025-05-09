import React, { useState } from 'react';
import ChatInterface from './components/ChatInterface';
import './App.css';

const App: React.FC = () => {
  return (
    <div className="app">
      <header className="app-header">
        <h1>葡萄酒智能助手</h1>
      </header>
      <main className="app-content">
        <ChatInterface />
      </main>
      <footer className="app-footer">
        <p>由 Wine-AI 提供支持 - 您的个人葡萄酒知识助手</p>
      </footer>
    </div>
  );
};

export default App; 