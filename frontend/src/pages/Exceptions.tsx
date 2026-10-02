import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../services/api";
import type { Asset, PageData, RecordData } from "../types";
import {
  Badge,
  Editor,
  Heading,
  Pager,
  State,
  Table,
} from "../components/Common";
export function Exceptions() {
  const { id } = useParams();
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [page, setPage] = useState(1);
  const [form, setForm] = useState("");
  const [reviewId, setReviewId] = useState(0);
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["exceptions", id, status, severity, page],
    queryFn: () =>
      api<PageData & RecordData>(
        id
          ? `/exceptions/${id}`
          : `/exceptions?status=${encodeURIComponent(status)}&severity=${severity}&page=${page}`,
      ),
  });
  const users = useQuery({
    queryKey: ["users"],
    queryFn: () => api<PageData>("/users"),
  });
  const d = query.data;
  const move = useMutation({
    mutationFn: (newStatus: string) =>
      api(`/exceptions/${id}/transition`, "POST", { status: newStatus }),
    onSuccess: () => client.invalidateQueries(),
  });
  const state = String(d?.status || "");
  return (
    <>
      <Heading
        title={
          id
            ? String(d?.reference || "Governance exception")
            : "Governance exceptions"
        }
        description={
          id
            ? "Controlled remediation, independently reviewed evidence and an immutable application audit trail."
            : "Evidence-based resolution of failed governance controls."
        }
      />
      <State loading={query.isLoading} error={query.error} />
      {move.error && (
        <div className="error" role="alert">
          {move.error.message}
        </div>
      )}
      {d &&
        (id ? (
          <>
            <div className="profile-strip">
              <Badge value={d.status} />
              <Badge value={d.severity} />
              <span>
                Due {new Date(String(d.due_date)).toLocaleDateString()}
              </span>
              <Link to={`/assets/${(d.asset as Asset).id}`}>
                {(d.asset as Asset).name}
              </Link>
            </div>
            <div className="workflow-steps">
              {[
                "Open",
                "Assigned",
                "Remediation in Progress",
                "Pending Review",
                "Closed",
              ].map((s, i) => (
                <div key={s} className={s === state ? "current" : ""}>
                  <span>{i + 1}</span>
                  {s}
                </div>
              ))}
            </div>
            <div className="detail-grid">
              <section className="panel">
                <h3>Control failure & accountability</h3>
                <h4>{String((d.control as RecordData).name)}</h4>
                <p>{String((d.control as RecordData).description)}</p>
                <dl>
                  <dt>Assigned owner</dt>
                  <dd>
                    {String(
                      users.data?.items.find((u) => u.id === d.assignee_id)
                        ?.name || "Unassigned",
                    )}
                  </dd>
                  <dt>Detected</dt>
                  <dd>{new Date(String(d.detected_at)).toLocaleString()}</dd>
                  <dt>Remediation plan</dt>
                  <dd>{String(d.remediation_plan || "No plan recorded")}</dd>
                </dl>
                <div className="actions">
                  {state === "Open" && (
                    <button
                      className="primary"
                      onClick={() => setForm("assign")}
                    >
                      Assign remediation owner
                    </button>
                  )}
                  {["Assigned", "Rejected"].includes(state) && (
                    <button className="primary" onClick={() => setForm("plan")}>
                      Start remediation
                    </button>
                  )}
                  {state === "Remediation in Progress" && (
                    <>
                      <button onClick={() => setForm("evidence")}>
                        Submit evidence
                      </button>
                      <button
                        className="primary"
                        onClick={() => move.mutate("Pending Review")}
                      >
                        Request review
                      </button>
                    </>
                  )}
                  {state === "Pending Review" && (
                    <>
                      <button
                        className="primary"
                        onClick={() => move.mutate("Closed")}
                      >
                        Close exception
                      </button>
                      <button onClick={() => move.mutate("Rejected")}>
                        Reject remediation
                      </button>
                    </>
                  )}
                </div>
              </section>
              <section className="panel">
                <h3>Submitted evidence</h3>
                <p className="muted">
                  References are private metadata; files are not served
                  publicly.
                </p>
                {(d.evidence as RecordData[]).map((e) => (
                  <div className="evidence-card" key={e.id}>
                    <b>{String(e.document_name)}</b>
                    <Badge value={e.status} />
                    <p>{String(e.description)}</p>
                    <small>{String(e.local_reference)}</small>
                    {e.status === "Pending Review" &&
                      state === "Pending Review" && (
                        <button
                          onClick={() => {
                            setReviewId(e.id);
                            setForm("review");
                          }}
                        >
                          Review evidence
                        </button>
                      )}
                  </div>
                ))}
                {!(d.evidence as RecordData[]).length && (
                  <p>No evidence submitted yet.</p>
                )}
              </section>
              <section className="panel wide">
                <h3>Exception audit history</h3>
                <Table
                  rows={d.history as RecordData[]}
                  columns={[
                    { key: "action", label: "Event" },
                    { key: "actor", label: "Actor" },
                    {
                      key: "created_at",
                      label: "Recorded",
                      render: (r) =>
                        new Date(String(r.created_at)).toLocaleString(),
                    },
                    {
                      key: "after_value",
                      label: "Status",
                      render: (r) => (
                        <Badge value={(r.after_value as RecordData).status} />
                      ),
                    },
                  ]}
                />
              </section>
            </div>
          </>
        ) : (
          <>
            <div className="filters">
              <select
                aria-label="Exception status"
                value={status}
                onChange={(e) => {
                  setStatus(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All statuses</option>
                {[
                  "Open",
                  "Assigned",
                  "Remediation in Progress",
                  "Pending Review",
                  "Closed",
                  "Rejected",
                ].map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
              <select
                aria-label="Exception severity"
                value={severity}
                onChange={(e) => {
                  setSeverity(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All severities</option>
                {["Low", "Medium", "High", "Critical"].map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </div>
            <section className="panel flush">
              <Table
                rows={d.items}
                link="/exceptions"
                columns={[
                  { key: "reference", label: "Exception" },
                  { key: "asset_name", label: "Data asset" },
                  { key: "control_name", label: "Failed control" },
                  {
                    key: "severity",
                    label: "Severity",
                    render: (r) => <Badge value={r.severity} />,
                  },
                  {
                    key: "status",
                    label: "Status",
                    render: (r) => <Badge value={r.status} />,
                  },
                  {
                    key: "due_date",
                    label: "Due date",
                    render: (r) =>
                      new Date(String(r.due_date)).toLocaleDateString(),
                  },
                ]}
              />
              <Pager page={page} total={d.total} size={20} onChange={setPage} />
            </section>
          </>
        ))}
      {form && (
        <Editor
          title={
            {
              assign: "Assign remediation owner",
              plan: "Record remediation plan",
              evidence: "Submit evidence metadata",
              review: "Review submitted evidence",
            }[form] || ""
          }
          fields={
            form === "assign"
              ? [
                  {
                    name: "assignee_id",
                    label: "Accountable remediator",
                    required: true,
                    options: users.data?.items.map((u) => ({
                      value: String(u.id),
                      label: String(u.name),
                    })),
                  },
                ]
              : form === "plan"
                ? [
                    {
                      name: "remediation_plan",
                      label: "Remediation plan",
                      type: "textarea",
                      required: true,
                    },
                  ]
                : form === "review"
                  ? [
                      {
                        name: "status",
                        label: "Decision",
                        required: true,
                        options: [
                          { value: "Approved", label: "Approved" },
                          { value: "Rejected", label: "Rejected" },
                        ],
                      },
                      {
                        name: "notes",
                        label: "Review rationale",
                        type: "textarea",
                        required: true,
                      },
                    ]
                  : [
                      {
                        name: "document_name",
                        label: "Document name",
                        required: true,
                      },
                      {
                        name: "document_type",
                        label: "Evidence type",
                        required: true,
                      },
                      {
                        name: "local_reference",
                        label: "Private relative reference",
                        required: true,
                      },
                      {
                        name: "description",
                        label: "Evidence description",
                        type: "textarea",
                        required: true,
                      },
                    ]
          }
          onClose={() => setForm("")}
          onSave={async (v) => {
            if (form === "assign")
              await api(`/exceptions/${id}/transition`, "POST", {
                status: "Assigned",
                assignee_id: Number(v.assignee_id),
              });
            else if (form === "plan")
              await api(`/exceptions/${id}/transition`, "POST", {
                status: "Remediation in Progress",
                ...v,
              });
            else if (form === "review")
              await api(`/evidence/${reviewId}/review`, "POST", v);
            else
              await api("/evidence", "POST", {
                ...v,
                exception_id: Number(id),
              });
            await client.invalidateQueries();
          }}
        />
      )}
    </>
  );
}
