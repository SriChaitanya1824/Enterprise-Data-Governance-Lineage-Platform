import { useEffect, useState } from "react";
import {
  NavLink,
  Navigate,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  BookOpen,
  Boxes,
  Database,
  FileCheck,
  Fingerprint,
  GitBranch,
  LayoutDashboard,
  LogOut,
  Search,
  ShieldCheck,
  Users,
  ClipboardList,
  Menu,
  ArrowUpRight,
} from "lucide-react";
import { api, hasToken, login, setToken } from "./services/api";
import type { Person } from "./types";
import { Dashboard } from "./pages/Dashboard";
import { Catalog } from "./pages/Catalog";
import { AssetDetail } from "./pages/AssetDetail";
import { Glossary } from "./pages/Glossary";
import { Lineage } from "./pages/Lineage";
import { Exceptions } from "./pages/Exceptions";
import { AdoptionPage, Operations } from "./pages/Operations";
const navigation = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard },
  { label: "Data Catalog", path: "/assets", icon: Database },
  { label: "Critical Data Elements", path: "/cdes", icon: Fingerprint },
  { label: "Business Glossary", path: "/business-terms", icon: BookOpen },
  { label: "Lineage Explorer", path: "/lineage", icon: GitBranch },
  { label: "Data Quality", path: "/quality", icon: Activity },
  { label: "Governance Controls", path: "/controls", icon: ShieldCheck },
  { label: "Exceptions", path: "/exceptions", icon: ClipboardList },
  { label: "Evidence", path: "/evidence", icon: FileCheck },
  { label: "Adoption", path: "/adoption", icon: Boxes },
  { label: "Audit Log", path: "/audit", icon: ClipboardList },
  { label: "Administration", path: "/admin", icon: Users },
];
function Login({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState("governance_analyst@example.test");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="login-screen">
      <div className="login-story">
        <div className="brand">
          <ShieldCheck size={30} />
          <div>
            Enterprise Data Office<small>GOVERNANCE & LINEAGE PLATFORM</small>
          </div>
        </div>
        <div>
          <span className="eyebrow">ACCOUNTABILITY. TRACEABILITY. TRUST.</span>
          <h1>
            Know your data.
            <br />
            Govern with evidence.
          </h1>
          <p>
            Connect critical data elements to their owners, quality controls and
            regulatory reporting paths.
          </p>
          <div className="login-path">
            Source data <span>→</span> Critical element <span>→</span>{" "}
            Regulatory report
          </div>
        </div>
        <small>Synthetic financial data · Portfolio demonstration</small>
      </div>
      <section className="login-form">
        <h2>Sign in to your data office</h2>
        <p>
          Use a seeded role account and the locally generated bootstrap
          password.
        </p>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            try {
              await login(email, password);
              onLogin();
            } catch (err) {
              setError((err as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            Email address
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && (
            <div role="alert" className="error">
              {error}
            </div>
          )}
          <button className="primary" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"} <ArrowUpRight size={16} />
          </button>
        </form>
        <p className="muted">
          Credentials are generated into your untracked .env file during setup.
        </p>
      </section>
    </div>
  );
}
export default function App() {
  const [signedIn, setSignedIn] = useState(hasToken());
  const [mobile, setMobile] = useState(false);
  const [search, setSearch] = useState("");
  const navigate = useNavigate();
  const client = useQueryClient();
  const user = useQuery({
    queryKey: ["me"],
    queryFn: () => api<Person>("/auth/me"),
    enabled: signedIn,
    retry: false,
  });
  const results = useQuery({
    queryKey: ["search", search],
    queryFn: () =>
      api<{ items: { id: number; name: string; type: string }[] }>(
        `/search?q=${encodeURIComponent(search)}`,
      ),
    enabled: signedIn && search.length >= 2,
  });
  useEffect(() => {
    const expire = () => {
      setSignedIn(false);
      client.clear();
    };
    window.addEventListener("session-expired", expire);
    return () => window.removeEventListener("session-expired", expire);
  }, [client]);
  if (!signedIn)
    return (
      <Login
        onLogin={() => {
          setSignedIn(true);
          client.invalidateQueries();
        }}
      />
    );
  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <div className="brand">
          <ShieldCheck size={30} />
          <div>
            Enterprise<small>DATA OFFICE</small>
          </div>
        </div>
        <div className="workspace-label">GOVERNANCE WORKSPACE</div>
        <nav>
          {navigation.map((n) => (
            <NavLink
              key={n.path}
              to={n.path}
              end={n.path === "/"}
              onClick={() => setMobile(false)}
            >
              <n.icon size={17} />
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="env-label">
            <span />
            Synthetic banking environment
          </div>
          <small>Governance & Lineage Platform · v1.0</small>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <button
            className="mobile-toggle"
            aria-label="Open navigation"
            onClick={() => setMobile(!mobile)}
          >
            <Menu size={20} />
          </button>
          <div className="global-search">
            <Search size={17} />
            <input
              aria-label="Global search"
              placeholder="Search assets, terms, owners and exceptions…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {search.length >= 2 && (
              <div className="search-results">
                {results.data?.items.map((r) => (
                  <button
                    key={`${r.type}-${r.id}`}
                    onClick={() => {
                      navigate(
                        [
                          "assets",
                          "cdes",
                          "business-terms",
                          "exceptions",
                        ].includes(r.type)
                          ? `/${r.type}/${r.id}`
                          : "/admin",
                      );
                      setSearch("");
                    }}
                  >
                    <span>{r.name}</span>
                    <small>{r.type}</small>
                  </button>
                ))}
                {results.data?.items.length === 0 && (
                  <p>No matching records.</p>
                )}
              </div>
            )}
          </div>
          <div className="user-info">
            <span className="avatar">{user.data?.name.slice(0, 1) || "G"}</span>
            <div>
              <b>{user.data?.name}</b>
              <small>{user.data?.role.replaceAll("_", " ")}</small>
            </div>
            <button
              aria-label="Sign out"
              onClick={() => {
                setToken(null);
                client.clear();
                setSignedIn(false);
              }}
            >
              <LogOut size={17} />
            </button>
          </div>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/assets" element={<Catalog />} />
            <Route path="/assets/:id" element={<AssetDetail />} />
            <Route path="/cdes" element={<Catalog cdes />} />
            <Route path="/cdes/:id" element={<AssetDetail cde />} />
            <Route path="/business-terms" element={<Glossary />} />
            <Route path="/business-terms/:id" element={<Glossary />} />
            <Route path="/lineage" element={<Lineage />} />
            <Route path="/exceptions" element={<Exceptions />} />
            <Route path="/exceptions/:id" element={<Exceptions />} />
            <Route path="/adoption" element={<AdoptionPage />} />
            {["quality", "controls", "evidence", "audit", "admin"].map(
              (kind) => (
                <Route
                  key={kind}
                  path={`/${kind}`}
                  element={<Operations kind={kind} />}
                />
              ),
            )}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <footer>
          Enterprise Data Governance & Lineage Platform{" "}
          <span>Synthetic data · Evidence-based governance</span>
        </footer>
      </div>
    </div>
  );
}
