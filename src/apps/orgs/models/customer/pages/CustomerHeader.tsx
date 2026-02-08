import React from "react";
import { FaBuilding, FaMapMarkerAlt, FaPhone, FaFileAlt, FaEnvelope } from "react-icons/fa";

type Customer = {
  id?: number;
  display_name?: string;
  status?: string;
  org_type?: string;
  version?: number;
  is_active?: boolean;
  contacts?: string;
  addresses?: string;
  docs?: string;
};

const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    active: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    inactive:
      "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
    pending:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    suspended:
      "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
    archived: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  };

  return (
    <span
      className={`px-2 py-1 text-xs font-medium rounded-full ${
        statusStyles[status?.toLowerCase() ?? "pending"] ?? statusStyles.pending
      }`}
    >
      {status?.replace("_", " ") ?? "pending"}
    </span>
  );
};

export default function CustomerHeader({ data }: { data: Customer }) {
  const contactsData = typeof data.contacts === "string" ? JSON.parse(data.contacts || "[]") : data.contacts || [];
  const addressesData = typeof data.addresses === "string" ? JSON.parse(data.addresses || "[]") : data.addresses || [];
  const docsData = typeof data.docs === "string" ? JSON.parse(data.docs || "[]") : data.docs || [];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <FaBuilding className="text-blue-500" />
            Company Details
          </h3>
          <dl className="space-y-3 text-xs">
            <div className="flex justify-between items-center">
              <dt className="text-slate-500 dark:text-slate-400">Display Name</dt>
              <dd className="font-medium text-slate-900 dark:text-white">{data.display_name || "—"}</dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-slate-500 dark:text-slate-400">Org Type</dt>
              <dd className="font-medium text-slate-900 dark:text-white">{data.org_type?.toUpperCase() || "—"}</dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-slate-500 dark:text-slate-400">Version</dt>
              <dd className="font-medium text-slate-900 dark:text-white">{data.version || 1}</dd>
            </div>
          </dl>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Status</h3>
          <div className="space-y-4">
            <div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Current Status</div>
              <StatusBadge status={data.status} />
            </div>
            <div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mb-1">Active</div>
              <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${
                data.is_active
                  ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                  : "bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400"
              }`}>{data.is_active ? "Active" : "Inactive"}</span>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-4">Summary</h3>
          <dl className="space-y-3 text-xs">
            <div className="flex justify-between items-center">
              <dt className="text-slate-500 dark:text-slate-400 flex items-center gap-1"><FaPhone size={12} /> Contacts</dt>
              <dd className="font-semibold text-slate-900 dark:text-white">{Array.isArray(contactsData) ? contactsData.length : 0}</dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-slate-500 dark:text-slate-400 flex items-center gap-1"><FaMapMarkerAlt size={12} /> Addresses</dt>
              <dd className="font-semibold text-slate-900 dark:text-white">{Array.isArray(addressesData) ? addressesData.length : 0}</dd>
            </div>
            <div className="flex justify-between items-center">
              <dt className="text-slate-500 dark:text-slate-400 flex items-center gap-1"><FaFileAlt size={12} /> Documents</dt>
              <dd className="font-semibold text-slate-900 dark:text-white">{Array.isArray(docsData) ? docsData.length : 0}</dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="flex gap-2">
        <button type="button" className="px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors flex items-center gap-2">
          <FaEnvelope size={14} />
          Email
        </button>
      </div>
    </div>
  );
}
