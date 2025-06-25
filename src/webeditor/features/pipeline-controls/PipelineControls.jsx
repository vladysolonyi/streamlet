import React, { useEffect, useState } from "react";
import { useTelemetry } from "../../contexts/TelemetryContext";
import { webSocketService } from "../../services/websocket";
import { usePipeline } from "../../contexts/PipelineContext";
import { useDebugConsole } from "../../contexts/DebugConsoleContext"; // Add this import
import { useServerStatus } from "../../contexts/ServerStatusContext";
import FpsControl from "./FPSControl";

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

  // WebSocket connection for telemetry
  useEffect(() => {
    if (!pipelineId) return;

    webSocketService.connect(pipelineId);

    // Log connection status
    addMessage(`Connecting to pipeline telemetry: ${pipelineId}`, "info");

    const removeListener = webSocketService.addListener((data) => {
      // Add telemetry messages to debug console
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
        case "data_rejected":
          updateTelemetry(data.node_id, "data_rejected", {
            count: data.value || 1,
          });
          break;
        default:
          break;
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

  useEffect(() => {
    if (!pipelineId) return;

    webSocketService.connect(pipelineId);

    const handleTelemetry = (data) => {
      // Handle all telemetry messages with consistent format
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
        case "data_rejected":
          updateTelemetry(data.node_id, "data_rejected", {
            count: data.value || 1,
          });
          break;
        case "fps":
          // Handled by FpsControl
          break;
        default:
          // Log other metrics to debug console
          addMessage(
            `[${data.node_id || "system"}] ${data.metric}: ${data.value}`,
            "log"
          );
      }
    };

    const removeListener = webSocketService.addListener(handleTelemetry);

    return () => {
      removeListener();
      webSocketService.disconnect();
    };
  }, [pipelineId, updateTelemetry, addMessage]);

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
    <div className="pipeline-controls">
      {!serverOnline && (
        <div className="server-warning">
          ⚠️ Server is offline - controls disabled
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      <div className="controls-row">
        <button
          onClick={handleInitialize}
          disabled={!serverOnline || pipelineStatus !== "not created"}
        >
          Initialize
        </button>
        <button
          onClick={handleStart}
          disabled={
            !serverOnline || !pipelineId || pipelineStatus === "running"
          }
        >
          Start
        </button>
        <button
          onClick={handleStop}
          disabled={
            !serverOnline || !pipelineId || pipelineStatus !== "running"
          }
        >
          Stop
        </button>

        {pipelineStatus === "running" && hasChanges && !autoUpdate && (
          <button onClick={handleApplyUpdate} className="apply-button">
            Apply Changes
          </button>
        )}
      </div>

      <div className="status-row">
        <div className="pipeline-status">Status: {pipelineStatus}</div>

        {pipelineStatus === "running" && (
          <label className="auto-update-toggle">
            <input
              type="checkbox"
              checked={autoUpdate}
              onChange={toggleAutoUpdate}
            />
            Auto Update
          </label>
        )}
      </div>

      {pipelineStatus === "running" && hasChanges && (
        <div className="changes-indicator">
          {autoUpdate ? "Applying changes..." : "Unapplied changes!"}
        </div>
      )}
      <FpsControl />
    </div>
  );
};

export default PipelineControls;
