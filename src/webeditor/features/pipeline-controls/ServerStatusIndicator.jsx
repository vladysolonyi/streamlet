import React from "react";
import { useServerStatus } from "../../contexts/ServerStatusContext";

const ServerStatusIndicator = () => {
  const { serverOnline, loading } = useServerStatus();

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
      <span className="status-text">
        {serverOnline ? "Server online" : "Server offline"}
      </span>
    </div>
  );
};

export default ServerStatusIndicator;
