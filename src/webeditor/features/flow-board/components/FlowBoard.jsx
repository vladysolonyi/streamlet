import React, { useRef, useCallback, useEffect, useState } from "react";
import {
  ReactFlow,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  useReactFlow,
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
import { RefEdge, DefEdge } from "./Edge";
import { useReferenceMonitor } from "../hooks/useReferenceMonitor";

const AUTOSAVE_KEY = "pipeline_autosave";
const IMPORTED_KEY = "importedConfigs";

const FlowBoard = ({ onConfigChange }) => {
  const { type, nodeTypes } = useDnD();
  const reactFlowWrapper = useRef(null);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const {
    screenToFlowPosition,
    setNodes: rfSetNodes,
    setEdges: rfSetEdges,
    getNodes,
    getEdges,
  } = useReactFlow();
  const { pipelineStatus, setHasChanges } = usePipeline();
  const [initialized, setInitialized] = useState(false);
  const nodeCount = useRef(new Map());
  const autosaveRef = useRef(null);

  const edgeTypes = {
    default: DefEdge,
    straight: RefEdge,
  };

  useReferenceMonitor(nodes, setEdges);

  // Drop‑zone state
  const [isDragOverFlow, setIsDragOverFlow] = useState(false);

  // Load initial or autosaved config ONLY after nodeTypes are available
  useEffect(() => {
    if (!nodeTypes || Object.keys(nodeTypes).length === 0) return;
    if (initialized) return;
    
    let cfg = getEmptyConfig();
    const saved = localStorage.getItem(AUTOSAVE_KEY);
    
    if (saved) {
      try {
        cfg = JSON.parse(saved);
      } catch (e) {
        console.error("Failed to parse autosave", e);
      }
    }
    
    try {
      const { initialNodes, initialEdges } = parseConfig(cfg, nodeTypes);
      setNodes(initialNodes);
      setEdges(initialEdges);
      
      // Initialize node count
      initialNodes.forEach((n) => {
        const m = n.id.match(/_(\d+)$/);
        const count = m ? +m[1] : 0;
        if (count > (nodeCount.current.get(n.type) || 0))
          nodeCount.current.set(n.type, count);
      });
      
      setInitialized(true);
    } catch (e) {
      console.error("Failed to initialize config", e);
      setInitialized(true); // Still mark as initialized to prevent blocking
    }
  }, [nodeTypes, setNodes, setEdges, initialized]);

  // Autosave - only after initialization
  useEffect(() => {
    if (!initialized) return;
    
    autosaveRef.current = setInterval(() => {
      const cfg = composeConfig(nodes, edges);
      localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(cfg));
    }, 1000);
    
    return () => {
      if (autosaveRef.current) {
        clearInterval(autosaveRef.current);
      }
    };
  }, [initialized, nodes, edges]);

  // Notify parent - only after initialization
  useEffect(() => {
    if (!initialized) return;
    onConfigChange?.(composeConfig(nodes, edges));
  }, [nodes, edges, onConfigChange, initialized]);

  // Reset pipeline change flag
  useEffect(() => {
    if (pipelineStatus !== "running") {
      setHasChanges(false);
    }
  }, [pipelineStatus, setHasChanges]);

  const getDefaultName = useCallback((t) => {
    const next = (nodeCount.current.get(t) || 0) + 1;
    nodeCount.current.set(t, next);
    return `${t}_${next}`;
  }, []);

  const onConnect = useCallback(
    (p) => setEdges((es) => addEdge(p, es)),
    [setEdges]
  );

  const onDragOver = useCallback((e) => {
    // allow drops
    e.preventDefault();
    const payload = e.dataTransfer.types.includes("text/plain");
    if (payload) setIsDragOverFlow(true);
  }, []);

  const onDragLeave = useCallback(() => {
    setIsDragOverFlow(false);
  }, []);

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      setIsDragOverFlow(false);

      // Check for a config name
      const name = e.dataTransfer.getData("text/plain");
      if (!name) return;

      // Try to load from localStorage
      let imported = {};
      try {
        imported = JSON.parse(localStorage.getItem(IMPORTED_KEY)) || {};
      } catch {}

      const cfg = imported[name];
      if (!cfg) return;

      // Parse and replace
      if (!nodeTypes || Object.keys(nodeTypes).length === 0) {
        console.error("Cannot load config - nodeTypes not available");
        return;
      }
      
      try {
        const { initialNodes, initialEdges } = parseConfig(cfg, nodeTypes);
        rfSetNodes(initialNodes);
        rfSetEdges(initialEdges);
        localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(cfg));
      } catch (e) {
        console.error("Failed to load dropped config", e);
      }
    },
    [nodeTypes, rfSetNodes, rfSetEdges]
  );

  const onDropNewNode = useCallback(
    (e) => {
      // existing node-drop logic
      e.preventDefault();
      if (!type) return;
      const pos = screenToFlowPosition({
        x: e.clientX,
        y: e.clientY,
      });
      const name = getDefaultName(type);
      
      // Get schema safely
      const schema = nodeTypes[type]?.params_schema;
      const schemaProperties = schema?.properties || {};
      
      // Create default parameters from schema
      const defaultParams = Object.fromEntries(
        Object.entries(schemaProperties)
          .filter(([_, def]) => def.default !== undefined)
          .map(([key, def]) => [key, def.default])
      );
      
      rfSetNodes((ns) =>
        ns.concat({
          id: name,
          type,
          position: pos,
          data: { 
            label: name, 
            params: defaultParams, 
            paramsSchema: schema 
          },
        })
      );
    },
    [type, nodeTypes, screenToFlowPosition, getDefaultName, rfSetNodes]
  );

  return (
    <div
      className={
        "reactflow-wrapper" + (isDragOverFlow ? " reactflow-wrapper--over" : "")
      }
      ref={reactFlowWrapper}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {!initialized ? (
        <div className="flow-loading-overlay">
          <div className="flow-loading-message">Loading pipeline configuration...</div>
        </div>
      ) : null}
      
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        // Node‑drop uses separate handler
        onDrop={onDropNewNode}
        onDragOver={(e) => {
          // prevent default so node-drop also works
          e.preventDefault();
        }}
        nodeTypes={Object.fromEntries(
          Object.keys(nodeTypes).map((t) => [t, Node])
        )}
        edgeTypes={edgeTypes}
        fitView
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