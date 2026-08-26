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
  Plane,
  type LucideIcon,
} from "lucide-react";
import { useSidebar } from "../context/SidebarContext";
import { PageRoutes } from "@/routes/Routes";
import { useWindowManager } from "../context/WindowManagerContext";
import { getUI } from "@/utils/contactUI";

type NavItem = {
  name: string;
  icon: React.ReactNode;
  path?: string;
  subItems?: { name: string; path: string; new?: boolean }[];
};

// Icon registry — maps model/page names to Lucide icons
const ICON_MAP: Record<string, LucideIcon> = {
  agenda: CalendarRange,
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
  "flight-simulator": Plane,
  "flight-sim": Plane,
  databrowser: Database,
  json: Braces,
  "form-parade": FileText,
  "setting-parade": Settings,
  selectlists: ClipboardList,
};

function iconFor(name: string): React.ReactNode {
  const Icon = ICON_MAP[name.toLowerCase()] || Database;
  return <Icon size={18} />;
}

// Route map — model name to route path
const ROUTE_MAP: Record<string, string> = {
  agenda: "/agenda",
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
  "flight-simulator": "/flight-simulator",
  "flight-sim": "/flight-simulator",
  databrowser: "/databrowser",
  json: "/json-tree",
  adjust: "/inventory-adjust",
  "form-parade": "/form-parade",
  "setting-parade": "/setting-parade",
  selectlists: "/selectlists",
};

function routeFor(name: string): string {
  return ROUTE_MAP[name.toLowerCase()] || `/${name.toLowerCase()}`;
}

// Display names (capitalize, handle special cases)
const DISPLAY_NAMES: Record<string, string> = {
  adjust: "Adjust",
  products: "Products",
  transactions: "Transactions",
  orgs: "Orgs",
  sync: "Sync",
  support: "Support",
  operations: "Operations",
  agenda: "Agenda",
  administration: "Administration",
  databrowser: "databrowser",
  json: "JSON",
  alice: "Alice",
  "flight-simulator": "Flight Sim",
  "flight-sim": "Flight Sim",
  workorder: "Work Order",
  gantt: "Gantt",
  kanban: "Kanban",
  "form-parade": "Form Parade",
  "setting-parade": "Setting Parade",
  selectlists: "Select Lists",
};

function displayName(name: string): string {
  return DISPLAY_NAMES[name.toLowerCase()] || name.charAt(0).toUpperCase() + name.slice(1);
}

// Build NavItem[] from a list of names
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

  // Read nav config from config.ui.navbar
  const modelNames: string[] = getUI<string[]>('navbar.models', ['agenda', 'proposal', 'order', 'invoice', 'purchase', 'action']);
  const dashboardNames: string[] = getUI<string[]>('navbar.dashboards', ['dashboard', 'products', 'transactions', 'orgs', 'administration', 'kanban', 'gantt', 'alice', 'databrowser', 'json']);

  const modelItems = buildItems(modelNames);
  const dashboardItems = buildItems(dashboardNames);

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
              className="sidebar-item"
              style={{
                backgroundColor: openSubmenu?.type === menuType && openSubmenu?.index === index
                  ? 'var(--wc-nav-hover)' : undefined,
                color: openSubmenu?.type === menuType && openSubmenu?.index === index
                  ? 'var(--wc-nav-text-active)' : 'var(--wc-nav-text)',
              }}
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
                className="sidebar-item"
                style={{
                  backgroundColor: isActive(nav.path) ? 'var(--wc-nav-active)' : undefined,
                  color: isActive(nav.path) ? 'var(--wc-nav-text-active)' : 'var(--wc-nav-text)',
                }}
                onClick={(e) => openWindow(nav.path!, nav.name, e.shiftKey)}
                onMouseEnter={(e) => { if (!isActive(nav.path!)) (e.currentTarget.style.backgroundColor = 'var(--wc-nav-hover)'); }}
                onMouseLeave={(e) => { if (!isActive(nav.path!)) (e.currentTarget.style.backgroundColor = ''); }}
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
                      className="sidebar-subitem"
                      style={{
                        color: isActive(sub.path) ? 'var(--wc-nav-text-active)' : 'var(--wc-nav-text-muted, var(--wc-nav-text))',
                        backgroundColor: isActive(sub.path) ? 'var(--wc-nav-hover)' : undefined,
                      }}
                      onClick={(e) => openWindow(sub.path, sub.name, e.shiftKey)}
                    >
                      {sub.name}
                      {sub.new && (
                        <span className="sidebar-badge-new">new</span>
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
      <h2 className="mb-1 mt-4 px-3 text-[10px] uppercase tracking-widest font-semibold"
        style={{ color: 'var(--wc-nav-section)' }}>
        {text}
      </h2>
    ) : (
      <div className="mt-3 mb-1 mx-3 border-t" style={{ borderColor: 'var(--wc-nav-divider)' }} />
    );

  const targetWidth = show ? 200 : 52;
  const translateClass = isVisible ? "translate-x-0" : "-translate-x-full";

  return (
    <aside
      className={`fixed top-[40px] left-0 flex h-[calc(100vh-40px)] flex-col transition-all duration-200 ease-in-out z-50 ${translateClass}`}
      data-zone="NavBar | aside.fixed | AppSidebar.tsx"
      onMouseEnter={() => !isExpanded && setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        pointerEvents: isVisible ? "auto" : "none",
        width: isVisible ? `${targetWidth}px` : 0,
        backgroundColor: 'var(--wc-nav-bg)',
      }}
    >
      {/* Top: branding + collapse */}
      <div className="flex items-center justify-between px-3 py-2 border-b"
        style={{ borderColor: 'var(--wc-nav-divider)' }}>
        {show && (
          <span className="text-sm font-bold tracking-wide" style={{ color: 'var(--wc-nav-text-active)' }}>WC3</span>
        )}
        <button
          onClick={toggleVisibility}
          className="p-1 rounded transition-colors"
          style={{ color: 'var(--wc-nav-text)' }}
          title={isVisible ? "Collapse sidebar" : "Expand sidebar"}
        >
          {show ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
        </button>
      </div>

      {/* Navigation */}
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
