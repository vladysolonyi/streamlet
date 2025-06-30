import React, { useState } from "react";
import { ReactFlowProvider } from "@xyflow/react";
import { TelemetryProvider } from "./contexts/TelemetryContext";
import { DnDProvider } from "./contexts/DnDContext";
import { PipelineProvider } from "./contexts/PipelineContext";
import NodeCatalog from "./features/node-catalog/NodeCatalog";
import FlowBoard from "./features/flow-board/components/FlowBoard";
import PipelineControls from "./features/pipeline-controls/PipelineControls";
import PropertiesPanel from "./features/properties-panel/PropertiesPanel";
import DebugConsole from "./features/debug-console/DebugConsole";
import ServerStatusIndicator from "./features/pipeline-controls/ServerStatusIndicator";
import ConfigPanel from "./features/config-panel/ConfigPanel";
import { DebugConsoleProvider } from "./contexts/DebugConsoleContext";
import { ServerStatusProvider } from "./contexts/ServerStatusContext";
import FpsControl from "./features/pipeline-controls/FpsControl";
import FpsDisplay from "./features/pipeline-controls/FpsDisplay";
import { Icon, Icons } from "./assets/icons";

import "./assets/styles/main.scss";

const GITHUB_URL = "https://github.com/vladysolonyi/RF-Vision"; // replace with your repo

const App = () => {
  const [pipelineConfig, setPipelineConfig] = useState(null);
  const [currentConfigName, setCurrentConfigName] = useState("Untitled Config");

  return (
    <ReactFlowProvider>
      <TelemetryProvider>
        <DnDProvider>
          <PipelineProvider>
            <DebugConsoleProvider>
              <ServerStatusProvider>
                <div className="grid-layout dnd-flow">
                  <section className="panel github">
                    <div className="link">
                      <a
                        href={GITHUB_URL}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Streamlet on GitHub
                      </a>
                    </div>
                    <div className="icon">
                      <Icon icon={Icons.github} />
                    </div>
                  </section>

                  <section className="panel node-catalog">
                    <header className="panel__header">Node Catalog</header>
                    <div className="panel__body">
                      <NodeCatalog />
                    </div>
                  </section>

                  <section className="panel config-panel">
                    <header className="panel__header">Config Menu</header>
                    <div className="panel__body">
                      <ConfigPanel
                        onConfigChange={setPipelineConfig}
                        onConfigNameChange={setCurrentConfigName}
                      />
                    </div>
                  </section>

                  <section className="panel settings">
                    <header className="panel__header">Settings</header>
                    <div className="panel__body">
                      <FpsControl />
                    </div>
                  </section>

                  <section className="panel name-bar">
                    <div className="panel__body">
                      <div>{currentConfigName}</div>
                      <div>
                        <FpsDisplay />
                      </div>
                    </div>
                  </section>

                  <section className="panel flow-board">
                    <div className="panel__body">
                      <FlowBoard onConfigChange={setPipelineConfig} />
                    </div>
                  </section>

                  <section className="panel node-params">
                    <header className="panel__header">Node Properties</header>
                    <div className="panel__body">
                      <PropertiesPanel />
                    </div>
                  </section>

                  <section className="panel debug-console">
                    <div className="panel__body">
                      <DebugConsole />
                    </div>
                  </section>

                  <section className="panel status">
                    <div className="panel__body">
                      <ServerStatusIndicator />
                    </div>
                  </section>

                  <section className=" pipeline-controls">
                    {pipelineConfig && (
                      <PipelineControls config={pipelineConfig} />
                    )}
                  </section>
                </div>
              </ServerStatusProvider>
            </DebugConsoleProvider>
          </PipelineProvider>
        </DnDProvider>
      </TelemetryProvider>
    </ReactFlowProvider>
  );
};

export default App;
