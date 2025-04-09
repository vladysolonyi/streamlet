import { v4 as uuid } from "uuid";

export const parseConfig = (config) => {
  const nodesWithIds = config.nodes.map((node) => ({
    ...node,
    id: node.id || uuid(),
    // Initialize inputs/outputs if missing
    inputs: node.inputs || [],
    outputs: node.outputs || [],
  }));

  const initialNodes = nodesWithIds.map((node, index) => ({
    id: node.id,
    type: node.type,
    position: {
      x: index * 100,
      y: index % 2 === 0 ? 0 : 150,
    },
    data: {
      label: node.type,
      params: node.params || {},
      // Store I/O channels directly from config
      outputs: node.outputs,
      inputs: node.inputs,
    },
  }));

  const initialEdges = [];
  nodesWithIds.forEach((sourceNode) => {
    sourceNode.outputs.forEach((outputChannel) => {
      nodesWithIds.forEach((targetNode) => {
        if (targetNode.inputs.includes(outputChannel)) {
          initialEdges.push({
            id: `${sourceNode.id}-${outputChannel}-${targetNode.id}`,
            source: sourceNode.id,
            target: targetNode.id,
            label: outputChannel,
            animated: true,
          });
        }
      });
    });
  });

  return { initialNodes, initialEdges };
};

export const composeConfig = (nodes, edges) => {
  // Create a map for efficient node lookups
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));

  return {
    nodes: nodes.map((node) => {
      // Get all outgoing connections (outputs)
      const outputs = edges
        .filter((edge) => edge.source === node.id)
        .map((edge) => edge.label)
        .filter((value, index, self) => self.indexOf(value) === index); // Unique values

      // Get all incoming connections (inputs)
      const inputs = edges
        .filter((edge) => edge.target === node.id)
        .map((edge) => edge.label)
        .filter((value, index, self) => self.indexOf(value) === index); // Unique values

      return {
        type: node.type,
        params: node.data.params || {},
        inputs,
        outputs,
      };
    }),
  };
};
