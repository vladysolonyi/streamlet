import React, { useEffect, useState } from "react";
import { Handle, useReactFlow } from "@xyflow/react";
import { useTelemetry } from "./TelemetryContext"; // Adjust import path as needed

const NodeConfig = ({ id, data, selected }) => {
  const { setNodes } = useReactFlow();
  const { nodeActivity } = useTelemetry();
  const [isActive, setIsActive] = useState(false);

  // Add safe navigation for schema properties
  const schema = data.paramsSchema || {};
  const properties = schema.properties || {};
  console.log(
    "Node ID:",
    id,
    "Telemetry ID:",
    nodeActivity[id] ? id : "no match"
  );
  // Handle telemetry updates
  useEffect(() => {
    if (nodeActivity[id]) {
      setIsActive(true);
      const timer = setTimeout(() => setIsActive(false), 250);
      return () => clearTimeout(timer);
    }
  }, [nodeActivity[id]]);

  const handleChange = (prop, value) => {
    setNodes((nodes) =>
      nodes.map((node) => {
        if (node.id === id) {
          return {
            ...node,
            data: {
              ...node.data,
              params: {
                ...node.data.params,
                [prop]: value,
              },
            },
          };
        }
        return node;
      })
    );
  };

  const renderInput = (prop, definition) => {
    // Add null checks for definition
    if (!definition) return null;

    const inputProps = {
      value: data.params[prop] ?? definition?.default,
      onChange: (e) => handleChange(prop, e.target.value),
      className: "node-input",
      placeholder: definition?.description || "",
    };

    switch (definition.type) {
      case "integer":
        return (
          <input
            {...inputProps}
            type="number"
            min={definition.minimum}
            max={definition.maximum}
          />
        );
      case "number":
        return (
          <input
            {...inputProps}
            type="number"
            step="0.1"
            min={definition.minimum}
            max={definition.maximum}
          />
        );
      case "boolean":
        return (
          <label>
            <input
              type="checkbox"
              checked={data.params[prop] ?? definition.default}
              onChange={(e) => handleChange(prop, e.target.checked)}
            />
            {definition.title}
          </label>
        );
      case "string":
        if (definition.enum) {
          return (
            <select {...inputProps}>
              {definition.enum.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          );
        }
        return <input {...inputProps} type="text" />;
      default:
        return <input {...inputProps} type="text" />;
    }
  };

  return (
    <div
      // ${colorClass}
      className={`
    status-border-wrapper
    ${isActive ? "active" : ""}
    ${selected ? "selected" : ""}
    green            /*   "green" | "red" | "yellow" */
  `}
    >
      <div
        className={`custom-node ${selected ? "selected" : ""}`}
        style={{ position: "relative" }}
      >
        <Handle type="target" position="top" />
        <div className="node-header">{data.label}</div>
        <div className="node-body">
          {Object.keys(properties).length > 0 ? (
            Object.entries(properties).map(([prop, definition]) => (
              <div key={prop} className="node-param">
                <label>{definition?.title || prop}</label>
                {renderInput(prop, definition)}
              </div>
            ))
          ) : (
            <div className="no-params">No parameters available</div>
          )}
        </div>
        <Handle type="source" position="bottom" />
      </div>
    </div>
  );
};

export default NodeConfig;
