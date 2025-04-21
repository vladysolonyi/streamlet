import React, { useState } from "react";
import { composeConfig } from "./configUtils";
const API_KEY = "SECRET_KEY"; // Should use environment variables in production

const PipelineControls = ({ config }) => {
  const [pipelineId, setPipelineId] = useState(null);
  const [pipelineStatus, setPipelineStatus] = useState("not created");
  const [error, setError] = useState(null);

  const handleInitialize = async () => {
    try {
      const pipelineConfig = {
        config: config,
        name: "Demo Pipeline",
      };

      const response = await fetch("http://localhost:8000/pipelines", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": API_KEY,
        },
        body: JSON.stringify(pipelineConfig),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to initialize pipeline");
      } else {
        console.log("Pipeline initialized successfully:", data);
      }

      setPipelineId(data.id);
      setPipelineStatus("created");
    } catch (err) {
      console.error("Initialize error:", err);
      setError(err.message);
      setPipelineStatus("error");
    }
  };

  const handleStart = async () => {
    if (!pipelineId) return;

    try {
      const response = await fetch(
        `http://localhost:8000/pipelines/${pipelineId}/start`,
        {
          method: "POST",
          headers: {
            "X-API-Key": API_KEY,
          },
        }
      );

      await response.json();
      setPipelineStatus("running");
      console.log("Pipeline started successfully", response);
    } catch (err) {
      console.error("Start error:", err);
      setError(err.message);
    }
  };

  const handleStop = async () => {
    if (!pipelineId) return;

    try {
      const response = await fetch(
        `http://localhost:8000/pipelines/${pipelineId}/stop`,
        {
          method: "POST",
          headers: {
            "X-API-Key": API_KEY,
          },
        }
      );

      await response.json();
      setPipelineStatus("stopped");
      console.log("Pipeline stopped successfully", response);
    } catch (err) {
      console.error("Stop error:", err);
      setError(err.message);
    }
  };

  return (
    <div className="pipeline-controls">
      {error && <div className="error-message">{error}</div>}
      <button
        onClick={handleInitialize}
        disabled={pipelineStatus !== "not created"}
      >
        Initialize Pipeline
      </button>
      <button
        onClick={handleStart}
        disabled={!pipelineId || pipelineStatus === "running"}
      >
        Start Pipeline
      </button>
      <button
        onClick={handleStop}
        disabled={!pipelineId || pipelineStatus !== "running"}
      >
        Stop Pipeline
      </button>
      <div className="pipeline-status">Pipeline Status: {pipelineStatus}</div>
    </div>
  );
};

export default PipelineControls;
