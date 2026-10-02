import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../services/api";
import type { Asset, GraphData, PageData } from "../types";
import { Editor, Heading, State } from "../components/Common";
import { LineageGraph } from "../components/LineageGraph";
export function Lineage() {
  const assets = useQuery({
    queryKey: ["all-assets"],
    queryFn: () => api<PageData<Asset>>("/assets?page_size=100"),
  });
  const [selected, setSelected] = useState("");
  const [direction, setDirection] = useState("assets");
  const [edit, setEdit] = useState(false);
  const client = useQueryClient();
  const id =
    selected ||
    String(
      assets.data?.items.find((a) => a.name === "customer_risk")?.id || "",
    );
  const graph = useQuery({
    queryKey: ["lineage", id, direction],
    queryFn: () => api<GraphData>(`/lineage/${direction}/${id}`),
    enabled: !!id,
  });
  return (
    <>
      <Heading
        title="Data lineage explorer"
        description="Trace source-to-report dependencies and inspect transformation context."
        action={<button onClick={() => setEdit(true)}>Document lineage</button>}
      />
      <div className="filters">
        <select
          aria-label="Select lineage asset"
          value={id}
          onChange={(e) => setSelected(e.target.value)}
        >
          {assets.data?.items.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Lineage direction"
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
        >
          <option value="assets">Both directions</option>
          <option value="upstream">Upstream sources</option>
          <option value="downstream">Downstream consumers</option>
        </select>
      </div>
      <State loading={graph.isLoading} error={graph.error} />
      {graph.data && (
        <section className="panel">
          <LineageGraph graph={graph.data} />
        </section>
      )}
      <section className="panel">
        <h3>Capture scope & provenance</h3>
        <p>
          OpenLineage events from the Airflow metadata pipeline capture
          dataset-level dependencies. Field mappings are curated explicitly and
          shown in CDE profiles. A connected graph indicates documented
          dependencies, rather than proof of full regulatory completeness.
        </p>
      </section>
      {edit && (
        <Editor
          title="Document dataset lineage"
          fields={[
            {
              name: "source_asset_id",
              label: "Upstream asset",
              required: true,
              options: assets.data?.items.map((a) => ({
                value: String(a.id),
                label: a.name,
              })),
            },
            {
              name: "target_asset_id",
              label: "Downstream asset",
              required: true,
              options: assets.data?.items.map((a) => ({
                value: String(a.id),
                label: a.name,
              })),
            },
            {
              name: "transformation",
              label: "Transformation description",
              type: "textarea",
              required: true,
            },
          ]}
          onClose={() => setEdit(false)}
          onSave={async (v) => {
            await api("/lineage/edges", "POST", {
              ...v,
              source_asset_id: Number(v.source_asset_id),
              target_asset_id: Number(v.target_asset_id),
            });
            await client.invalidateQueries();
          }}
        />
      )}
    </>
  );
}
