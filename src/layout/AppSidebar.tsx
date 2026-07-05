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
} from "lucide-react";
import { useSidebar } from "../context/SidebarContext";
import { PageRoutes } from "@/routes/Routes";
import { useWindowManager } from "../context/WindowManagerContext";

type NavItem = {
  name: string;
  icon: React.ReactNode;
  path?: string;
  subItems?: { name: string; path: string; new?: boolean }[];
};

// ─── Work ───────────────────────────────────────────────
const workItems: NavItem[] = [
  { icon: <LayoutDashboard size={18} />, name: "Dashboard", path: "/dashboard" },
  { icon: <Columns3 size={18} />, name: "Kanban", path: "/kanban-board" },
  { icon: <CalendarRange size={18} />, name: "Gantt", path: PageRoutes.gantt },
];

// ─── Forms ──────────────────────────────────────────────
const formItems: NavItem[] = [
  { icon: <UserCircle size={18} />, name: "Contact", path: "/core/contact/list" },
  { icon: <Users size={18} />, name: "Customer", path: "/org/customer/list" },
  { icon: <ClipboardList size={18} />, name: "Proposal", path: "/transactions/proposal/list" },
  { icon: <ShoppingCart size={18} />, name: "Order", path: "/transactions/order/list" },
  { icon: <FileText size={18} />, name: "Invoice", path: "/transactions/invoice/list" },
  { icon: <CreditCard size={18} />, name: "Purchase", path: "/transactions/purchase/list" },
];

// ─── Dashboards ─────────────────────────────────────────
const dashboardItems: NavItem[] = [
  { icon: <Package size={18} />, name: "Products", path: "/inventory-dashboard" },
  { icon: <BarChart3 size={18} />, name: "Accounting", path: "/accounting" },
  { icon: <Bot size={18} />, name: "Alice", path: "/alice-dashboard" },
  { icon: <Database size={18} />, name: "DataBrowser", path: "/admin-wb" },
];

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
    if (shiftKey && !path.startsWith("/admin-wb")) {
      const segments = path.replace(/^\//, "").split("/");
      const modelGuess =
        segments.length >= 2 ? segments[segments.length - 2] : segments[0];
      const dbPath = `/admin-wb?model=${modelGuess}`;
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
      className={`fixed top-[60px] left-0 flex h-[calc(100vh-60px)] flex-col bg-slate-900 transition-all duration-200 ease-in-out z-50 ${translateClass}`}
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
        {sectionLabel("Work")}
        {renderItems(workItems, "work")}

        {sectionLabel("Forms")}
        {renderItems(formItems, "forms")}

        {sectionLabel("Dashboards")}
        {renderItems(dashboardItems, "dashboards")}
      </nav>
    </aside>
  );
};

export default AppSidebar;
