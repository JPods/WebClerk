import React from "react";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import { DevBadge } from './DevBadge';

type DetailMode = "add" | "edit" | "view";

interface DetailShellProps {
  title: string;
  mode?: DetailMode;
  inline?: boolean;
  hideBreadcrumb?: boolean;
  breadcrumbTitle?: string;
  onCancelInline?: () => void;
  showInlineHeader?: boolean;
  card?: boolean;
  children: React.ReactNode;
}

const getHeaderTitle = (title: string, mode: DetailMode) => {
  if (mode === "edit") return `Edit ${title}`;
  if (mode === "view") return `View ${title}`;
  return `Add New ${title}`;
};

const getBreadcrumbTitle = (title: string, mode: DetailMode) => {
  if (mode === "edit") return `Edit ${title}`;
  if (mode === "view") return `View ${title}`;
  return `${title} Detail`;
};

export default function DetailShell({
  title,
  mode = "view",
  inline = false,
  hideBreadcrumb,
  breadcrumbTitle,
  onCancelInline,
  showInlineHeader = true,
  card = true,
  children,
}: DetailShellProps) {
  const inlineHeader = inline && showInlineHeader ? (
    <div className="flex justify-between items-center mb-4">
      <h3 className="dark:text-white text-lg font-semibold">
        <DevBadge label={`${title}Detail`} className="mr-2" />
        {getHeaderTitle(title, mode)}
      </h3>
      {onCancelInline && (
        <button
          type="button"
          onClick={onCancelInline}
          className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        >
          &times;
        </button>
      )}
    </div>
  ) : null;

  return (
    <>
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb pageTitle={breadcrumbTitle ?? getBreadcrumbTitle(title, mode)} />
      )}

      {card ? (
        <ComponentCard>
          {inlineHeader}
          {children}
        </ComponentCard>
      ) : (
        <>
          {inlineHeader}
          {children}
        </>
      )}
    </>
  );
}