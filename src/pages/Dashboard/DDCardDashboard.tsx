/**
 * DDCardDashboard — Generic data-driven dashboard
 *
 * Reads its config from the dd_card:base Setting record.
 * Renders DDCard summary cards + a real DataBrowser instance.
 * Replaces all boilerplate dashboard pages with one component.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getRecords } from "@/api/wcapi";
import { useAppSelector } from "@/store/hooks";
import DDCard, { type DDCardConfig } from "@/components/common/DDCard";
import DataBrowser from "@/pages/admin/DataBrowser";
import "@/pages/admin/DataBrowser.css";

type ThemeKey = "dark" | "light";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface QuickAdd {
  label: string;
  to: string;
  accent: string;
}

interface DashboardConfig {
  label: string;
  route: string;
  cards: string[];
  default_model: string;
  quick_adds?: QuickAdd[];
}

interface DDCardBaseConfig {
  cards: Record<string, DDCardConfig>;
  dashboards: Record<string, DashboardConfig>;
}

// Accent color map — Tailwind classes
const ACCENT_MAP: Record<string, string> = {
  blue: "bg-blue-600 text-white",
  indigo: "bg-indigo-600 text-white",
  emerald: "bg-emerald-600 text-white",
  amber: "bg-amber-600 text-white",
  purple: "bg-purple-600 text-white",
  teal: "bg-teal-600 text-white",
  rose: "bg-rose-600 text-white",
  orange: "bg-orange-600 text-white",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DDCardDashboard({ dashboardName }: { dashboardName: string }) {
  const { user } = useAppSelector((s) => s.auth);
  const [baseConfig, setBaseConfig] = useState<DDCardBaseConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [theme, setTheme] = useState<ThemeKey>(() => (localStorage.getItem("db-theme") as ThemeKey) || "dark");

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await getRecords("setting", {
          purpose: "wc:dd_card",
          name: "dd_card:base",
          limit: 1,
        });
        const record = res?.results?.[0];
        if (mounted && record?.config) {
          setBaseConfig(record.config as DDCardBaseConfig);
        }
      } catch {
        // Setting not seeded — dashboard shows empty
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, []);

  // Stay in sync with theme toggles from DataBrowser
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent)?.detail;
      setTheme(detail?.theme || (localStorage.getItem("db-theme") as ThemeKey) || "dark");
    };
    window.addEventListener("wc3-theme-changed", handler);
    return () => window.removeEventListener("wc3-theme-changed", handler);
  }, []);

  if (loading) {
    return <div style={{ padding: 20, color: "var(--db-text-muted, #888)" }}>Loading dashboard…</div>;
  }

  if (!baseConfig) {
    return <div style={{ padding: 20, color: "var(--db-text-muted, #888)" }}>Dashboard config not found. Run: manage.py seed_dd_cards</div>;
  }

  const dashboard = baseConfig.dashboards[dashboardName];
  if (!dashboard) {
    return <div style={{ padding: 20, color: "var(--db-text-muted, #888)" }}>Dashboard "{dashboardName}" not defined in dd_card:base</div>;
  }

  // User's card selection from prefs.staff.nav.cards — falls back to dashboard default
  const staffPrefs = (user as any)?.prefs?.staff;
  const userCards: string[] | undefined = staffPrefs?.nav?.cards;
  // Support both flat 'cards' array and nested 'rows' array-of-arrays
  const dashboardCards = dashboard.cards ?? ((dashboard as any).rows?.flat() as string[]) ?? [];
  const cardNames = userCards ?? dashboardCards;

  const cardConfigs = cardNames
    .map((name) => ({ name, config: baseConfig.cards[name] }))
    .filter((c) => c.config);

  const quickAdds = dashboard.quick_adds || [];

  return (
    <div className="db-root flex h-full flex-col" data-theme={theme} style={{ overflow: "hidden", background: "var(--db-bg)", color: "var(--db-text)" }}>
      {/* Header: title + quick adds */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "6px 8px",
        borderBottom: "1px solid var(--db-border)",
        flexShrink: 0,
      }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--db-text)" }}>
          {dashboard.label}
        </span>
        {quickAdds.length > 0 && (
          <div className="flex gap-1.5">
            {quickAdds.map((qa) => (
              <Link
                key={qa.label}
                to={qa.to}
                className={`rounded px-2 py-0.5 text-[10px] font-semibold shadow-sm transition hover:-translate-y-[1px] hover:shadow-md ${ACCENT_MAP[qa.accent] || "bg-slate-600 text-white"}`}
              >
                {qa.label}
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Cards row */}
      <div style={{
        display: "flex",
        gap: 6,
        padding: "6px 8px",
        overflowX: "auto",
        flexShrink: 0,
      }}>
        {cardConfigs.map((c) => (
          <DDCard key={c.name} model={c.name} config={c.config} />
        ))}
      </div>

      {/* DataBrowser — standard db.list */}
      <div className="min-h-0 flex-1">
        <DataBrowser defaultModel={dashboard.default_model} />
      </div>
    </div>
  );
}
