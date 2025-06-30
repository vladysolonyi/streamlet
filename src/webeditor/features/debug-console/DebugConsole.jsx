import React, { useRef, useEffect } from "react";
import { useDebugConsole } from "../../contexts/DebugConsoleContext";

const DebugConsole = () => {
  const { messages, clearMessages } = useDebugConsole(); // Add clearMessages here
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="debug-console">
      <div className="panel__header">
        <div className="panel__title">
          <h3>Debug Console</h3>
        </div>
        <div className="console-controls">
          <button
            className="clear-button"
            onClick={clearMessages}
            disabled={messages.length === 0}
          >
            Clear
          </button>
        </div>
      </div>
      <div className="console-output">
        {messages.map((msg, index) => (
          <div key={index} className={`console-line ${msg.type || "log"}`}>
            <span className="timestamp">[{msg.timestamp}] </span>
            {msg.pipelineId && (
              <span className="pipeline-id">
                [{msg.pipelineId.slice(0, 8)}]{" "}
              </span>
            )}
            {msg.content}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default DebugConsole;
