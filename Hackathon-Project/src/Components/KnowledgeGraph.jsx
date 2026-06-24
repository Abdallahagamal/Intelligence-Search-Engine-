import { useMemo, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { motion } from "framer-motion";

const TYPE_COLOR = {
  query:        "#fb923c",
  topic:        "#38bdf8",
  organization: "#f87171",
  person:       "#fbbf24",
  technology:   "#34d399",
  concept:      "#818cf8",
  location:     "#a78bfa",
  group:        "#f472b6",
  event:        "#fb923c",
  regulation:   "#94a3b8",
  platform:     "#475569",
  unknown:      "#64748b",
};

function GraphNode({ data }) {
  const color = TYPE_COLOR[data.nodeType] || "#64748b";
  return (
    <div
      className="px-3 py-1.5 rounded-xl text-xs font-semibold text-white shadow-lg select-none"
      style={{
        background: color + "22",
        border: `1.5px solid ${color}55`,
        color,
        backdropFilter: "blur(8px)",
        maxWidth: 140,
        textAlign: "center",
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
      }}
      title={data.label}
    >
      {data.label}
    </div>
  );
}

const nodeTypes = { custom: GraphNode };

export default function KnowledgeGraph({ graph, onNodeClick }) {
  const rawNodes = graph?.nodes || [];
  const rawEdges = graph?.edges || [];

  const [nodes, , onNodesChange] = useNodesState(
    rawNodes.map((n) => ({
      ...n,
      type: "custom",
      style: { background: "transparent", border: "none", padding: 0 },
    }))
  );

  const [edges, , onEdgesChange] = useEdgesState(
    rawEdges.map((e) => ({
      ...e,
      style: { stroke: "rgba(255,255,255,0.12)", strokeWidth: 1.5 },
      animated: e.data?.edgeType === "related_to",
    }))
  );

  const handleNodeClick = useCallback(
    (event, node) => {
      const label = node.data?.label;
      if (label && onNodeClick) onNodeClick(label);
    },
    [onNodeClick]
  );

  if (!rawNodes.length) return null;

  const meta = graph?.metadata || {};

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-white">🗺️ Knowledge Map</h2>
        <div className="flex gap-3 text-xs text-slate-500">
          <span>{meta.total_nodes} concepts</span>
          <span>·</span>
          <span>{meta.total_edges} connections</span>
          {onNodeClick && (
            <span className="text-orange-500/60">· click any node to research it</span>
          )}
        </div>
      </div>

      <div
        className="rounded-3xl overflow-hidden"
        style={{
          height: 420,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.07)",
        }}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick ? handleNodeClick : undefined}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.3}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="rgba(255,255,255,0.04)" gap={28} size={1} />
          <Controls
            style={{
              background: "rgba(8,5,3,0.8)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 12,
            }}
          />
          <MiniMap
            style={{
              background: "rgba(8,5,3,0.8)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 12,
            }}
            nodeColor={(n) => TYPE_COLOR[n.data?.nodeType] || "#64748b"}
            maskColor="rgba(0,0,0,0.7)"
          />
        </ReactFlow>
      </div>

      <div className="mt-3 flex flex-wrap gap-3">
        {Object.entries(TYPE_COLOR)
          .filter(([type]) => type !== "unknown" && type !== "platform")
          .map(([type, color]) => (
            <div key={type} className="flex items-center gap-1.5 text-xs text-slate-500">
              <div className="w-2 h-2 rounded-full" style={{ background: color }} />
              {type}
            </div>
          ))}
      </div>
    </motion.div>
  );
}
