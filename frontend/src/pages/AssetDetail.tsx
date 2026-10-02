import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../services/api";
import type { Asset, GraphData, PageData, RecordData } from "../types";
import { Badge, Editor, Heading, State, Table } from "../components/Common";
import { LineageGraph } from "../components/LineageGraph";
const fieldColumns = [
  {
    key: "name",
    label: "Field",
    render: (r: RecordData) =>
      r.is_cde ? (
        <Link to={`/cdes/${r.id}`}>{String(r.name)}</Link>
      ) : (
        String(r.name)
      ),
  },
  { key: "data_type", label: "Data type" },
  {
    key: "is_cde",
    label: "CDE",
    render: (r: RecordData) => (r.is_cde ? <Badge value="Critical" /> : "—"),
  },
  { key: "classification", label: "Classification" },
  {
    key: "business_term_id",
    label: "Business term",
    render: (r: RecordData) =>
      r.business_term_id ? (
        <Link to={`/business-terms/${r.business_term_id}`}>
          View term #{String(r.business_term_id)}
        </Link>
      ) : (
        "—"
      ),
  },
  { key: "regulatory_tag", label: "Regulatory tag" },
];
export const qualityColumns = [
  { key: "rule_id", label: "Rule" },
  {
    key: "passed",
    label: "Outcome",
    render: (r: RecordData) => <Badge value={r.passed ? "PASS" : "FAIL"} />,
  },
  {
    key: "score",
    label: "Row success",
    render: (r: RecordData) => `${r.score}%`,
  },
  {
    key: "severity",
    label: "Severity",
    render: (r: RecordData) => <Badge value={r.severity} />,
  },
  {
    key: "execution_time",
    label: "Executed",
    render: (r: RecordData) =>
      new Date(String(r.execution_time)).toLocaleString(),
  },
  {
    key: "actual_result",
    label: "Observed result",
    render: (r: RecordData) => (
      <details>
        <summary>Inspect</summary>
        <pre>{JSON.stringify(r.actual_result, null, 2)}</pre>
      </details>
    ),
  },
];
export function AssetDetail({ cde = false }: { cde?: boolean }) {
  const { id } = useParams();
  const [tab, setTab] = useState("Overview");
  const [edit, setEdit] = useState(false);
  const [fieldEdit, setFieldEdit] = useState(false);
  const client = useQueryClient();
  const query = useQuery({
    queryKey: [cde ? "cde" : "asset", id],
    queryFn: () => api<RecordData>(`/${cde ? "cdes" : "assets"}/${id}`),
  });
  const users = useQuery({
    queryKey: ["users"],
    queryFn: () => api<PageData>("/users"),
  });
  const terms = useQuery({
    queryKey: ["terms-all"],
    queryFn: () => api<PageData>("/business-terms?page_size=100"),
  });
  const data = query.data;
  const asset = (cde ? data?.asset : data) as Asset | undefined;
  const graph = (cde ? data?.lineage : asset?.lineage) as GraphData | undefined;
  const title = cde
    ? String(
        (data?.business_term as RecordData | undefined)?.name ||
          data?.name ||
          "Critical data element",
      )
    : asset?.name.replaceAll("_", " ") || "Asset governance profile";
  return (
    <>
      <Link className="breadcrumb" to={cde ? "/cdes" : "/assets"}>
        ← {cde ? "Critical data elements" : "Data catalog"}
      </Link>
      <Heading
        title={title}
        eyebrow={
          cde
            ? "CRITICAL DATA ELEMENT / GOVERNANCE PROFILE"
            : "DATA CATALOG / ASSET PROFILE"
        }
        description={String(
          cde ? data?.description || "" : asset?.description || "",
        )}
        action={
          <button onClick={() => setEdit(true)}>
            Edit governance metadata
          </button>
        }
      />
      <State loading={query.isLoading} error={query.error} />
      {asset && (
        <>
          <div className="profile-strip">
            <Badge value={asset.classification} />
            <Badge value={asset.criticality} />
            <span>{asset.domain}</span>
            <span>
              {asset.regulatory_relevance
                ? "Regulatory relevance · BCBS 239"
                : "Enterprise catalog"}
            </span>
            <span>
              Quality:{" "}
              <b>
                {asset.quality_score === null
                  ? "Unmeasured"
                  : `${asset.quality_score}%`}
              </b>
            </span>
          </div>
          <div className="tabs">
            {[
              "Overview",
              "Fields",
              "Quality",
              "Lineage",
              "Governance",
              "Exceptions",
            ].map((t) => (
              <button
                className={tab === t ? "selected" : ""}
                onClick={() => setTab(t)}
                key={t}
              >
                {t}
              </button>
            ))}
          </div>
          {tab === "Overview" && (
            <div className="detail-grid">
              <section className="panel">
                <h3>Accountability & business context</h3>
                <dl>
                  <dt>Data owner</dt>
                  <dd>{asset.owner || <Badge value="Unassigned" />}</dd>
                  <dt>Data steward</dt>
                  <dd>{asset.steward || <Badge value="Unassigned" />}</dd>
                  <dt>Business division</dt>
                  <dd>{asset.domain}</dd>
                  <dt>Classification</dt>
                  <dd>{asset.classification}</dd>
                  <dt>Criticality</dt>
                  <dd>{asset.criticality}</dd>
                  <dt>Business term</dt>
                  <dd>
                    {cde
                      ? String(
                          (data?.business_term as RecordData | undefined)
                            ?.name || "Unlinked",
                        )
                      : "See field definitions"}
                  </dd>
                </dl>
              </section>
              <section className="panel">
                <h3>Technical metadata</h3>
                <dl>
                  <dt>Source system</dt>
                  <dd>{asset.source_system}</dd>
                  <dt>Physical location</dt>
                  <dd>
                    <code>{String(asset.physical_location)}</code>
                  </dd>
                  <dt>Asset type</dt>
                  <dd>{String(asset.asset_type)}</dd>
                  <dt>Last reviewed</dt>
                  <dd>
                    {asset.last_reviewed_at
                      ? new Date(
                          String(asset.last_reviewed_at),
                        ).toLocaleDateString()
                      : "Never reviewed"}
                  </dd>
                  <dt>Registered</dt>
                  <dd>
                    {new Date(String(asset.created_at)).toLocaleDateString()}
                  </dd>
                </dl>
              </section>
              {cde && (
                <section className="panel wide">
                  <h3>Critical data definition</h3>
                  <p>
                    {String(
                      (data?.business_term as RecordData | undefined)
                        ?.definition || data?.description,
                    )}
                  </p>
                  <p>
                    Regulatory tag: <Badge value={data?.regulatory_tag} />
                  </p>
                  <Link to={`/assets/${asset.id}`}>
                    Open full asset profile →
                  </Link>
                </section>
              )}
            </div>
          )}
          {tab === "Fields" && (
            <section className="panel">
              <div className="panel-heading">
                <h3>Field inventory & critical elements</h3>
                <button onClick={() => setFieldEdit(true)}>
                  Register field
                </button>
              </div>
              <Table rows={asset.fields || []} columns={fieldColumns} />
            </section>
          )}
          {tab === "Quality" && (
            <section className="panel">
              <h3>Measured quality results</h3>
              <p>
                Mean row success across the latest result per rule. A failed
                strict rule can still have a high row success rate.
              </p>
              <Table
                rows={asset.quality_results || []}
                columns={qualityColumns}
              />
            </section>
          )}
          {tab === "Lineage" && graph && (
            <section className="panel">
              <h3>
                {cde
                  ? "Critical field traceability"
                  : "Upstream & downstream lineage"}
              </h3>
              <LineageGraph graph={graph} />
              <p className="muted">
                Field mappings are explicitly documented. OpenLineage processing
                jobs capture dataset dependencies.
              </p>
            </section>
          )}
          {tab === "Governance" && (
            <section className="panel">
              <h3>Latest governance controls</h3>
              <Table
                rows={asset.controls || []}
                columns={[
                  { key: "control_id", label: "Control" },
                  {
                    key: "result",
                    label: "Outcome",
                    render: (r) => <Badge value={r.result} />,
                  },
                  { key: "severity", label: "Severity" },
                  {
                    key: "evidence",
                    label: "Control evidence",
                    render: (r) => (
                      <details>
                        <summary>Inspect evidence</summary>
                        <pre>{JSON.stringify(r.evidence, null, 2)}</pre>
                      </details>
                    ),
                  },
                ]}
              />
            </section>
          )}
          {tab === "Exceptions" && (
            <section className="panel">
              <h3>Linked governance exceptions</h3>
              <Table
                rows={asset.exceptions || []}
                link="/exceptions"
                columns={[
                  { key: "reference", label: "Exception" },
                  {
                    key: "status",
                    label: "Status",
                    render: (r) => <Badge value={r.status} />,
                  },
                  { key: "severity", label: "Severity" },
                  {
                    key: "due_date",
                    label: "Due date",
                    render: (r) =>
                      new Date(String(r.due_date)).toLocaleDateString(),
                  },
                ]}
              />
            </section>
          )}
          {edit && (
            <Editor
              title="Edit governance metadata"
              fields={[
                {
                  name: "description",
                  label: "Description",
                  type: "textarea",
                  required: true,
                },
                {
                  name: "owner_id",
                  label: "Data owner",
                  options: users.data?.items.map((u) => ({
                    value: String(u.id),
                    label: String(u.name),
                  })),
                },
                {
                  name: "steward_id",
                  label: "Data steward",
                  options: users.data?.items.map((u) => ({
                    value: String(u.id),
                    label: String(u.name),
                  })),
                },
                {
                  name: "classification",
                  label: "Classification",
                  options: [
                    "Public",
                    "Internal",
                    "Confidential",
                    "Restricted",
                  ].map((v) => ({ value: v, label: v })),
                  required: true,
                },
                {
                  name: "last_reviewed_at",
                  label: "Review date",
                  type: "date",
                },
              ]}
              initial={{
                description: asset.description,
                owner_id: asset.owner_id,
                steward_id: asset.steward_id,
                classification: asset.classification,
                last_reviewed_at: String(asset.last_reviewed_at || "").slice(
                  0,
                  10,
                ),
              }}
              onClose={() => setEdit(false)}
              onSave={async (v) => {
                await api(`/assets/${asset.id}`, "PATCH", {
                  ...v,
                  owner_id: v.owner_id ? Number(v.owner_id) : null,
                  steward_id: v.steward_id ? Number(v.steward_id) : null,
                  last_reviewed_at: v.last_reviewed_at
                    ? `${v.last_reviewed_at}T00:00:00Z`
                    : null,
                });
                await client.invalidateQueries();
              }}
            />
          )}
          {fieldEdit && (
            <Editor
              title="Register field / CDE"
              fields={[
                { name: "name", label: "Field name", required: true },
                { name: "data_type", label: "Data type", required: true },
                {
                  name: "description",
                  label: "Definition",
                  type: "textarea",
                  required: true,
                },
                {
                  name: "classification",
                  label: "Classification",
                  options: [
                    "Public",
                    "Internal",
                    "Confidential",
                    "Restricted",
                  ].map((v) => ({ value: v, label: v })),
                  required: true,
                },
                {
                  name: "is_cde",
                  label: "Critical data element",
                  options: [
                    { value: "true", label: "Yes" },
                    { value: "false", label: "No" },
                  ],
                  required: true,
                },
                {
                  name: "business_term_id",
                  label: "Business term",
                  options: terms.data?.items.map((t) => ({
                    value: String(t.id),
                    label: String(t.name),
                  })),
                },
                { name: "regulatory_tag", label: "Regulatory tag" },
              ]}
              initial={{
                classification: asset.classification,
                is_cde: "false",
                data_type: "string",
              }}
              onClose={() => setFieldEdit(false)}
              onSave={async (v) => {
                await api("/fields", "POST", {
                  ...v,
                  data_asset_id: asset.id,
                  is_cde: v.is_cde === "true",
                  business_term_id: v.business_term_id
                    ? Number(v.business_term_id)
                    : null,
                  regulatory_tag: v.regulatory_tag || null,
                  nullable: false,
                });
                await client.invalidateQueries();
              }}
            />
          )}
        </>
      )}
    </>
  );
}
