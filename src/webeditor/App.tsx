import React, { useState } from "react";
import { ReactFlowProvider } from "@xyflow/react";
import { TelemetryProvider } from "./contexts/TelemetryContext";
import { DnDProvider } from "./contexts/DnDContext";
import { PipelineProvider } from "./contexts/PipelineContext";
import Sidebar from "./sidebar/Sidebar";
import FlowBoard from "./features/flow-board/components/FlowBoard";
import PipelineControls from "./features/pipeline-controls/PipelineControls";

import PropertiesPanel from "./features/properties-panel/PropertiesPanel"; // New component
import { DebugConsoleProvider } from "./contexts/DebugConsoleContext";

import ServerStatusIndicator from "./features/pipeline-controls/ServerStatusIndicator";
import { ServerStatusProvider } from "./contexts/ServerStatusContext";

import "./assets/index.css";
import DebugConsole from "./features/debug-console/DebugConsole";

const App = () => {
  const [pipelineConfig, setPipelineConfig] = useState(null);

  return (
    <ReactFlowProvider>
      <TelemetryProvider>
        <DnDProvider>
          <PipelineProvider>
            <DebugConsoleProvider>
              <ServerStatusProvider>
                <div className="dndflow">
                  <Sidebar />

                  <PropertiesPanel />

                  <FlowBoard onConfigChange={setPipelineConfig} />
                  <div className="controls">
                    <ServerStatusIndicator />
                    {pipelineConfig && (
                      <PipelineControls config={pipelineConfig} />
                    )}
                    <DebugConsole />
                  </div>
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
