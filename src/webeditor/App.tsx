import React, { useRef, useCallback, useEffect } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  useReactFlow,
  Background,
} from "@xyflow/react";
//import "@xyflow/react/dist/style.css";
import "@xyflow/react/dist/base.css";

import { TelemetryProvider } from "./TelemetryContext";
import NodeConfig from "./NodeConfig";
import Sidebar from "./Sidebar";
import config from "./ai_pipeline.json";
import { parseConfig, composeConfig } from "./configUtils";
import PipelineControls from "./PipelineControls";
import { DnDProvider, useDnD } from "./DnDContext";

const { initialNodes, initialEdges } = parseConfig(config);

const DnDFlow = () => {
  const { type, nodeTypes } = useDnD();
  const reactFlowWrapper = useRef(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { screenToFlowPosition } = useReactFlow();
  const nodeCount = useRef(new Map());

  useEffect(() => {
    if (Object.keys(nodeTypes).length > 0) {
      const { initialNodes, initialEdges } = parseConfig(config, nodeTypes);
      setNodes(initialNodes);
      setEdges(initialEdges);

      // Initialize node count based on loaded nodes
      initialNodes.forEach((node) => {
        const type = node.type;
        const match = node.id.match(/_(\d+)$/);
        const count = match ? parseInt(match[1]) : 0;
        if (count > (nodeCount.current.get(type) || 0)) {
          // Fixed line
          nodeCount.current.set(type, count);
        }
      });
    }
  }, [nodeTypes, setNodes, setEdges]);

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
        type: type, // Use actual type instead of 'custom'
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

  const handleExport = useCallback(() => {
    const currentConfig = composeConfig(nodes, edges);
    console.log("Exported Config:", JSON.stringify(currentConfig, null, 2));
  }, [nodes, edges]);

  return (
    <div className="dndflow">
      <div className="reactflow-wrapper" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={
            // Dynamically create node types from available nodeTypes
            Object.keys(nodeTypes).reduce((acc, nodeType) => {
              acc[nodeType] = NodeConfig;
              return acc;
            }, {})
          }
          fitView
          style={{ backgroundColor: "#F7F9FB" }}
        >
          <Controls />
        </ReactFlow>
      </div>
      <Sidebar />
      <PipelineControls config={composeConfig(nodes, edges)} />
      <button
        onClick={handleExport}
        style={{ position: "absolute", bottom: 10, right: 10 }}
      >
        Export Config
      </button>
    </div>
  );
};

export default () => (
  <ReactFlowProvider>
    <TelemetryProvider>
      <DnDProvider>
        <DnDFlow />
      </DnDProvider>
    </TelemetryProvider>
  </ReactFlowProvider>
);
