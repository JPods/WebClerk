/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useCallback, useEffect, useRef, useState } from "react";

// Assume these icons are imported from an icon library
import {
  CalenderIcon,
  ChevronDownIcon,
  GridIcon,
  HorizontaLDots,
  UserCircleIcon,
} from "../icons";
import { useSidebar } from "../context/SidebarContext";
import { PageRoutes } from "@/routes/Routes";
import { useWindowManager } from "../context/WindowManagerContext";
//import SidebarWidget from "./SidebarWidget";

type NavItem = {
  name: string;
  icon: React.ReactNode;
  path?: string;
  subItems?: { name: string; path: string; pro?: boolean; new?: boolean }[];
};

const keyModelNavItems: NavItem[] = [
  {
    icon: <GridIcon />,
    name: "Contact",
    path: "/core/contact/list",
  },
  {
    icon: <GridIcon />,
    name: "Customer",
    path: "/org/customer/list",
  },
  {
    icon: <GridIcon />,
    name: "Order",
    path: "/transactions/order/list",
  },
];

const navItems: NavItem[] = [
  // {
  //   icon: <CalenderIcon />,
  //   name: "Calendar",
  //   path: "/calendar",
  // },
  {
    icon: <GridIcon />,
    name: "Dashboard",
    path: "/dashboard",
  },
  {
    icon: <GridIcon />,
    name: "Kanban Board",
    path: "/kanban-board",
  },
  // moved to bottom
  {
    icon: <GridIcon />,
    name: "Accounts",
    subItems: [
      { name: "Audit", path: "/admin-wb?model=audit" },
      { name: "Currency", path: "/admin-wb?model=currency" },
      { name: "Exchange Rate", path: "/admin-wb?model=exchange_rate" },
      { name: "Exchange Transaction", path: "/admin-wb?model=exchange_transaction" },
      { name: "GL Account", path: "/admin-wb?model=gl_account" },
      { name: "GL Journal", path: "/admin-wb?model=gl_journal" },
      { name: "Ledger", path: "/admin-wb?model=ledger" },
      { name: "Tax Jurisdiction", path: "/admin-wb?model=tax_jurisdiction" },
      { name: "Term", path: "/admin-wb?model=term" },
    ],
  },
  {
    icon: <GridIcon />,
    name: "Core",
    subItems: [
      { name: "Action", path: PageRoutes.actionList },
      { name: "Contact", path: PageRoutes.coreContactList },
      { name: "Notification", path: "/admin-wb?model=notification" },
      { name: "Report", path: "/admin-wb?model=report" },
      { name: "Setting", path: "/admin-wb?model=setting" },
      { name: "Template", path: "/admin-wb?model=template" },
    ],
  },
  {
    icon: <GridIcon />,
    name: "Communications",
    subItems: [
      { name: "Address", path: "/admin-wb?model=address" },
      { name: "Domain", path: "/admin-wb?model=domain" },
      { name: "Email", path: "/admin-wb?model=email" },
      { name: "Phone", path: "/admin-wb?model=phone" },
    ],
  },
  {
    icon: <GridIcon />,
    name: "Docs",
    subItems: [
      { name: "Document", path: "/admin-wb?model=document" },
      { name: "Question Answer", path: "/admin-wb?model=question_answer" },
      { name: "Tag", path: "/admin-wb?model=tag" },
    ],
  },
  {
    icon: <GridIcon />,
    name: "Orgs",
    subItems: [
      { name: "Customer", path: "/org/customer" },
      { name: "Vendor", path: "/org/vendor" },
      { name: "Employee", path: "/org/employee" },
      { name: "Rep", path: "/org/rep" },
      { name: "Manufacturer", path: "/org/manufacturer" },
    ],
  },
  {
    icon: <GridIcon />,
    name: "Products",
    subItems: [
      { name: "Items", path: PageRoutes.productsItemList },
      { name: "Bill Of Material", path: "/admin-wb?model=bill_of_material" },
      { name: "Catalog", path: "/admin-wb?model=catalog" },
      { name: "Org Item", path: "/admin-wb?model=org_item" },
      { name: "Serial", path: "/admin-wb?model=serial_log" },
      { name: "Service", path: "/admin-wb?model=service" },
      { name: "Variant", path: "/admin-wb?model=variant" },
      { name: "Warehouse", path: "/admin-wb?model=warehouse" },
      { name: "Item XRef", path: "/admin-wb?model=item_xref" },
    ],
  },
  {
    icon: <GridIcon />,
    name: "Transactions",
    subItems: [
      { name: "Orders", path: PageRoutes.transactionsOrderList },
      { name: "Invoices", path: PageRoutes.transactionsInvoiceList },
      { name: "Proposals", path: PageRoutes.transactionsProposalList },
      { name: "Purchases", path: PageRoutes.transactionsPurchaseList },
      { name: "Work Orders", path: PageRoutes.transactionsWorkOrderList },
      { name: "Receipts", path: PageRoutes.transactionsReceiptList },
      { name: "Adjustments", path: PageRoutes.transactionsAdjustmentList },
      { name: "Payments", path: PageRoutes.transactionsPaymentList },
      { name: "Apply Payments", path: PageRoutes.transactionsApplyPayments },
    ],
  },
  {
    icon: <GridIcon />,
    name: "DataBrowser",
    path: "/admin-wb",
  },
  {
    icon: <GridIcon />,
    name: "Accounting",
    path: "/accounting",
  },
  {
    icon: <GridIcon />,
    name: "Alice Training",
    path: "/training",
  },
  {
    icon: <GridIcon />,
    name: "CycleDetails",
    path: PageRoutes.detailReview,
  },
  {
    icon: <GridIcon />,
    name: "Whitelist Tester",
    path: "/whitelist",
  },
  {
    icon: <UserCircleIcon />,
    name: "User Profile",
    path: "/profile",
  },
  {
    icon: <GridIcon />,
    name: "Alice Dashboard",
    path: "/alice-dashboard",
  },
  {
    icon: <GridIcon />,
    name: "Submit for Bonus",
    path: "/submit-bonus",
  },
  {
    icon: <CalenderIcon />,
    name: "Gantt",
    path: PageRoutes.gantt,
  },
  // {
  //   name: "Pages",
  //   icon: <PageIcon />,
  //   subItems: [
  //     { name: "Blank Page", path: "/blank", pro: false },
  //     { name: "404 Error", path: "/error-404", pro: false },
  //   ],
  // },
];

