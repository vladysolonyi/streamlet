import React, { useRef, useCallback, useState, useEffect } from "react";
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
import "@xyflow/react/dist/style.css";

import Sidebar from "./Sidebar";
import config from "./math_pipeline.json";
import { parseConfig, composeConfig } from "./configUtils";
import PipelineControls from "./PipelineControls";
import { DnDProvider, useDnD } from "./DnDContext";

const { initialNodes, initialEdges } = parseConfig(config);

const DnDFlow = () => {
  const reactFlowWrapper = useRef(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const { screenToFlowPosition } = useReactFlow();
  const [type] = useDnD();
  const nodeCount = useRef(new Map());

  const getDefaultName = (nodeType) => {
    const count = nodeCount.current.get(nodeType) || 0;
    nodeCount.current.set(nodeType, count + 1);
    return `${nodeType}_${count + 1}`;
  };

  const getDefaultParams = (nodeType) => {
    const defaults = {
      number_generator: { current: 0, step: 1 },
      math_multiply: { multiplier: 0 },
      console_logger: {},
    };
    return defaults[nodeType] || {};
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
      const newNode = {
        id: nodeName,
        type,
        position,
        data: {
          label: nodeName,
          params: getDefaultParams(type),
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [screenToFlowPosition, type]
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
          fitView
          style={{ backgroundColor: "#F7F9FB" }}
        >
          <Controls />
          <Background />
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
    <DnDProvider>
      <DnDFlow />
    </DnDProvider>
  </ReactFlowProvider>
);
