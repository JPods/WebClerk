import { useCallback, useEffect, useRef, useState } from "react";
import {
  LayoutDashboard,
  ShoppingCart,
  FileText,
  Users,
  UserCircle,
  ClipboardList,
  CreditCard,
  Columns3,
  BarChart3,
  CalendarRange,
  Bot,
  Database,
  Package,
  ChevronDown,
  PanelLeftClose,
  PanelLeftOpen,
  Truck,
  Factory,
  Briefcase,
  ScrollText,
  Settings,
  Wrench,
  Receipt,
  CircleDollarSign,
  Braces,
  ArrowLeftRight,
  LifeBuoy,
  type LucideIcon,
} from "lucide-react";
import { useSidebar } from "../context/SidebarContext";
import { PageRoutes } from "@/routes/Routes";
import { useWindowManager } from "../context/WindowManagerContext";
import { useSelector } from "react-redux";
import type { RootState } from "@/store";

type NavItem = {
  name: string;
  icon: React.ReactNode;
  path?: string;
  subItems?: { name: string; path: string; new?: boolean }[];
};

// ─── Icon registry — maps model/page names to Lucide icons ───────────
const ICON_MAP: Record<string, LucideIcon> = {
  contact: UserCircle,
  customer: Users,
  vendor: Truck,
  manufacturer: Factory,
  employee: Briefcase,
  rep: Briefcase,
  proposal: ClipboardList,
  order: ShoppingCart,
  invoice: FileText,
  purchase: CreditCard,
  receipt: Receipt,
  requisition: ScrollText,
  work_order: Wrench,
  workorder: Wrench,
  item: Package,
  products: Package,
  transactions: ShoppingCart,
  orgs: Users,
  sync: ArrowLeftRight,
  support: LifeBuoy,
  operations: Settings,
  administration: Settings,
  serial: Package,
  action: ClipboardList,
  setting: Settings,
  payment: CircleDollarSign,
  // Dashboards / pages
  dashboard: LayoutDashboard,
  kanban: Columns3,
  gantt: CalendarRange,
  accounting: BarChart3,
  alice: Bot,
  databrowser: Database,
  json: Braces,
};

function iconFor(name: string): React.ReactNode {
  const Icon = ICON_MAP[name.toLowerCase()] || Database;
  return <Icon size={18} />;
}

// ─── Route map — model name to route path ────────────────────────────
const ROUTE_MAP: Record<string, string> = {
  dashboard: "/dashboard",
  kanban: "/kanban",
  gantt: PageRoutes.gantt,
  products: "/products",
  transactions: "/transactions",
  orgs: "/orgs",
  sync: "/operations?tab=sync",
  support: "/operations?tab=support",
  accounting: "/operations?tab=accounting",
  operations: "/operations",
  administration: "/administration",
  alice: "/alice-dashboard",
  databrowser: "/databrowser",
  json: "/json-tree",
  adjust: "/inventory-adjust",
};

function routeFor(name: string): string {
  return ROUTE_MAP[name.toLowerCase()] || `/${name.toLowerCase()}`;
}

// ─── Defaults (used when user has no prefs.nav) ──────────────────────
const DEFAULT_MODELS = ["contact", "customer", "proposal", "order", "invoice", "purchase"];
const DEFAULT_DASHBOARDS = ["dashboard", "products", "transactions", "orgs", "administration", "kanban", "gantt", "alice", "databrowser", "json"];

// ─── Display names (capitalize, handle special cases) ────────────────
const DISPLAY_NAMES: Record<string, string> = {
  adjust: "Adjust",
  products: "Products",
  transactions: "Transactions",
  orgs: "Orgs",
  sync: "Sync",
  support: "Support",
  operations: "Operations",
  administration: "Administration",
  databrowser: "databrowser",
  json: "JSON",
  alice: "Alice",
  work_order: "Work Order",
  gantt: "Gantt",
  kanban: "Kanban",
};

function displayName(name: string): string {
  return DISPLAY_NAMES[name.toLowerCase()] || name.charAt(0).toUpperCase() + name.slice(1);
}

// ─── Build NavItem[] from a list of names ────────────────────────────
function buildItems(names: string[]): NavItem[] {
  return names.map(name => ({
    name: displayName(name),
    icon: iconFor(name),
    path: routeFor(name),
  }));
}

