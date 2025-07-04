import React, { useEffect, useState } from "react";
import { Icon, Icons } from "../../assets/icons";
import { useTelemetry } from "../../contexts/TelemetryContext";
import { webSocketService } from "../../services/websocket";
import { usePipeline } from "../../contexts/PipelineContext";
import { useDebugConsole } from "../../contexts/DebugConsoleContext"; // Add this import
import { useServerStatus } from "../../contexts/ServerStatusContext";

const API_KEY = "SECRET_KEY";

const PipelineControls = ({ config }) => {
  // Get all state and setters from context
  const {
    pipelineId,
    setPipelineId,
    pipelineStatus,
    setPipelineStatus,
    hasChanges,
    setHasChanges,
    autoUpdate,
    setAutoUpdate,
    lastAppliedConfig,
    setLastAppliedConfig,
    error,
    setError,
  } = usePipeline();
  const [fpsLimit, setFpsLimit] = useState(60);
  const { serverOnline } = useServerStatus();
  const { updateTelemetry } = useTelemetry();
  const { addMessage } = useDebugConsole(); // Add this hook

  // Track config changes for hot-reload
  useEffect(() => {
    if (pipelineStatus === "running" && lastAppliedConfig) {
      const configChanged =
        JSON.stringify(config) !== JSON.stringify(lastAppliedConfig);
      setHasChanges(configChanged);

      if (autoUpdate && configChanged) {
        handleApplyUpdate();
      }
    }
  }, [config, pipelineStatus, lastAppliedConfig, autoUpdate]);

  // Get saved FPS limit
  useEffect(() => {
    const savedFps = localStorage.getItem("fps_limit");
    if (savedFps) {
      try {
        setFpsLimit(parseInt(savedFps));
      } catch {
        setFpsLimit(60);
      }
    }
  }, []);

  // Connect to pipeline telemetry
  useEffect(() => {
    if (!pipelineId) return;

    webSocketService.connect(pipelineId);

    // Log connection status
    addMessage(`Connecting to pipeline telemetry: ${pipelineId}`, "info");

    const removeListener = webSocketService.addListener((data) => {
      // Handle connection acknowledgement messages
      if (data.type === "connection_ack") {
        const timeStr = new Date(data.server_time * 1000).toISOString();
        addMessage(`Connected to server at ${timeStr}`, "success");
        return;
      }

      // Handle other non-telemetry system messages
      if (!data.metric) {
        addMessage(JSON.stringify(data), "info");
        return;
      }

      // Existing telemetry handling remains the same
      const metricMessage = `${data.node_id}: ${data.metric} ${
        data.value ? `(${data.value})` : ""
      }`;
      addMessage(metricMessage, "log");

      switch (data.metric) {
        case "processing_start":
          updateTelemetry(data.node_id, "processing_start");
          break;
        case "processing_end":
          updateTelemetry(data.node_id, "processing_end");
          break;
        case "processing_error":
          updateTelemetry(data.node_id, "processing_error", {
            message: data.value || "Error occurred",
          });
          break;
        case "execution_time":
          updateTelemetry(data.node_id, "execution_time", {
            message: data.value || "Error occurred",
          });
          break;
        case "fps":
          updateTelemetry(data.node_id, "fps", {
            count: data.value || 1,
          });
          break;
        case "data_rejected":
          updateTelemetry(data.node_id, "data_rejected", {
            count: data.value || 1,
          });
          break;
        default:
          // Log unhandled metrics
          addMessage(
            `[${data.node_id || "system"}] Unhandled metric: ${data.metric}`,
            "debug"
          );
      }
    });

    return () => {
      removeListener();
      webSocketService.disconnect();
      addMessage("Disconnected from telemetry", "info");
    };
  }, [pipelineId, updateTelemetry, addMessage]);

  const handleInitialize = async () => {
    try {
      // Create full config with settings
      const fullConfig = {
        settings: {
          fps_limit: parseInt(localStorage.getItem("fps_limit") || 60),
        },
        nodes: config.nodes || [],
      };

      const pipelineConfig = {
        config: fullConfig,
        name: "Web Pipeline",
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
        const errorMsg = data.detail || "Failed to initialize pipeline";
        addMessage(`Initialize error: ${errorMsg}`, "error");
        throw new Error(errorMsg);
      }

      addMessage(
        `Pipeline initialized successfully. ID: ${data.pipeline_id}`,
        "success"
      );
      console.log("Pipeline initialized successfully:", data);
      setPipelineId(data.pipeline_id);
      setPipelineStatus("created");
      setLastAppliedConfig(config);
      setError(null); // Clear any previous errors
    } catch (err) {
      console.error("Initialize error:", err);
      setError(err.message);
      setPipelineStatus("error");
      addMessage(`Initialize failed: ${err.message}`, "error");
    }
  };

  const handleStart = async () => {
    if (!pipelineId) return;

    try {
      addMessage(`Starting pipeline: ${pipelineId}`, "info");

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
      addMessage("Pipeline started successfully", "success");
      setPipelineStatus("running");
      setLastAppliedConfig(config);
      setError(null); // Clear any previous errors
      console.log("Pipeline started successfully", response);
    } catch (err) {
      console.error("Start error:", err);
      setError(err.message);
      addMessage(`Start failed: ${err.message}`, "error");
    }
  };

  const handleStop = async () => {
    if (!pipelineId) {
      console.error("No pipelineId to stop");
      addMessage("Stop failed: No pipeline ID", "error");
      return;
    }

    try {
      addMessage(`Stopping pipeline: ${pipelineId}`, "info");

      const response = await fetch(
        `http://localhost:8000/pipelines/${pipelineId}/stop`,
        {
          method: "POST",
          headers: {
            "X-API-Key": API_KEY,
          },
        }
      );

      const result = await response.json();

      if (!response.ok) {
        const errorMsg = result.detail || "Failed to stop pipeline";
        addMessage(`Stop error: ${errorMsg}`, "error");
        throw new Error(errorMsg);
      }

      setPipelineStatus("stopped");
      setError(null);
      addMessage("Pipeline stopped successfully", "success");
      console.log("Pipeline stopped successfully", result);

      // Add a small delay before deleting to ensure complete shutdown
      setTimeout(() => {
        handleDeletePipeline();
      }, 500);
    } catch (err) {
      console.error("Stop error:", err);
      setError(err.message);
      addMessage(`Stop failed: ${err.message}`, "error");
    }
  };

  const handleDeletePipeline = async () => {
    if (!pipelineId) return;

    try {
      addMessage(`Deleting pipeline: ${pipelineId}`, "info");

      const response = await fetch(
        `http://localhost:8000/pipelines/${pipelineId}`,
        {
          method: "DELETE",
          headers: {
            "X-API-Key": API_KEY,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        const errorMsg = errorData.detail || "Failed to delete pipeline";
        addMessage(`Delete error: ${errorMsg}`, "error");
        throw new Error(errorMsg);
      }

      addMessage("Pipeline deleted successfully", "success");
      console.log("Pipeline deleted successfully");
      setPipelineId(null);
      setPipelineStatus("not created");
    } catch (err) {
      console.error("Delete error:", err);
      setError(err.message);
      addMessage(`Delete failed: ${err.message}`, "error");
    }
  };

  const handleApplyUpdate = async () => {
    if (!pipelineId || pipelineStatus !== "running") return;

    try {
      // Create full config with settings
      const updatePayload = {
        config: {
          settings: {
            fps_limit: parseInt(localStorage.getItem("fps_limit") || 60),
          },
          nodes: config.nodes || [],
        },
        name: "Updated Pipeline",
      };

      console.log("Sending update:", JSON.stringify(updatePayload));

      const response = await fetch(
        `http://localhost:8000/pipelines/${pipelineId}/config`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
          },
          body: JSON.stringify(updatePayload),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        const errorMsg = errorData.detail || "Failed to update pipeline config";
        addMessage(`Update error: ${errorMsg}`, "error");
        throw new Error(errorMsg);
      }

      addMessage("Configuration updated successfully", "success");
      console.log("Pipeline config updated successfully");
      setLastAppliedConfig(config);
      setHasChanges(false);
      setError(null);
    } catch (err) {
      console.error("Update error:", err);
      setError(err.message);
      addMessage(`Update failed: ${err.message}`, "error");
    }
  };

  const toggleAutoUpdate = () => {
    const newAutoUpdate = !autoUpdate;
    setAutoUpdate(newAutoUpdate);

    addMessage(
      newAutoUpdate ? "Auto-update enabled" : "Auto-update disabled",
      "info"
    );

    // Apply immediately when enabling auto-update if changes exist
    if (newAutoUpdate && hasChanges) {
      handleApplyUpdate();
    }
  };

  return (
    <div
      className={`pipeline-controls--floating status-${
        pipelineStatus == "not created" ? "not-created" : pipelineStatus
      }`}
    >
      <div className="controls-row">
        <button
          onClick={handleInitialize}
          disabled={!serverOnline || pipelineStatus !== "not created"}
          title="Initialize"
        >
          <Icon icon={Icons.init} width="20" height="20" /> Initialize
        </button>
        <button
          onClick={handleStart}
          disabled={
            !serverOnline || !pipelineId || pipelineStatus === "running"
          }
          title="Start"
        >
          <Icon icon={Icons.start} width="20" height="20" /> Start
        </button>
        <button
          onClick={handleStop}
          disabled={
            !serverOnline || !pipelineId || pipelineStatus !== "running"
          }
          title="Stop"
        >
          <Icon icon={Icons.stop} width="20" height="20" /> Stop
        </button>
        {pipelineStatus === "running" && hasChanges && !autoUpdate && (
          <button
            onClick={handleApplyUpdate}
            className="apply-button"
            title="Apply Changes"
          >
            <Icon icon={Icons.rerun} width="20" height="20" /> Apply
          </button>
        )}
      </div>

      <div className="status-row">
        <span>
          Status: <strong>{pipelineStatus}</strong>
        </span>
        {pipelineStatus === "running" && (
          <label>
            <input
              type="checkbox"
              checked={autoUpdate}
              onChange={toggleAutoUpdate}
            />{" "}
            Auto‑update
          </label>
        )}
      </div>

      {!serverOnline && <div className="server-warning">⚠️ Server offline</div>}
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default PipelineControls;
