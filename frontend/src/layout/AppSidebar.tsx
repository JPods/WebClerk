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
import { getUI, setUI } from "@/utils/contactUI";
import { useAppSelector } from "../store/hooks";

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
  "layout-parade": Settings,
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
  "layout-parade": "/layout-parade",
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
  "layout-parade": "Layout Parade",
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

  // Read nav config from config.ui.navbar — portal users get a scoped model list
  const user = useAppSelector(s => s.auth.user);
  const isPortal = user?.is_portal === true;
  const portalRoles = user?.roles || [];
  const isCustomer = portalRoles.includes('user_customer');
  const isVendor = portalRoles.includes('user_vendor') || portalRoles.includes('user_manufacturer');

  const PORTAL_CUSTOMER_MODELS = ['invoice', 'order', 'item', 'contact', 'action'];
  const PORTAL_VENDOR_MODELS = ['purchase', 'item', 'contact', 'action'];
  const PORTAL_DASHBOARDS = ['portal', 'kanban', 'gantt'];

  // All available items — superset the user can pick from
  const ALL_MODELS = ['agenda', 'proposal', 'order', 'invoice', 'purchase', 'receipt', 'requisition', 'workorder', 'payment', 'action', 'contact', 'customer', 'vendor', 'manufacturer', 'employee', 'rep', 'item', 'serial', 'setting'];
  const ALL_DASHBOARDS = ['dashboard', 'products', 'transactions', 'orgs', 'administration', 'alice', 'kanban', 'gantt', 'databrowser', 'json', 'accounting', 'flight-simulator'];

  const [editingSection, setEditingSection] = useState<'models' | 'dashboards' | null>(null);
  const [localModels, setLocalModels] = useState<string[]>([]);
  const [localDashboards, setLocalDashboards] = useState<string[]>([]);

  const savedModels: string[] = isPortal
    ? (isCustomer ? PORTAL_CUSTOMER_MODELS : isVendor ? PORTAL_VENDOR_MODELS : ['contact', 'action'])
    : getUI<string[]>('navbar.models', ['agenda', 'proposal', 'order', 'invoice', 'purchase', 'action']);
  const savedDashboards: string[] = isPortal
    ? PORTAL_DASHBOARDS
    : getUI<string[]>('navbar.dashboards', ['dashboard', 'products', 'transactions', 'orgs', 'administration', 'kanban', 'gantt', 'alice', 'databrowser', 'json']);

  const modelNames = editingSection ? localModels : savedModels;
  const dashboardNames = editingSection ? localDashboards : savedDashboards;

  // Sync local state when entering edit mode
  useEffect(() => {
    if (editingSection) {
      setLocalModels(savedModels);
      setLocalDashboards(savedDashboards);
    }
  }, [editingSection]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleItem = (section: 'models' | 'dashboards', name: string) => {
    const setter = section === 'models' ? setLocalModels : setLocalDashboards;
    setter(prev => prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name]);
  };

  const saveNavbar = () => {
    setUI('navbar.models', localModels);
    setUI('navbar.dashboards', localDashboards);
    setEditingSection(null);
  };

  const cancelEdit = () => setEditingSection(null);

  const handleSectionClick = (section: 'models' | 'dashboards', e: React.MouseEvent) => {
    // Option+Cmd+click (Mac) or Alt+Ctrl+click (Win) opens editor
    if (e.altKey && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      setEditingSection(prev => prev === section ? null : section);
    }
  };

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

  const sectionLabel = (text: string, section: 'models' | 'dashboards') =>
    show ? (
      <h2 className="mb-1 mt-4 px-3 text-[10px] uppercase tracking-widest font-semibold cursor-default"
        style={{ color: editingSection === section ? 'var(--wc-nav-text-active)' : 'var(--wc-nav-section)' }}
        onClick={(e) => handleSectionClick(section, e)}
        title="Option+Cmd+click to configure">
        {text}
        {editingSection === section && <span className="ml-1 text-[9px] normal-case tracking-normal" style={{ color: 'var(--wc-nav-text-muted, var(--wc-nav-text))' }}>editing</span>}
      </h2>
    ) : (
      <div className="mt-3 mb-1 mx-3 border-t" style={{ borderColor: 'var(--wc-nav-divider)' }} />
    );

  // Item picker — shows all available items with checkboxes
  const renderPicker = (section: 'models' | 'dashboards') => {
    if (editingSection !== section || !show) return null;
    const allItems = section === 'models' ? ALL_MODELS : ALL_DASHBOARDS;
    const active = section === 'models' ? localModels : localDashboards;
    return (
      <div className="mx-2 mb-2 rounded-lg p-2" style={{ background: 'var(--wc-nav-hover, rgba(255,255,255,0.05))', border: '1px solid var(--wc-nav-divider)' }}>
        <div className="flex flex-wrap gap-1 mb-2">
          {allItems.map(name => {
            const on = active.includes(name);
            return (
              <button key={name}
                onClick={() => toggleItem(section, name)}
                className="px-1.5 py-0.5 rounded text-[10px] font-medium transition-colors"
                style={{
                  background: on ? 'var(--wc-nav-active, #3b82f6)' : 'transparent',
                  color: on ? 'var(--wc-nav-text-active, #fff)' : 'var(--wc-nav-text-muted, var(--wc-nav-text))',
                  border: `1px solid ${on ? 'transparent' : 'var(--wc-nav-divider)'}`,
                }}
              >{displayName(name)}</button>
            );
          })}
        </div>
        <div className="flex gap-1 justify-end">
          <button onClick={cancelEdit} className="px-2 py-0.5 rounded text-[10px]"
            style={{ color: 'var(--wc-nav-text-muted)', border: '1px solid var(--wc-nav-divider)' }}>Cancel</button>
          <button onClick={saveNavbar} className="px-2 py-0.5 rounded text-[10px] font-semibold"
            style={{ background: 'var(--wc-nav-active, #3b82f6)', color: 'var(--wc-nav-text-active, #fff)' }}>Save</button>
        </div>
      </div>
    );
  };

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
        {sectionLabel("Models", "models")}
        {renderPicker("models")}
        {renderItems(modelItems, "models")}

        {sectionLabel("Dashboards", "dashboards")}
        {renderPicker("dashboards")}
        {renderItems(dashboardItems, "dashboards")}
      </nav>
    </aside>
  );
};

export default AppSidebar;
