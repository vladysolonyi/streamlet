import React, { useRef, useCallback, useEffect, useState } from "react";
import {
  ReactFlow,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  useReactFlow,
  Background,
  applyNodeChanges, // Add this import
} from "@xyflow/react";
import Node from "./Node";
import { useDnD } from "../../../contexts/DnDContext";
import { usePipeline } from "../../../contexts/PipelineContext";

import {
  parseConfig,
  composeConfig,
  getEmptyConfig,
} from "../utils/configUtils";
import "@xyflow/react/dist/base.css";
import { ReferenceEdge, DefaultEdge } from "./Edge";
import { useReferenceMonitor } from "../hooks/useReferenceMonitor";

const AUTOSAVE_KEY = "pipeline_autosave";
const NODE_TYPES_KEY = "nodeTypes";

const FlowBoard = ({ onConfigChange }) => {
  const { type, nodeTypes } = useDnD();
  const reactFlowWrapper = useRef(null);

  // Use the standard hook for nodes and edges state
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { pipelineStatus, setHasChanges } = usePipeline();
  // Define edge types
  const edgeTypes = useRef({
    default: DefaultEdge,
    straight: ReferenceEdge,
  }).current;
  useReferenceMonitor(nodes, setEdges);

  const [initialized, setInitialized] = useState(false); // Track initialization status

  const { screenToFlowPosition } = useReactFlow();
  const nodeCount = useRef(new Map());
  const fileInputRef = useRef(null);
  const autosaveIntervalRef = useRef(null);

  // Add handler for node changes including selection
  const handleNodesChange = useCallback(
    (changes) => {
      setNodes((nds) => applyNodeChanges(changes, nds));
    },
    [setNodes]
  );

  // Initialize with saved config
  useEffect(() => {
    const savedConfig = localStorage.getItem(AUTOSAVE_KEY);
    let configToLoad = getEmptyConfig();

    if (savedConfig) {
      try {
        configToLoad = JSON.parse(savedConfig);
        console.log("Loaded saved config from localStorage");
      } catch (error) {
        console.error("Error loading saved config:", error);
        configToLoad = getEmptyConfig();
      }
    }

    // Always load config even if server is offline
    const { initialNodes, initialEdges } = parseConfig(configToLoad, nodeTypes);

    setNodes(initialNodes);
    setEdges(initialEdges);

    // Update node counter
    initialNodes.forEach((node) => {
      const type = node.type;
      const match = node.id.match(/_(\d+)$/);
      const count = match ? parseInt(match[1]) : 0;
      if (count > (nodeCount.current.get(type) || 0)) {
        nodeCount.current.set(type, count);
      }
    });

    setInitialized(true);
  }, [nodeTypes]); // Only run when nodeTypes change

  // Setup autosave after initialization
  useEffect(() => {
    if (!initialized) return;

    autosaveIntervalRef.current = setInterval(() => {
      const currentConfig = composeConfig(nodes, edges);
      localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(currentConfig));
    }, 1000);

    return () => {
      if (autosaveIntervalRef.current) {
        clearInterval(autosaveIntervalRef.current);
      }
    };
  }, [nodes, edges, initialized]);

  // Add this useEffect to reset changes when pipeline stops
  useEffect(() => {
    console.log("Pipeline status changed:", pipelineStatus);
    if (pipelineStatus !== "running") {
      setHasChanges(false);
    }
  }, [pipelineStatus]);

  // Notify parent about config changes
  useEffect(() => {
    if (typeof onConfigChange === "function") {
      const currentConfig = composeConfig(nodes, edges);
      onConfigChange(currentConfig);
    }
  }, [nodes, edges, onConfigChange]);

  const getDefaultName = (nodeType) => {
    const count = (nodeCount.current.get(nodeType) || 0) + 1;
    nodeCount.current.set(nodeType, count);
    return `${nodeType}_${count}`;
  };

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    []
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      if (!type) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const nodeName = getDefaultName(type);
      const nodeSchema = nodeTypes[type]?.params_schema;
      const defaultParams = Object.fromEntries(
        Object.entries(nodeSchema?.properties || {}).map(([key, def]) => [
          key,
          def.default,
        ])
      );

      const newNode = {
        id: nodeName,
        type: type,
        position,
        data: {
          label: nodeName,
          params: defaultParams,
          paramsSchema: nodeSchema,
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [screenToFlowPosition, type, nodeTypes]
  );

  const handleNewConfig = useCallback(() => {
    if (
      window.confirm(
        "Are you sure you want to create a new config? This will clear the current board and remove autosaved data."
      )
    ) {
      setNodes([]);
      setEdges([]);
      nodeCount.current = new Map();
      localStorage.removeItem(AUTOSAVE_KEY);
    }
  }, [setNodes, setEdges]);

  const handleExportToFile = useCallback(() => {
    const currentConfig = composeConfig(nodes, edges);
    const dataStr = JSON.stringify(currentConfig, null, 2);
    const dataUri = `data:application/json;charset=utf-8,${encodeURIComponent(
      dataStr
    )}`;

    const exportFileDefaultName = `pipeline_config_${new Date()
      .toISOString()
      .slice(0, 10)}.json`;
    const linkElement = document.createElement("a");
    linkElement.setAttribute("href", dataUri);
    linkElement.setAttribute("download", exportFileDefaultName);
    linkElement.click();
  }, [nodes, edges]);

  const handleImportConfig = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (event) => {
      const file = event.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const importedConfig = JSON.parse(e.target.result);
          const { initialNodes, initialEdges } = parseConfig(
            importedConfig,
            nodeTypes
          );

          setNodes(initialNodes);
          setEdges(initialEdges);

          // Update node counter
          initialNodes.forEach((node) => {
            const type = node.type;
            const match = node.id.match(/_(\d+)$/);
            const count = match ? parseInt(match[1]) : 0;
            if (count > (nodeCount.current.get(type) || 0)) {
              nodeCount.current.set(type, count);
            }
          });

          // Save to localStorage
          localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(importedConfig));
        } catch (error) {
          console.error("Error parsing config file:", error);
          alert(`Error importing config: ${error.message}`);
        }
      };
      reader.readAsText(file);
      event.target.value = ""; // Reset input
    },
    [nodeTypes, setNodes, setEdges]
  );

  return (
    <div className="reactflow-wrapper" ref={reactFlowWrapper}>
      {/* Hidden file input for config import */}
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: "none" }}
        accept=".json"
        onChange={handleFileChange}
      />

      {/* Config management buttons */}
      <div className="config-controls">
        <button
          onClick={handleNewConfig}
          className="config-btn"
          title="Clear board and start fresh"
        >
          New
        </button>
        <button
          onClick={handleImportConfig}
          className="config-btn"
          title="Import pipeline config"
        >
          Import
        </button>
        <button
          onClick={handleExportToFile}
          className="config-btn"
          title="Export current config"
        >
          Export
        </button>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodeTypes={Object.keys(nodeTypes).reduce((acc, nodeType) => {
          acc[nodeType] = Node;
          return acc;
        }, {})}
        edgeTypes={edgeTypes} // Add this
        fitView
        style={{ backgroundColor: "#F7F9FB" }}
        nodesDraggable
        nodesConnectable
        elementsSelectable
        selectNodesOnDrag={false}
      >
        <Controls />
        <Background />
      </ReactFlow>
    </div>
  );
};

export default FlowBoard;
