const edgeType = "smoothstep";

import yaml from "js-yaml";
import { v4 as uuid } from "uuid";
import fs from "vite-plugin-fs/browser";

// Read YAML content from a file
const yamlContent = await fs.readFile("math_pipeline.yaml");
console.log(yamlContent);

const parsePipeline = (yamlContent) => {
  const config = yaml.load(yamlContent);
  const nodesMap = new Map();
  const verticalSpacing = 150;
  const horizontalSpacing = 100;

  // Create nodes
  const initialNodes = config.nodes.map((node, index) => {
    const id = node.type || uuid();
    const type =
      node.type === "input"
        ? "input"
        : node.type === "output"
        ? "output"
        : "default";

    nodesMap.set(id, {
      ...node,
      connections: [],
    });

    return {
      id,
      type,
      position: {
        x: index * horizontalSpacing,
        y: index % 2 === 0 ? 0 : verticalSpacing,
      },
      data: {
        label: `${node.type} (${node.params})`,
        // params: node.params,
      },
    };
  });

  // Create edges
  const initialEdges = [];
  config.nodes.forEach((node) => {
    node.outputs?.forEach((outputChannel, outputIndex) => {
      config.nodes.forEach((targetNode) => {
        if (targetNode.inputs?.includes(outputChannel)) {
          initialEdges.push({
            id: `e${node.type}-${targetNode.type}-${outputIndex}`,
            source: node.type,
            target: targetNode.type,
            animated: true,
            label: outputChannel,
          });
        }
      });
    });
  });

  return { initialNodes, initialEdges };
};

// Usage
export const { initialNodes, initialEdges } = parsePipeline(yamlContent);
