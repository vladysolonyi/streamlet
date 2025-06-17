import React, { useState } from "react";
import { ReactFlowProvider } from "@xyflow/react";
import { TelemetryProvider } from "./contexts/TelemetryContext";
import { DnDProvider } from "./contexts/DnDContext";
import Sidebar from "./sidebar/Sidebar";
import FlowBoard from "./features/flow-board/components/FlowBoard";
import PipelineControls from "./features/pipeline-controls/PipelineControls";
import PropertiesPanel from "./features/properties-panel/PropertiesPanel"; // New component
import "./assets/index.css";
import "./assets/xy-theme.css";
import "./assets/reset.css";

const App = () => {
  const [pipelineConfig, setPipelineConfig] = useState(null);

  return (
    <ReactFlowProvider>
      <TelemetryProvider>
        <DnDProvider>
          <div className="dndflow">
            <Sidebar />
            <PropertiesPanel />
            <FlowBoard onConfigChange={setPipelineConfig} />
            {pipelineConfig && <PipelineControls config={pipelineConfig} />}
          </div>
        </DnDProvider>
      </TelemetryProvider>
    </ReactFlowProvider>
  );
};

export default App;
