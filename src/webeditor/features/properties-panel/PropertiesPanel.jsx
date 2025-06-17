import React from "react";
import { useReactFlow } from "@xyflow/react";

const PropertiesPanel = () => {
  const { getNodes } = useReactFlow();
  const selectedNode = getNodes().find((node) => node.selected);

  if (!selectedNode) {
    return (
      <div className="properties-panel">
        <div className="no-selection">Select a node to edit its properties</div>
      </div>
    );
  }

  const { data } = selectedNode;
  const schema = data.paramsSchema || {};
  const properties = schema.properties || {};

  const handleChange = (prop, value) => {
    useReactFlow().setNodes((nodes) =>
      nodes.map((node) => {
        if (node.id === selectedNode.id) {
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
    if (!definition) return null;

    const inputProps = {
      value: data.params[prop] ?? definition?.default,
      onChange: (e) => handleChange(prop, e.target.value),
      className: "property-input",
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
          <label className="property-checkbox">
            <input
              type="checkbox"
              checked={data.params[prop] ?? definition.default}
              onChange={(e) => handleChange(prop, e.target.checked)}
            />
            <span>{definition.title}</span>
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
    <div className="properties-panel">
      <div className="panel-header">
        <h3>{data.label}</h3>
        <div className="node-type">{selectedNode.type}</div>
      </div>

      <div className="panel-body">
        {Object.keys(properties).length > 0 ? (
          Object.entries(properties).map(([prop, definition]) => (
            <div key={prop} className="property-group">
              <label className="property-label">
                {definition?.title || prop}
              </label>
              <div className="property-input-container">
                {renderInput(prop, definition)}
              </div>
              {definition.description && (
                <div className="property-description">
                  {definition.description}
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="no-params">No configurable properties</div>
        )}
      </div>
    </div>
  );
};

export default PropertiesPanel;
