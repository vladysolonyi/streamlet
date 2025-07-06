import React, { useState, useRef, useCallback } from "react";
import { useReactFlow } from "@xyflow/react";
import { parseConfig, composeConfig } from "../flow-board/utils/configUtils";
import { Icon, Icons } from "../../assets/icons";
import { useDnD } from "../../contexts/DnDContext";

const AUTOSAVE_KEY = "pipeline_autosave";
const IMPORTED_KEY = "importedConfigs";

const ConfigPanel = ({ onConfigChange, onConfigNameChange }) => {
  const { setNodes, setEdges, getNodes, getEdges } = useReactFlow();
  const { nodeTypes } = useDnD();
  const fileInputRef = useRef(null);
  const [isLoading, setIsLoading] = useState(false);

  const [importedConfigs, setImportedConfigs] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(IMPORTED_KEY)) || {};
    } catch {
      return {};
    }
  });

  const updateImported = useCallback((next) => {
    setImportedConfigs(next);
    localStorage.setItem(IMPORTED_KEY, JSON.stringify(next));
  }, []);

  const applyConfig = useCallback(
    (cfgObj, name) => {
      if (!nodeTypes || Object.keys(nodeTypes).length === 0) {
        console.error("Node types not loaded yet");
        return;
      }
      
      const { initialNodes, initialEdges } = parseConfig(cfgObj, nodeTypes);
      setNodes(initialNodes);
      setEdges(initialEdges);
      localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(cfgObj));
      onConfigChange(cfgObj);
      onConfigNameChange(name);
    },
    [nodeTypes, onConfigChange, onConfigNameChange, setNodes, setEdges]
  );

  // --- Button handlers ---

  const handleNew = () => {
    if (
      window.confirm(
        "Create new config? This will clear the board and remove autosaved data."
      )
    ) {
      setNodes([]);
      setEdges([]);
      localStorage.removeItem(AUTOSAVE_KEY);
      onConfigChange(null);
      onConfigNameChange("Untitled Config");
    }
  };

  const handleExport = () => {
    const cfg = composeConfig(getNodes(), getEdges());
    const dataUri = `data:application/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(cfg, null, 2)
    )}`;
    const name = `pipeline_config_${new Date()
      .toISOString()
      .slice(0, 10)}.json`;
    const link = document.createElement("a");
    link.href = dataUri;
    link.download = name;
    link.click();
  };

  const handleImportClick = () => fileInputRef.current?.click();

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setIsLoading(true);
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target.result);
        const defaultName = file.name.replace(/\.json$/, "");
        const name = window.prompt("Name this imported config:", defaultName);
        
        if (name) {
          const next = { ...importedConfigs, [name]: parsed };
          updateImported(next);
          applyConfig(parsed, name);
        }
      } catch (err) {
        alert(`Import error: ${err.message}`);
      } finally {
        setIsLoading(false);
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };
 

  const handleSave = () => {
    const name = window.prompt("Save current config as:", "");
    if (!name) return;
    const cfg = composeConfig(getNodes(), getEdges());
    const next = { ...importedConfigs, [name]: cfg };
    updateImported(next);
    onConfigNameChange(name);
  };

  const handleLoad = (name) => {
    const cfg = importedConfigs[name];
    if (!cfg) return;
    applyConfig(cfg, name);
  };

  const handleDelete = (name) => {
    if (!window.confirm(`Delete saved config "${name}"?`)) return;
    const next = { ...importedConfigs };
    delete next[name];
    updateImported(next);
  };

  return (
    <div className="config-panel__container">
      {/* Top buttons */}
      <div className="config-panel__actions">
        <button onClick={handleNew} className="pipeline-button">
          <Icon icon={Icons.file} />
          New
        </button>
        <button onClick={handleImportClick} className="pipeline-button">
          <Icon icon={Icons.pass} />
          Import
        </button>
        <button onClick={handleExport} className="pipeline-button">
          <Icon icon={Icons.exp} />
          Export
        </button>
        <button onClick={handleSave} className="pipeline-button">
          <Icon icon={Icons.save} />
          Save
        </button>
      </div>

      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        className="config-panel__input"
        accept=".json"
        onChange={handleFileChange}
      />

      {/* Saved list */}
      {Object.keys(importedConfigs).length > 0 && (
        <div className="config-panel__saved">
          <ul className="config-panel__list">
            {Object.entries(importedConfigs).map(([name]) => (
              <li key={name} className="config-panel__saved-item">
                <span className="config-panel__name">{name}</span>
                <button
                  onClick={() => handleLoad(name)}
                  className="config-panel__small-btn"
                  title="Load"
                >
                  <Icon icon={Icons.start} />
                </button>
                <button
                  onClick={() => {
                    const newName = window.prompt("Overwrite config as:", name);
                    if (newName) {
                      const cfg = composeConfig(getNodes(), getEdges());
                      const next = { ...importedConfigs, [newName]: cfg };
                      updateImported(next);
                      onConfigNameChange(newName);
                    }
                  }}
                  className="config-panel__small-btn"
                  title="Overwrite"
                >
                  <Icon icon={Icons.save} />
                </button>
                <button
                  onClick={() => handleDelete(name)}
                  className="config-panel__small-btn"
                  title="Delete"
                >
                  <Icon icon={Icons.del} />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default ConfigPanel;