const AppSidebar: React.FC = () => {
  const {
    isExpanded,
    isMobileOpen,
    isHovered,
    isVisible,
    setIsHovered,
    toggleVisibility,
  } = useSidebar();
  const { ensureWindow, activateWindow, activePath } = useWindowManager();
  const authUser = useSelector((s: RootState) => s.auth?.user);

  // Read nav prefs from user's contact record (prefs.staff.nav or legacy prefs.nav)
  const staffPrefs = (authUser as any)?.prefs?.staff;
  const navPrefs = staffPrefs?.nav || (authUser as any)?.prefs?.nav;
  const modelNames: string[] = navPrefs?.models || DEFAULT_MODELS;
  const dashboardNames: string[] = navPrefs?.dashboards || DEFAULT_DASHBOARDS;

  const modelItems = buildItems(modelNames);
  const dashboardItems = buildItems(dashboardNames);
  console.log('[AppSidebar] dashboardNames:', dashboardNames, 'from prefs:', !!navPrefs?.dashboards);

  const [openSubmenu, setOpenSubmenu] = useState<{
    type: string;
    index: number;
  } | null>(null);
  const [subMenuHeight, setSubMenuHeight] = useState<Record<string, number>>({});
  const subMenuRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const isActive = useCallback(
    (path: string) => activePath === path,
    [activePath],
  );

  useEffect(() => {
    if (openSubmenu !== null) {
      const key = `${openSubmenu.type}-${openSubmenu.index}`;
      if (subMenuRefs.current[key]) {
        setSubMenuHeight((prev) => ({
          ...prev,
          [key]: subMenuRefs.current[key]?.scrollHeight || 0,
        }));
      }
    }
  }, [openSubmenu]);

  const handleSubmenuToggle = (index: number, menuType: string) => {
    setOpenSubmenu((prev) =>
      prev && prev.type === menuType && prev.index === index
        ? null
        : { type: menuType, index },
    );
  };

  const openWindow = (path: string, title: string, shiftKey?: boolean) => {
    if (shiftKey && !path.startsWith("/databrowser")) {
      const segments = path.replace(/^\//, "").split("/");
      const modelGuess =
        segments.length >= 2 ? segments[segments.length - 2] : segments[0];
      const dbPath = `/${modelGuess}`;
      ensureWindow(dbPath, `DB: ${title}`);
      activateWindow(dbPath);
      return;
    }
    ensureWindow(path, title);
    activateWindow(path);
  };

  const show = isExpanded || isHovered || isMobileOpen;

  const renderItems = (items: NavItem[], menuType: string) => (
    <ul className="flex flex-col gap-0.5">
      {items.map((nav, index) => (
        <li key={nav.name}>
          {nav.subItems ? (
            <button
              onClick={() => handleSubmenuToggle(index, menuType)}
              className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                openSubmenu?.type === menuType && openSubmenu?.index === index
                  ? "bg-white/10 text-white"
                  : "text-slate-300 hover:bg-white/5 hover:text-white"
              }`}
            >
              <span className="flex-shrink-0">{nav.icon}</span>
              {show && <span className="flex-1 text-left">{nav.name}</span>}
              {show && (
                <ChevronDown
                  size={14}
                  className={`transition-transform duration-200 ${
                    openSubmenu?.type === menuType && openSubmenu?.index === index
                      ? "rotate-180"
                      : ""
                  }`}
                />
              )}
            </button>
          ) : (
            nav.path && (
              <button
                className={`flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive(nav.path)
                    ? "bg-blue-600 text-white"
                    : "text-slate-300 hover:bg-white/5 hover:text-white"
                }`}
                onClick={(e) => openWindow(nav.path!, nav.name, e.shiftKey)}
              >
                <span className="flex-shrink-0">{nav.icon}</span>
                {show && <span>{nav.name}</span>}
              </button>
            )
          )}
          {nav.subItems && show && (
            <div
              ref={(el) => {
                subMenuRefs.current[`${menuType}-${index}`] = el;
              }}
              className="overflow-hidden transition-all duration-200"
              style={{
                height:
                  openSubmenu?.type === menuType && openSubmenu?.index === index
                    ? `${subMenuHeight[`${menuType}-${index}`]}px`
                    : "0px",
              }}
            >
              <ul className="mt-0.5 space-y-0.5 pl-9">
                {nav.subItems.map((sub) => (
                  <li key={sub.name}>
                    <button
                      className={`flex w-full items-center rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                        isActive(sub.path)
                          ? "text-white bg-white/10"
                          : "text-slate-400 hover:text-white hover:bg-white/5"
                      }`}
                      onClick={(e) => openWindow(sub.path, sub.name, e.shiftKey)}
                    >
                      {sub.name}
                      {sub.new && (
                        <span className="ml-auto rounded-full bg-blue-500/20 px-1.5 py-0.5 text-[9px] font-semibold text-blue-300">
                          new
                        </span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </li>
      ))}
    </ul>
  );

  const sectionLabel = (text: string) =>
    show ? (
      <h2 className="mb-1 mt-4 px-3 text-[10px] uppercase tracking-widest font-semibold text-slate-500">
        {text}
      </h2>
    ) : (
      <div className="mt-3 mb-1 mx-3 border-t border-slate-700" />
    );

  const targetWidth = show ? 200 : 52;
  const translateClass = isVisible ? "translate-x-0" : "-translate-x-full";

  return (
    <aside
      className={`fixed top-[40px] left-0 flex h-[calc(100vh-40px)] flex-col bg-slate-900 transition-all duration-200 ease-in-out z-50 ${translateClass}`}
      data-zone="NavBar | aside.fixed | AppSidebar.tsx"
      onMouseEnter={() => !isExpanded && setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        pointerEvents: isVisible ? "auto" : "none",
        width: isVisible ? `${targetWidth}px` : 0,
      }}
    >
      {/* Top: branding + collapse */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-slate-700/50">
        {show && (
          <span className="text-sm font-bold text-white tracking-wide">WC3</span>
        )}
        <button
          onClick={toggleVisibility}
          className="p-1 rounded text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          title={isVisible ? "Collapse sidebar" : "Expand sidebar"}
        >
          {show ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
        </button>
      </div>

      {/* Navigation — fills all available space */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden py-2 px-2">
        {sectionLabel("Models")}
        {renderItems(modelItems, "models")}

        {sectionLabel("Dashboards")}
        {renderItems(dashboardItems, "dashboards")}
      </nav>
    </aside>
  );
};

export default AppSidebar;
