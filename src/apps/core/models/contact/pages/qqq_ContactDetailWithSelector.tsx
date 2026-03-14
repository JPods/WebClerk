/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useState } from "react";
import { FaColumns, FaThLarge, FaListAlt, FaLayerGroup } from "react-icons/fa";
import { ContactAddProps } from "../types/contactType";
import ContactDetailMain from "./ContactDetail"; // Enterprise best-practice layout
import ContactDetailHorizontal from "./ContactDetailHorizontal";
import ContactDetailTwoColumn from "./ContactDetailTwoColumn";
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { useLocation } from "react-router";

export type LayoutStyle = "grid" | "horizontal" | "two-column";

interface LayoutOption {
  value: LayoutStyle;
  label: string;
  icon: React.ReactNode;
  description: string;
}

const layoutOptions: LayoutOption[] = [
  {
    value: "grid",
    label: "Grid",
    icon: <FaThLarge className="w-4 h-4" />,
    description: "3-column grid layout with labels above inputs",
  },
  {
    value: "horizontal",
    label: "Horizontal",
    icon: <FaListAlt className="w-4 h-4" />,
    description: "Single column with labels on the left",
  },
  {
    value: "two-column",
    label: "Two Column",
    icon: <FaColumns className="w-4 h-4" />,
    description: "Card-based two-column layout",
  },
];

interface LayoutSelectorProps {
  value: LayoutStyle;
  onChange: (layout: LayoutStyle) => void;
}

function LayoutSelector({ value, onChange }: LayoutSelectorProps) {
  return (
    <div className="mb-6 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
      <div className="flex items-center gap-2 mb-3">
        <FaLayerGroup className="text-slate-500" />
        <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">Layout Style</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {layoutOptions.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg border-2 transition-all
              ${value === option.value
                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                : "border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-500"
              }
            `}
            title={option.description}
          >
            {option.icon}
            <span className="text-sm font-medium">{option.label}</span>
          </button>
        ))}
      </div>
      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
        {layoutOptions.find(o => o.value === value)?.description}
      </p>
    </div>
  );
}

export default function ContactDetailWithSelector(props: ContactAddProps) {
  const location = useLocation();
  const routeState = (location.state as any) || {};
  const mode: "add" | "edit" | "view" = props.modeProp || routeState.mode || "add";
  
  const [layout, setLayout] = useState<LayoutStyle>(() => {
    // Try to load saved preference from localStorage
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("contactDetailLayout");
      if (saved && ["grid", "horizontal", "two-column"].includes(saved)) {
        return saved as LayoutStyle;
      }
    }
    return "grid";
  });

  const handleLayoutChange = (newLayout: LayoutStyle) => {
    setLayout(newLayout);
    // Save preference to localStorage
    if (typeof window !== "undefined") {
      localStorage.setItem("contactDetailLayout", newLayout);
    }
  };

  // Render the appropriate layout component
  const renderLayout = () => {
    switch (layout) {
      case "horizontal":
        return <ContactDetailHorizontal {...props} hideBreadcrumb />;
      case "two-column":
        return <ContactDetailTwoColumn {...props} hideBreadcrumb />;
      case "grid":
      default:
        return <ContactDetailMain {...props} hideBreadcrumb />;
    }
  };

  return (
    <div>
      {/* Breadcrumb - show unless hidden or inline */}
      {!props.hideBreadcrumb && !props.inline && (
        <PageBreadcrumb
          pageTitle={
            mode === "edit"
              ? "Edit Contact"
              : mode === "view"
              ? "View Contact"
              : "Add Contact"
          }
        />
      )}
      
      {/* Layout Selector - only show if not inline mode */}
      {!props.inline && (
        <LayoutSelector value={layout} onChange={handleLayoutChange} />
      )}
      
      {/* Render the selected layout */}
      {renderLayout()}
    </div>
  );
}

// Re-export individual layouts for direct use
export { ContactDetailMain, ContactDetailHorizontal, ContactDetailTwoColumn };
