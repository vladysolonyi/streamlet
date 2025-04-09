import React, { useRef, useCallback, useState, useEffect } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useNodes,
  useNodesState,
  useEdges,
  useEdgesState,
  Controls,
  useReactFlow,
  Background,
} from "@xyflow/react";

import "@xyflow/react/dist/style.css";

import Sidebar from "./Sidebar";
import config from "./math_pipeline.json"; // Direct JSON import
import { parseConfig, composeConfig } from "./configUtils";
import PipelineControls from "./PipelineControls";
const { initialNodes, initialEdges } = parseConfig(config);

export { initialNodes, initialEdges };
import { DnDProvider, useDnD } from "./DnDContext";
import { use } from "express/lib/application";

let id = 0;
const getId = () => `dndnode_${id++}`;
const DnDFlow = () => {
  const reactFlowWrapper = useRef(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const { screenToFlowPosition } = useReactFlow();
  const [type] = useDnD();
  const nodeArray = useEdges();

  useEffect(() => {
    fetch("http://localhost:8000/node-types")
      .then((response) => response.json())
      .then((data) => {
        console.log(data);
      })
      .catch((err) => {
        console.error(err);
      });
  }, []);

  const onConnect = useCallback(
    (connection) => {
      // Get the source node's details
      const sourceNode = nodes.find((n) => n.id === connection.source);
      // Use the first output channel by default (or implement channel selection UI)
      const outputChannel = sourceNode?.data.outputs?.[0] || "default";

      // Create the new edge with proper channel labeling
      const newEdge = {
        ...connection,
        id: `${connection.source}-${outputChannel}-${connection.target}`,
        label: outputChannel,
        animated: true,
      };

      setEdges((eds) => addEdge(newEdge, eds));
    },
    [nodes]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      // check if the dropped element is valid
      if (!type) {
        return;
      }

      // project was renamed to screenToFlowPosition
      // and you don't need to subtract the reactFlowBounds.left/top anymore
      // details: https://reactflow.dev/whats-new/2023-11-10
      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });
      const newNode = {
        id: getId(),
        type,
        position,
        data: { label: `${type} node` },
      };

      setNodes((nds) => nds.concat(newNode));
      console.log(nodeArray);
    },
    [screenToFlowPosition, type]
  );

  const handleExport = useCallback(() => {
    const currentConfig = composeConfig(nodes, edges);
    console.log("Exported Config:", JSON.stringify(currentConfig, null, 2));
    // Add logic to save/download the config
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
