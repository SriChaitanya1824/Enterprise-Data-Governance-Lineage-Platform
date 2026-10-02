import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Database,
  Fingerprint,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";
import {
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { api } from "../services/api";
import type { DashboardData } from "../types";
import { Heading, State } from "../components/Common";
const colors = [
  "#285d73",
  "#75a6a5",
  "#d7ad65",
  "#b86356",
  "#8d9fb6",
  "#c3d4df",
];
function Distribution({
  title,
  data,
}: {
  title: string;
  data: Record<string, number>;
}) {
  const rows = Object.entries(data).map(([name, value]) => ({ name, value }));
  return (
    <section className="panel chart-panel">
      <h3>{title}</h3>
      <div className="distribution">
        <ResponsiveContainer width="55%" height={170}>
          <PieChart>
            <Pie
              data={rows}
              dataKey="value"
              innerRadius={48}
              outerRadius={68}
              paddingAngle={3}
            >
              {rows.map((_, i) => (
                <Cell key={i} fill={colors[i % colors.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
        <div className="legend">
          {rows.map((r, i) => (
            <div key={r.name}>
              <i style={{ background: colors[i % colors.length] }} />
              <span>{r.name}</span>
              <b>{r.value}</b>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
export function Dashboard() {
  const query = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => api<DashboardData>("/dashboard"),
  });
  const d = query.data;
  return (
    <>
      <Heading
        eyebrow="GOVERNANCE INTELLIGENCE / OVERVIEW"
        title="Governance overview"
        description="Understand your data estate. Identify gaps. Maintain regulatory traceability."
        action={
          <Link className="button primary" to="/cdes">
            Explore critical data <ArrowUpRight size={15} />
          </Link>
        }
      />
      <State loading={query.isLoading} error={query.error} />
      {d && (
        <>
          <div className="notice">
            <ShieldCheck size={18} />
            <span>Synthetic enterprise environment</span>
            <p>
              Metrics are calculated from catalog records, control executions
              and observed quality results.
            </p>
            <span className="live-dot">Live database</span>
          </div>
          <div className="stats-grid">
            {[
              {
                label: "Registered data assets",
                value: d.total_assets,
                icon: Database,
                sub: `${d.governed_assets} with governance metadata`,
              },
              {
                label: "Critical data elements",
                value: d.cdes,
                icon: Fingerprint,
                sub: "Field-level accountability & traceability",
              },
              {
                label: "Open governance exceptions",
                value: d.open_exceptions,
                icon: AlertTriangle,
                sub: `${d.overdue_exceptions} overdue · ${d.missing_ownership} missing owners`,
              },
              {
                label: "Observed data quality",
                value:
                  d.average_quality === null
                    ? "Unmeasured"
                    : `${d.average_quality}%`,
                icon: ShieldCheck,
                sub: `Measured across ${d.quality_coverage} assets`,
              },
            ].map((s) => (
              <section className="stat" key={s.label}>
                <div>
                  {s.label}
                  <s.icon size={18} />
                </div>
                <strong>{s.value}</strong>
                <small>{s.sub}</small>
              </section>
            ))}
          </div>
          <div className="dashboard-main">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h3>Governance adoption by division</h3>
                  <p>Coverage across seven governance requirements</p>
                </div>
                <span className="score">
                  {d.adoption_score}% <small>overall</small>
                </span>
              </div>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={d.adoption}
                  layout="vertical"
                  margin={{ left: 0, right: 30 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis
                    type="number"
                    domain={[0, 100]}
                    tickFormatter={(v) => `${v}%`}
                    fontSize={11}
                  />
                  <YAxis
                    type="category"
                    dataKey="domain"
                    width={130}
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip />
                  <Bar
                    dataKey="adoption_score"
                    name="Adoption"
                    fill="#285d73"
                    radius={[0, 4, 4, 0]}
                    barSize={18}
                  />
                </BarChart>
              </ResponsiveContainer>
              <Link className="text-link" to="/adoption">
                View division assessment →
              </Link>
            </section>
            <section className="panel attention">
              <h3>Priority governance gaps</h3>
              <p>Focus on accountability and regulatory traceability.</p>
              <Link to="/assets">
                <div className="gap-icon">01</div>
                <div>
                  <b>{d.missing_ownership} assets missing ownership</b>
                  <small>Assign an accountable data owner</small>
                </div>
                <ArrowUpRight size={17} />
              </Link>
              <Link to="/lineage">
                <div className="gap-icon">02</div>
                <div>
                  <b>{d.missing_lineage} assets without lineage</b>
                  <small>Document source and consumption paths</small>
                </div>
                <ArrowUpRight size={17} />
              </Link>
              <Link to="/exceptions">
                <div className="gap-icon">03</div>
                <div>
                  <b>{d.open_exceptions} exceptions require action</b>
                  <small>Remediate, submit evidence and review</small>
                </div>
                <ArrowUpRight size={17} />
              </Link>
              <div className="demo-callout">
                <small>FEATURED TRACEABILITY SCENARIO</small>
                <b>Customer Risk Rating</b>
                <p>Source → CDE → risk analytics → regulatory report</p>
                <Link to="/cdes">Inspect governance profile →</Link>
              </div>
            </section>
          </div>
          <div className="chart-grid">
            <Distribution title="Exception status" data={d.exception_status} />
            <Distribution
              title="Exception severity"
              data={d.exception_severity}
            />
            <Distribution
              title="Data-quality rule results"
              data={d.quality_results}
            />
            <Distribution
              title="Assets by division"
              data={d.assets_by_domain}
            />
            <Distribution
              title="Lineage coverage"
              data={d.lineage_completeness}
            />
          </div>
        </>
      )}
    </>
  );
}
