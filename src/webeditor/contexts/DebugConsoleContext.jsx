import React, { createContext, useContext, useState, useCallback } from "react";

const DebugConsoleContext = createContext();

export const DebugConsoleProvider = ({ children }) => {
  const [messages, setMessages] = useState([]);
  const maxMessages = 500; // Prevent memory issues

  const addMessage = useCallback((message, type = "log") => {
    const timestamp = new Date().toLocaleTimeString();
    setMessages((prev) => [
      ...prev.slice(-maxMessages + 1), // Keep only recent messages
      { content: message, type, timestamp },
    ]);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return (
    <DebugConsoleContext.Provider
      value={{ messages, addMessage, clearMessages }}
    >
      {children}
    </DebugConsoleContext.Provider>
  );
};

export const useDebugConsole = () => {
  const context = useContext(DebugConsoleContext);
  if (!context) {
    throw new Error(
      "useDebugConsole must be used within a DebugConsoleProvider"
    );
  }
  return context;
};

export default DebugConsoleContext;
