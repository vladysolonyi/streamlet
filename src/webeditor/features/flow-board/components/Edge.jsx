import React from "react";
import { BezierEdge, StraightEdge } from "@xyflow/react";

export const ReferenceEdge = (props) => {
  return (
    <StraightEdge
      {...props}
      style={{ stroke: "rgb(0 255 171 / 50%)", strokeWidth: 2 }}
    />
  );
};

export const DefaultEdge = (props) => {
  return <BezierEdge {...props} />;
};
