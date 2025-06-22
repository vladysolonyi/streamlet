import React, { useState } from "react";
import { useNodes, useReactFlow, useEdges } from "@xyflow/react";

const PropertiesPanel = () => {
  const { setNodes } = useReactFlow();
  const nodes = useNodes();
  const edges = useEdges();
  const selectedNode = nodes.find((node) => node.selected);
  const [isEditingName, setIsEditingName] = useState(false);
  const [tempName, setTempName] = useState("");

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

  // Function to handle node renaming
  const handleRenameNode = () => {
    if (tempName.trim() === "") return;

    setNodes((nodes) =>
      nodes.map((node) => {
        if (node.id === selectedNode.id) {
          return {
            ...node,
            data: {
              ...node.data,
              label: tempName,
            },
          };
        }
        return node;
      })
    );

    setIsEditingName(false);
  };

  const handleChange = (prop, value) => {
    setNodes((nodes) =>
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

    const currentValue = data.params[prop] ?? definition?.default;

    const inputProps = {
      value: currentValue,
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
              checked={currentValue}
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

  const referencingEdges = edges.filter(
    (edge) => edge.source === selectedNode.id && edge.type === "straight"
  );

  // Find references from this node
  const referencedEdges = edges.filter(
    (edge) => edge.target === selectedNode.id && edge.type === "straight"
  );

  return (
    <div className="properties-panel">
      <div className="panel-header">
        {isEditingName ? (
          <div className="name-editor">
            <input
              type="text"
              value={tempName}
              onChange={(e) => setTempName(e.target.value)}
              className="node-name-input"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") handleRenameNode();
                if (e.key === "Escape") setIsEditingName(false);
              }}
              onBlur={handleRenameNode}
            />
            <div className="name-editor-buttons">
              <button className="confirm-rename" onClick={handleRenameNode}>
                ✓
              </button>
              <button
                className="cancel-rename"
                onClick={() => setIsEditingName(false)}
              >
                ✕
              </button>
            </div>
          </div>
        ) : (
          <div
            className="node-name-display"
            onClick={() => {
              setTempName(data.label);
              setIsEditingName(true);
            }}
          >
            <h3>{data.label}</h3>
            <span className="edit-icon">✏️</span>
          </div>
        )}
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
      <div className="references-section">
        <h4>References</h4>

        {referencingEdges.length > 0 && (
          <div className="references-group">
            <h5>Referencing:</h5>
            {referencingEdges.map((edge) => (
              <div key={edge.id} className="reference-item">
                <span className="reference-node">{edge.target}</span>
                <span className="reference-path">
                  {edge.data?.referencePath}
                </span>
              </div>
            ))}
          </div>
        )}

        {referencedEdges.length > 0 && (
          <div className="references-group">
            <h5>Referenced by:</h5>
            {referencedEdges.map((edge) => (
              <div key={edge.id} className="reference-item">
                <span className="reference-node">{edge.source}</span>
                <span className="reference-path">
                  {edge.data?.referencePath}
                </span>
              </div>
            ))}
          </div>
        )}

        {referencingEdges.length === 0 && referencedEdges.length === 0 && (
          <div className="no-references">No references</div>
        )}
      </div>
    </div>
  );
};

export default PropertiesPanel;
