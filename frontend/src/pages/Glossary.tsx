import { useState } from "react";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { api } from "../services/api";
import type { PageData, RecordData } from "../types";
import {
  Badge,
  Editor,
  Heading,
  Pager,
  State,
  Table,
} from "../components/Common";
export function Glossary() {
  const { id } = useParams();
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [edit, setEdit] = useState(false);
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ["glossary", id, q, page],
    queryFn: () =>
      api<PageData & RecordData>(
        id
          ? `/business-terms/${id}`
          : `/business-terms?q=${encodeURIComponent(q)}&page=${page}`,
      ),
  });
  const domains = useQuery({
    queryKey: ["domains"],
    queryFn: () => api<PageData>("/domains"),
  });
  const users = useQuery({
    queryKey: ["users"],
    queryFn: () => api<PageData>("/users"),
  });
  const approve = useMutation({
    mutationFn: () => api(`/business-terms/${id}/approve`, "POST"),
    onSuccess: () => client.invalidateQueries(),
  });
  const d = query.data;
  return (
    <>
      <Heading
        title={id ? String(d?.name || "Business term") : "Business glossary"}
        description={
          id
            ? "A controlled definition linking business meaning to physical data."
            : "Shared, approved business language across the enterprise."
        }
        action={
          <div className="actions">
            <button onClick={() => setEdit(true)}>
              {id ? "Edit term" : "Create term"}
            </button>
            {id && d?.approval_status !== "Approved" && (
              <button className="primary" onClick={() => approve.mutate()}>
                Approve term
              </button>
            )}
          </div>
        }
      />
      {approve.error && <p className="error">{approve.error.message}</p>}
      <State loading={query.isLoading} error={query.error} />
      {!id && (
        <div className="filters">
          <input
            aria-label="Search terms"
            placeholder="Search business terms…"
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
          />
        </div>
      )}
      {d &&
        (id ? (
          <>
            <section className="panel">
              <Badge value={d.approval_status} />
              <h3>Business definition</h3>
              <p className="definition">{String(d.definition)}</p>
              <dl>
                <dt>Owner</dt>
                <dd>
                  {String(
                    users.data?.items.find((u) => u.id === d.owner_id)?.name ||
                      "Unassigned",
                  )}
                </dd>
                <dt>Steward</dt>
                <dd>
                  {String(
                    users.data?.items.find((u) => u.id === d.steward_id)
                      ?.name || "Unassigned",
                  )}
                </dd>
              </dl>
            </section>
            <section className="panel">
              <h3>Assets using this term</h3>
              <Table
                rows={d.assets as RecordData[]}
                link="/assets"
                columns={[
                  { key: "name", label: "Data asset" },
                  { key: "domain", label: "Division" },
                  { key: "classification", label: "Classification" },
                ]}
              />
              <h3>Linked fields</h3>
              <Table
                rows={d.fields as RecordData[]}
                columns={[
                  { key: "name", label: "Field" },
                  {
                    key: "is_cde",
                    label: "CDE",
                    render: (r) =>
                      r.is_cde ? (
                        <Link to={`/cdes/${r.id}`}>Open CDE →</Link>
                      ) : (
                        "Standard field"
                      ),
                  },
                ]}
              />
            </section>
          </>
        ) : (
          <section className="panel flush">
            <Table
              rows={d.items}
              link="/business-terms"
              columns={[
                { key: "name", label: "Business term" },
                { key: "definition", label: "Definition" },
                {
                  key: "approval_status",
                  label: "Approval",
                  render: (r) => <Badge value={r.approval_status} />,
                },
              ]}
            />
            <Pager page={page} total={d.total} size={20} onChange={setPage} />
          </section>
        ))}
      {edit && (
        <Editor
          title={id ? "Edit business term" : "Create business term"}
          initial={
            id
              ? {
                  name: d?.name,
                  definition: d?.definition,
                  business_domain_id: d?.business_domain_id,
                  owner_id: d?.owner_id,
                  steward_id: d?.steward_id,
                }
              : {}
          }
          fields={[
            { name: "name", label: "Term name", required: true },
            {
              name: "definition",
              label: "Business definition",
              type: "textarea",
              required: true,
            },
            {
              name: "business_domain_id",
              label: "Business division",
              required: true,
              options: domains.data?.items.map((r) => ({
                value: String(r.id),
                label: String(r.name),
              })),
            },
            {
              name: "owner_id",
              label: "Data owner",
              options: users.data?.items.map((r) => ({
                value: String(r.id),
                label: String(r.name),
              })),
            },
            {
              name: "steward_id",
              label: "Data steward",
              options: users.data?.items.map((r) => ({
                value: String(r.id),
                label: String(r.name),
              })),
            },
          ]}
          onClose={() => setEdit(false)}
          onSave={async (v) => {
            await api(
              id ? `/business-terms/${id}` : "/business-terms",
              id ? "PUT" : "POST",
              {
                ...v,
                business_domain_id: Number(v.business_domain_id),
                owner_id: v.owner_id ? Number(v.owner_id) : null,
                steward_id: v.steward_id ? Number(v.steward_id) : null,
              },
            );
            await client.invalidateQueries();
          }}
        />
      )}
    </>
  );
}
