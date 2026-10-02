import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
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
export function Catalog({ cdes = false }: { cdes?: boolean }) {
  const [q, setQ] = useState("");
  const [domain, setDomain] = useState("");
  const [page, setPage] = useState(1);
  const [create, setCreate] = useState(false);
  const client = useQueryClient();
  const query = useQuery({
    queryKey: [cdes ? "cdes" : "assets", q, domain, page],
    queryFn: () =>
      api<PageData>(
        `/${cdes ? "cdes" : "assets"}?q=${encodeURIComponent(q)}&page=${page}${domain ? `&domain_id=${domain}` : ""}`,
      ),
  });
  const domains = useQuery({
    queryKey: ["domains"],
    queryFn: () => api<PageData>("/domains"),
  });
  const people = useQuery({
    queryKey: ["users"],
    queryFn: () => api<PageData>("/users"),
  });
  const columns = cdes
    ? [
        {
          key: "name",
          label: "Critical data element",
          render: (r: RecordData) => (
            <Link to={`/cdes/${r.id}`}>
              {String(r.term || r.name)}
              <small className="cell-sub">{String(r.name)}</small>
            </Link>
          ),
        },
        {
          key: "asset",
          label: "Data asset",
          render: (r: RecordData) => (
            <Link to={`/assets/${(r.asset as Asset).id}`}>
              {(r.asset as Asset).name}
            </Link>
          ),
        },
        {
          key: "classification",
          label: "Classification",
          render: (r: RecordData) => <Badge value={r.classification} />,
        },
        {
          key: "owner",
          label: "Accountable owner",
          render: (r: RecordData) => <Badge value={(r.asset as Asset).owner} />,
        },
        {
          key: "quality",
          label: "Quality",
          render: (r: RecordData) =>
            `${(r.asset as Asset).quality_score ?? "—"}%`,
        },
      ]
    : [
        { key: "name", label: "Data asset" },
        { key: "domain", label: "Division" },
        {
          key: "owner",
          label: "Data owner",
          render: (r: RecordData) =>
            r.owner ? String(r.owner) : <Badge value="Unassigned" />,
        },
        {
          key: "classification",
          label: "Classification",
          render: (r: RecordData) => <Badge value={r.classification} />,
        },
        { key: "criticality", label: "Criticality" },
        {
          key: "quality_score",
          label: "Quality",
          render: (r: RecordData) =>
            r.quality_score === null ? "Unmeasured" : `${r.quality_score}%`,
        },
      ];
  return (
    <>
      <Heading
        title={cdes ? "Critical data elements" : "Data catalog"}
        description={
          cdes
            ? "Identify the fields that matter most to risk, finance and regulatory reporting."
            : "A governed inventory of enterprise data assets and accountable stakeholders."
        }
        action={
          !cdes && (
            <button className="primary" onClick={() => setCreate(true)}>
              Register asset
            </button>
          )
        }
      />
      <div className="filters">
        <input
          aria-label="Search catalog"
          placeholder={
            cdes
              ? "Search critical data elements…"
              : "Search assets or descriptions…"
          }
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
        />
        <select
          aria-label="Business division"
          value={domain}
          onChange={(e) => {
            setDomain(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All business divisions</option>
          {domains.data?.items.map((d) => (
            <option key={d.id} value={d.id}>
              {String(d.name)}
            </option>
          ))}
        </select>
        <span>{query.data?.total ?? 0} records</span>
      </div>
      <State loading={query.isLoading} error={query.error} />
      {query.data && (
        <section className="panel flush">
          <Table
            rows={query.data.items}
            columns={columns}
            link={cdes ? "/cdes" : "/assets"}
          />
          <Pager
            page={page}
            total={query.data.total}
            size={20}
            onChange={setPage}
          />
        </section>
      )}
      {create && (
        <Editor
          title="Register data asset"
          fields={[
            { name: "name", label: "Asset name", required: true },
            {
              name: "description",
              label: "Business description",
              type: "textarea",
              required: true,
            },
            {
              name: "business_domain_id",
              label: "Business division",
              options: domains.data?.items.map((d) => ({
                value: String(d.id),
                label: String(d.name),
              })),
              required: true,
            },
            {
              name: "owner_id",
              label: "Data owner",
              options: people.data?.items.map((p) => ({
                value: String(p.id),
                label: String(p.name),
              })),
            },
            {
              name: "steward_id",
              label: "Data steward",
              options: people.data?.items.map((p) => ({
                value: String(p.id),
                label: String(p.name),
              })),
            },
            {
              name: "classification",
              label: "Classification",
              options: ["Public", "Internal", "Confidential", "Restricted"].map(
                (v) => ({ value: v, label: v }),
              ),
              required: true,
            },
            {
              name: "criticality",
              label: "Criticality",
              options: ["Standard", "Critical"].map((v) => ({
                value: v,
                label: v,
              })),
            },
            { name: "source_system", label: "Source system", required: true },
            {
              name: "physical_location",
              label: "Physical location",
              required: true,
            },
          ]}
          initial={{ classification: "Internal", criticality: "Standard" }}
          onClose={() => setCreate(false)}
          onSave={async (v) => {
            await api("/assets", "POST", {
              ...v,
              business_domain_id: Number(v.business_domain_id),
              owner_id: v.owner_id ? Number(v.owner_id) : null,
              steward_id: v.steward_id ? Number(v.steward_id) : null,
              asset_type: "Dataset",
            });
            await client.invalidateQueries();
          }}
        />
      )}
    </>
  );
}
