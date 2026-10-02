import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import type { Adoption, PageData, RecordData } from "../types";
import {
  Badge,
  Editor,
  Heading,
  Pager,
  RunButton,
  State,
  Table,
  type Column,
} from "../components/Common";
import { qualityColumns } from "./AssetDetail";
export function Operations({ kind }: { kind: string }) {
  const [page, setPage] = useState(1);
  const [edit, setEdit] = useState(false);
  const [selectedUser, setSelectedUser] = useState<RecordData | null>(null);
  const client = useQueryClient();
  const config: Record<
    string,
    { title: string; description: string; path: string; columns: Column[] }
  > = {
    quality: {
      title: "Data quality",
      description:
        "Great Expectations checks against synthetic banking files, with persisted observed results.",
      path: "/data-quality/results",
      columns: [
        {
          key: "data_asset_id",
          label: "Asset",
          render: (r) => (
            <Link to={`/assets/${r.data_asset_id}`}>
              Asset #{String(r.data_asset_id)}
            </Link>
          ),
        },
        ...qualityColumns,
      ],
    },
    controls: {
      title: "Governance controls",
      description:
        "Policy checks turn missing governance requirements into actionable exceptions.",
      path: "/governance-controls",
      columns: [
        { key: "code", label: "Control" },
        { key: "name", label: "Requirement" },
        { key: "description", label: "Policy" },
        {
          key: "severity",
          label: "Severity",
          render: (r) => <Badge value={r.severity} />,
        },
      ],
    },
    evidence: {
      title: "Evidence register",
      description:
        "Private document references with submission and independent review metadata.",
      path: "/evidence",
      columns: [
        { key: "document_name", label: "Document" },
        { key: "document_type", label: "Type" },
        {
          key: "exception_id",
          label: "Exception",
          render: (r) => (
            <Link to={`/exceptions/${r.exception_id}`}>Open exception →</Link>
          ),
        },
        {
          key: "status",
          label: "Review status",
          render: (r) => <Badge value={r.status} />,
        },
        { key: "description", label: "Description" },
      ],
    },
    audit: {
      title: "Audit log",
      description:
        "Append-only application history of governance decisions and metadata changes.",
      path: "/audit",
      columns: [
        { key: "action", label: "Action" },
        { key: "actor", label: "Actor" },
        { key: "entity_type", label: "Entity" },
        { key: "entity_id", label: "Record" },
        {
          key: "created_at",
          label: "Timestamp",
          render: (r) => new Date(String(r.created_at)).toLocaleString(),
        },
        {
          key: "after_value",
          label: "Change record",
          render: (r) => (
            <details>
              <summary>Before / after</summary>
              <pre>
                {JSON.stringify(
                  { before: r.before_value, after: r.after_value },
                  null,
                  2,
                )}
              </pre>
            </details>
          ),
        },
      ],
    },
    admin: {
      title: "Administration",
      description:
        "Governance stakeholders, application roles and accountable access.",
      path: "/users",
      columns: [
        {
          key: "name",
          label: "Stakeholder",
          render: (r) => (
            <button className="text-button" onClick={() => setSelectedUser(r)}>
              {String(r.name)}
            </button>
          ),
        },
        { key: "email", label: "Email" },
        { key: "role", label: "Role", render: (r) => <Badge value={r.role} /> },
        {
          key: "active",
          label: "Active",
          render: (r) => (r.active ? "Yes" : "No"),
        },
      ],
    },
  };
  const c = config[kind];
  const query = useQuery({
    queryKey: [kind, page],
    queryFn: () => api<PageData>(`${c.path}?page=${page}&page_size=20`),
  });
  return (
    <>
      <Heading
        title={c.title}
        description={c.description}
        action={
          kind === "quality" ? (
            <RunButton
              path="/data-quality/run"
              label="Execute quality checks"
            />
          ) : kind === "controls" ? (
            <RunButton
              path="/governance-controls/run"
              label="Execute governance controls"
            />
          ) : kind === "admin" ? (
            <button onClick={() => setEdit(true)}>Create stakeholder</button>
          ) : undefined
        }
      />
      <State loading={query.isLoading} error={query.error} />
      {query.data && (
        <section className="panel flush">
          <Table rows={query.data.items} columns={c.columns} />
          {query.data.total !== undefined && (
            <Pager
              page={page}
              total={query.data.total}
              size={20}
              onChange={setPage}
            />
          )}
        </section>
      )}
      {kind === "controls" && <ExecutionHistory />}
      {selectedUser && (
        <Editor
          title="Manage stakeholder access"
          initial={{
            name: selectedUser.name,
            role: selectedUser.role,
            active: String(selectedUser.active),
          }}
          fields={[
            { name: "name", label: "Name", required: true },
            {
              name: "role",
              label: "Role",
              required: true,
              options: [
                "ADMIN",
                "GOVERNANCE_ANALYST",
                "DATA_OWNER",
                "DATA_STEWARD",
                "REVIEWER",
              ].map((v) => ({ value: v, label: v })),
            },
            {
              name: "active",
              label: "Account status",
              required: true,
              options: [
                { value: "true", label: "Active" },
                { value: "false", label: "Inactive" },
              ],
            },
          ]}
          onClose={() => setSelectedUser(null)}
          onSave={async (v) => {
            await api(`/users/${selectedUser.id}`, "PATCH", {
              ...v,
              active: v.active === "true",
            });
            await client.invalidateQueries();
          }}
        />
      )}

      {edit && (
        <Editor
          title="Create stakeholder"
          fields={[
            { name: "name", label: "Name", required: true },
            { name: "email", label: "Email", type: "email", required: true },
            {
              name: "password",
              label: "Initial password (12+ characters)",
              type: "password",
              required: true,
            },
            {
              name: "role",
              label: "Role",
              required: true,
              options: [
                "ADMIN",
                "GOVERNANCE_ANALYST",
                "DATA_OWNER",
                "DATA_STEWARD",
                "REVIEWER",
              ].map((v) => ({ value: v, label: v })),
            },
          ]}
          onClose={() => setEdit(false)}
          onSave={async (v) => {
            await api("/users", "POST", v);
            await client.invalidateQueries();
          }}
        />
      )}
    </>
  );
}
function ExecutionHistory() {
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["executions", page],
    queryFn: () => api<PageData>(`/control-executions?page=${page}`),
  });
  return (
    <section className="panel">
      <h3>Control execution evidence</h3>
      {query.data && (
        <>
          <Table
            rows={query.data.items}
            columns={[
              { key: "control_id", label: "Control" },
              {
                key: "data_asset_id",
                label: "Asset",
                render: (r) => (
                  <Link to={`/assets/${r.data_asset_id}`}>
                    Asset #{String(r.data_asset_id)}
                  </Link>
                ),
              },
              {
                key: "result",
                label: "Outcome",
                render: (r) => <Badge value={r.result} />,
              },
              {
                key: "evidence",
                label: "Evidence",
                render: (r) => (
                  <details>
                    <summary>Inspect</summary>
                    <pre>{JSON.stringify(r.evidence, null, 2)}</pre>
                  </details>
                ),
              },
              {
                key: "execution_time",
                label: "Executed",
                render: (r) =>
                  new Date(String(r.execution_time)).toLocaleString(),
              },
            ]}
          />
          <Pager
            page={page}
            total={query.data.total}
            size={20}
            onChange={setPage}
          />
        </>
      )}
    </section>
  );
}
export function AdoptionPage() {
  const query = useQuery({
    queryKey: ["adoption"],
    queryFn: () => api<{ items: Adoption[] }>("/adoption"),
  });
  return (
    <>
      <Heading
        title="Governance adoption"
        description="Business division coverage calculated from active catalog assets. Quality coverage indicates rule registration, rather than a quality pass rate."
      />
      <State loading={query.isLoading} error={query.error} />
      {query.data && (
        <section className="panel">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Business division</th>
                  <th>Assets</th>
                  {[
                    "Ownership",
                    "Stewardship",
                    "Metadata",
                    "Classification",
                    "Lineage",
                    "Quality",
                    "Review",
                    "Adoption",
                  ].map((s) => (
                    <th key={s}>{s}</th>
                  ))}
                  <th>Open exceptions</th>
                </tr>
              </thead>
              <tbody>
                {query.data.items.map((r) => (
                  <tr key={r.domain}>
                    <td>
                      <b>{r.domain}</b>
                    </td>
                    <td>{r.assets}</td>
                    {[
                      r.ownership,
                      r.stewardship,
                      r.metadata,
                      r.classification,
                      r.lineage,
                      r.quality,
                      r.review,
                      r.adoption_score,
                    ].map((v, i) => (
                      <td key={i}>
                        <span>{v}%</span>
                        <div className="mini-bar">
                          <i style={{ width: `${v}%` }} />
                        </div>
                      </td>
                    ))}
                    <td>{r.open_exceptions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      <section className="panel">
        <h3>Assessment method</h3>
        <p>
          Each division's adoption score is the unweighted mean of ownership,
          stewardship, required metadata, classification, documented lineage,
          registered quality rules and review currency. The enterprise score
          weights divisions by their active asset count. Open exceptions remain
          open until reviewed and closed.
        </p>
      </section>
    </>
  );
}