// const othersItems: NavItem[] = [
//   {
//     icon: <PieChartIcon />,
//     name: "Charts",
//     subItems: [
//       { name: "Line Chart", path: "/line-chart", pro: false },
//       { name: "Bar Chart", path: "/bar-chart", pro: false },
//     ],
//   },
//   {
//     icon: <BoxCubeIcon />,
//     name: "UI Elements",
//     subItems: [
//       { name: "Alerts", path: "/alerts", pro: false },
//       { name: "Avatar", path: "/avatars", pro: false },
//       { name: "Badge", path: "/badge", pro: false },
//       { name: "Buttons", path: "/buttons", pro: false },
//       { name: "Images", path: "/images", pro: false },
//       { name: "Videos", path: "/videos", pro: false },
//     ],
//   },
//   {
//     icon: <PlugInIcon />,
//     name: "Authentication",
//     subItems: [
//       { name: "Sign In", path: "/signin", pro: false },
//       { name: "Sign Up", path: "/signup", pro: false },
//     ],
//   },
// ];

const AppSidebar: React.FC = () => {
  const {
    isExpanded,
    isMobileOpen,
    isHovered,
    isVisible,
    setIsHovered,
    toggleSidebar,
    toggleVisibility,
  } = useSidebar();
  const { ensureWindow, activateWindow, activePath } = useWindowManager();

  const [openSubmenu, setOpenSubmenu] = useState<{
    type: "main" | "others";
    index: number;
  } | null>(null);
  const [subMenuHeight, setSubMenuHeight] = useState<Record<string, number>>(
    {},
  );
  const subMenuRefs = useRef<Record<string, HTMLDivElement | null>>({});

  // const isActive = (path: string) => location.pathname === path;
  const isActive = useCallback(
    (path: string) => activePath === path,
    [activePath],
  );

  // useEffect(() => {
  //   let submenuMatched = false;
  //   ["main", "others"].forEach((menuType) => {
  //     const items = menuType === "main" ? navItems : othersItems;
  //     items.forEach((nav, index) => {
  //       if (nav.subItems) {
  //         nav.subItems.forEach((subItem) => {
  //           if (isActive(subItem.path)) {
  //             setOpenSubmenu({
  //               type: menuType as "main" | "others",
  //               index,
  //             });
  //             submenuMatched = true;
  //           }
  //         });
  //       }
  //     });
  //   });

  //   if (!submenuMatched) {
  //     setOpenSubmenu(null);
  //   }
  // }, [location, isActive]);

  useEffect(() => {
    if (openSubmenu !== null) {
      const key = `${openSubmenu.type}-${openSubmenu.index}`;
      if (subMenuRefs.current[key]) {
        setSubMenuHeight((prevHeights) => ({
          ...prevHeights,
          [key]: subMenuRefs.current[key]?.scrollHeight || 0,
        }));
      }
    }
  }, [openSubmenu]);

  const handleSubmenuToggle = (index: number, menuType: "main" | "others") => {
    setOpenSubmenu((prevOpenSubmenu) => {
      if (
        prevOpenSubmenu &&
        prevOpenSubmenu.type === menuType &&
        prevOpenSubmenu.index === index
      ) {
        return null;
      }
      return { type: menuType, index };
    });
  };

  const openWindow = (path: string, title: string, shiftKey?: boolean) => {
    // Shift-click any model → open in DataBrowser
    if (shiftKey && !path.startsWith('/admin-wb')) {
      // Extract a model name from the path: /org/customer/list → customer, /products/item/list → item
      const segments = path.replace(/^\//, '').split('/');
      const modelGuess = segments.length >= 2 ? segments[segments.length - 2] : segments[0];
      const dbPath = `/admin-wb?model=${modelGuess}`;
      ensureWindow(dbPath, `DB: ${title}`);
      activateWindow(dbPath);
      return;
    }
    ensureWindow(path, title);
    activateWindow(path);
  };

  const renderMenuItems = (items: NavItem[], menuType: "main" | "others") => (
    <ul className="flex flex-col gap-2 px-3 pb-4">
      {items.map((nav, index) => (
        <li key={nav.name}>
          {nav.subItems ? (
            <button
              onClick={() => handleSubmenuToggle(index, menuType)}
              className={`menu-item group ${
                openSubmenu?.type === menuType && openSubmenu?.index === index
                  ? "menu-item-active"
                  : "menu-item-inactive"
              } cursor-pointer ${
                !isExpanded && !isHovered
                  ? "lg:justify-center"
                  : "lg:justify-start"
              }`}
            >
              <span
                className={`menu-item-icon-size  ${
                  openSubmenu?.type === menuType && openSubmenu?.index === index
                    ? "menu-item-icon-active"
                    : "menu-item-icon-inactive"
                }`}
              >
                {nav.icon}
              </span>
              {(isExpanded || isHovered || isMobileOpen) && (
                <span className="menu-item-text">{nav.name}</span>
              )}
              {(isExpanded || isHovered || isMobileOpen) && (
                <ChevronDownIcon
                  className={`ml-auto w-5 h-5 transition-transform duration-200 ${
                    openSubmenu?.type === menuType &&
                    openSubmenu?.index === index
                      ? "rotate-180 text-brand-500"
                      : ""
                  }`}
                />
              )}
            </button>
          ) : (
            nav.path && (
              <button
                className={`menu-item group ${
                  isActive(nav.path) ? "menu-item-active" : "menu-item-inactive"
                }`}
                onClick={(e) => openWindow(nav.path!, nav.name, e.shiftKey)}
              >
                <span
                  className={`menu-item-icon-size ${
                    isActive(nav.path)
                      ? "menu-item-icon-active"
                      : "menu-item-icon-inactive"
                  }`}
                >
                  {nav.icon}
                </span>
                {(isExpanded || isHovered || isMobileOpen) && (
                  <span className="menu-item-text">{nav.name}</span>
                )}
              </button>
            )
          )}
          {nav.subItems && (isExpanded || isHovered || isMobileOpen) && (
            <div
              ref={(el) => {
                subMenuRefs.current[`${menuType}-${index}`] = el;
              }}
              className="overflow-hidden transition-all duration-300"
              style={{
                height:
                  openSubmenu?.type === menuType && openSubmenu?.index === index
                    ? `${subMenuHeight[`${menuType}-${index}`]}px`
                    : "0px",
              }}
            >
              <ul className="mt-2 space-y-1 ml-9">
                {nav.subItems.map((subItem) => (
                  <li key={subItem.name}>
                    <button
                      className={`menu-dropdown-item ${
                        isActive(subItem.path)
                          ? "menu-dropdown-item-active"
                          : "menu-dropdown-item-inactive"
                      }`}
                      onClick={(e) => openWindow(subItem.path, subItem.name, e.shiftKey)}
                    >
                      {subItem.name}
                      <span className="flex items-center gap-1 ml-auto">
                        {subItem.new && (
                          <span
                            className={`ml-auto ${
                              isActive(subItem.path)
                                ? "menu-dropdown-badge-active"
                                : "menu-dropdown-badge-inactive"
                            } menu-dropdown-badge`}
                          >
                            new
                          </span>
                        )}
                        {subItem.pro && (
                          <span
                            className={`ml-auto ${
                              isActive(subItem.path)
                                ? "menu-dropdown-badge-active"
                                : "menu-dropdown-badge-inactive"
                            } menu-dropdown-badge`}
                          >
                            pro
                          </span>
                        )}
                      </span>
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

  const targetWidth = isExpanded || isMobileOpen ? 290 : isHovered ? 290 : 90;
  const translateClass = isVisible ? "translate-x-0" : "-translate-x-full";

  return (
    <aside
      className={`fixed top-[60px] left-0 flex h-[calc(100vh-60px)] flex-col px-5 bg-white text-gray-900 transition-all duration-300 ease-in-out z-50 border-r border-gray-200 ${translateClass}`}
      onMouseEnter={() => !isExpanded && setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        pointerEvents: isVisible ? "auto" : "none",
        width: isVisible ? `${targetWidth}px` : 0,
        paddingLeft: isVisible ? "20px" : 0,
        paddingRight: isVisible ? "20px" : 0,
      }}
    >
      <div className="py-2" />
      <div className="flex items-center justify-end">
        <button
          className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-semibold text-slate-700 shadow-sm hover:border-slate-300 hover:bg-slate-50"
          onClick={() => {
            if (isVisible) {
              toggleVisibility();
            } else {
              toggleVisibility();
            }
          }}
        >
          {isVisible ? "Hide" : "Show"}
        </button>
      </div>
      <div className="flex flex-col overflow-y-auto duration-300 ease-linear no-scrollbar">
        <nav className="mb-6">
          <div className="flex flex-col gap-4">
            {/* Key Models Section */}
            <div>
              <h2
                className={`mb-2 text-xs uppercase flex leading-[20px] text-blue-500 font-bold ${
                  !isExpanded && !isHovered
                    ? "lg:justify-center"
                    : "justify-start"
                }`}
              >
                {isExpanded || isHovered || isMobileOpen ? (
                  "Key Models"
                ) : (
                  <HorizontaLDots className="size-6" />
                )}
              </h2>
              {renderMenuItems(keyModelNavItems, "main")}
            </div>
            {/* Main Menu Section */}
            <div>
              <h2
                className={`mb-4 text-xs uppercase flex leading-[20px] text-gray-400 ${
                  !isExpanded && !isHovered
                    ? "lg:justify-center"
                    : "justify-start"
                }`}
              >
                {isExpanded || isHovered || isMobileOpen ? (
                  "Menu"
                ) : (
                  <HorizontaLDots className="size-6" />
                )}
              </h2>
              {renderMenuItems(navItems, "main")}
            </div>
            <div className="">
              <h2
                className={`mb-4 text-xs uppercase flex leading-[20px] text-gray-400 ${
                  !isExpanded && !isHovered
                    ? "lg:justify-center"
                    : "justify-start"
                }`}
              >
                {/* {isExpanded || isHovered || isMobileOpen ? (
                  "Others"
                ) : (
                  <HorizontaLDots />
                )} */}
              </h2>
              {/* {renderMenuItems(othersItems, "others")} */}
            </div>
          </div>
        </nav>
        {/* {isExpanded || isHovered || isMobileOpen ? <SidebarWidget /> : null} */}
      </div>
    </aside>
  );
};

export default AppSidebar;
