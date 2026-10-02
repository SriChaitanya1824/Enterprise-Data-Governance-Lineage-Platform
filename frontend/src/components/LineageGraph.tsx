import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ReactFlow, Background, Controls, MarkerType } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { GraphData } from "../types";
export function LineageGraph({ graph }: { graph: GraphData }) {
  const navigate = useNavigate();
  const { nodes, edges } = useMemo(() => {
    const depth = new Map<number, number>(graph.nodes.map((n) => [n.id, 0]));
    for (let pass = 0; pass < graph.nodes.length; pass++)
      for (const e of graph.edges)
        depth.set(
          e.target_asset_id,
          Math.max(
            depth.get(e.target_asset_id) || 0,
            (depth.get(e.source_asset_id) || 0) + 1,
          ),
        );
    const groups = new Map<number, number>();
    const nodes = graph.nodes.map((n) => {
      const level = depth.get(n.id) || 0;
      const offset = groups.get(level) || 0;
      groups.set(level, offset + 1);
      return {
        id: String(n.id),
        position: { x: level * 240, y: offset * 120 },
        data: {
          label: (
            <div>
              <small>{n.source_system}</small>
              <strong>{n.name.replaceAll("_", " ")}</strong>
              <span>{n.asset_type as string}</span>
            </div>
          ),
        },
        style: {
          width: 205,
          border:
            n.asset_type === "Report"
              ? "1px solid #9b7344"
              : "1px solid #b5c5d3",
          borderRadius: 8,
          background: n.asset_type === "Report" ? "#fff8ec" : "#fff",
        },
      };
    });
    const unique = new Map<string, GraphData["edges"][0]>();
    for (const e of graph.edges)
      unique.set(`${e.source_asset_id}-${e.target_asset_id}`, e);
    const edges = [...unique.values()].map((e) => ({
      id: String(e.id),
      source: String(e.source_asset_id),
      target: String(e.target_asset_id),
      label: e.origin === "OpenLineage" ? "Captured" : "Documented",
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: "#538b9a" },
      labelStyle: { fontSize: 10 },
      data: { transformation: e.transformation },
    }));
    return { nodes, edges };
  }, [graph]);
  return (
    <div>
      <div className="graph-caption">
        {graph.scope === "field"
          ? "Documented field mappings"
          : "Dataset lineage · captured and documented edges"}{" "}
        · Select a node to inspect its governance profile
      </div>
      <div className="lineage-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          nodesDraggable
          nodesConnectable={false}
          onNodeClick={(_, node) => navigate(`/assets/${node.id}`)}
          onEdgeClick={(_, edge) =>
            window.alert(String(edge.data?.transformation))
          }
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
}
