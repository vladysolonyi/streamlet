import React, { useEffect, useState } from "react";
import { useServerStatus } from "../../contexts/ServerStatusContext";

const ServerStatusIndicator = () => {
  const { serverOnline, loading } = useServerStatus();
  const [connectionTime, setConnectionTime] = useState(null);

  useEffect(() => {
    if (serverOnline) {
      setConnectionTime(new Date());
    } else {
      setConnectionTime(null);
    }
  }, [serverOnline]);

  if (loading) {
    return (
      <div className="server-status">
        <div className="status-dot loading"></div>
        <span className="status-text">Checking server...</span>
      </div>
    );
  }

  return (
    <div className="server-status">
      <div
        className={`status-dot ${serverOnline ? "online" : "offline"}`}
      ></div>
      <div className="status-content">
        <span className="status-text">
          {serverOnline ? "Server online" : "Server offline"}
        </span>
        <span className="connection-time">
          {serverOnline && connectionTime
            ? `Connected at ${connectionTime.toLocaleTimeString()}`
            : "-------------"}
        </span>
      </div>
    </div>
  );
};

export default ServerStatusIndicator;
