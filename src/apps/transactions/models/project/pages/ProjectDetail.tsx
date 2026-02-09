/**
 * ProjectDetail - Refactored to use standard DetailTabs layout
 * Provides tabbed navigation with overview, comments, actions, documents panels
 */
import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { useAppSelector } from "@/store/hooks";
import {
  FaArrowLeft,
  FaEdit,
  FaSave,
  FaTimes,
  FaProjectDiagram,
  FaCalendar,
  FaInfoCircle,
} from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { getRecord, saveRecord, deleteRecord } from "@/api/wcapi";

// Import standard components
import { DetailTabs, useDetailTabs } from "@/components/common/DetailTabs";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import CommentsPanel from "@/apps/transactions/components/CommentsPanel";
import MetadataPanel from "@/apps/transactions/components/MetadataPanel";
import JsonFieldEditor from "@/apps/transactions/components/JsonFieldEditor";

// Import types
import type { ProjectAddProps } from "../types/projectType";

// Project interface extending base record
interface Project {
  id?: number;
  ida?: string;
  name?: string;
  description?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  dt_created?: number;
  dt_modified?: number;
  comments?: {
    notes?: Array<{
      user?: string;
      mgs?: string;
      time?: string;
    }>;
  };
  actions?: {
    items?: Array<{
      id: number;
      status: string;
      action_type?: string;
      description?: string;
    }>;
  };
  refs?: {
    links?: {
      document?: Array<{ id: number; name?: string }>;
      customer?: Array<{ id: number; display_name?: string }>;
    };
  };
  metadata?: Record<string, unknown>;
}

// Status Badge Component
const StatusBadge: React.FC<{ status?: string }> = ({ status }) => {
  const statusStyles: Record<string, string> = {
    planned:
      "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
    active:
      "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    completed:
      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    on_hold:
      "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    cancelled:
      "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  };

  return (
    <span
      className={`px-2 py-1 text-xs font-medium rounded-full ${
        statusStyles[status ?? "planned"] ?? statusStyles.planned
      }`}
    >
      {status?.replace("_", " ") ?? "planned"}
    </span>
  );
};

// Format date for display
const formatDate = (dateStr?: string): string => {
  if (!dateStr) return "--";
  try {
    return new Date(dateStr).toLocaleDateString();
  } catch {
    return dateStr;
  }
};

export default function ProjectDetail({
  modeProp,
  dataProp,
  hideBreadcrumb,
  onSaved,
  inline = false,
  onCancelInline,
}: ProjectAddProps) {
  const { id: urlId } = useParams<{ id: string }>();
  const id = dataProp?.id?.toString() ?? urlId;
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const isAdmin = user?.role === "admin" || (Array.isArray(user?.role) && user.role.includes("admin"));

  // State
  const [data, setData] = useState<Project | null>(null);
  const [editData, setEditData] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(modeProp === "add" || modeProp === "edit");
  const [saving, setSaving] = useState(false);

  // Use standard tab management hooks
  const { activeTab, setActiveTab } = useDetailTabs("project", "overview");

  // Compute badge counts
  const commentCount = useMemo(() => {
    const notes = data?.comments?.notes ?? [];
    return notes.length;
  }, [data?.comments]);

  const actionCount = useMemo(() => {
    const items = data?.actions?.items ?? [];
    return items.filter((a) => a.status === "pending").length;
  }, [data?.actions]);

  const documentCount = useMemo(() => {
    return data?.refs?.links?.document?.length ?? 0;
  }, [data?.refs?.links?.document]);

  // Fetch data
  useEffect(() => {
    if (modeProp === "add") {
      const emptyRecord: Project = {
        id: 0,
        name: "",
        description: "",
        status: "planned",
        comments: { notes: [] },
        actions: { items: [] },
        refs: { links: {} },
        metadata: {},
      };
      setData(emptyRecord);
      setEditData(emptyRecord);
      setLoading(false);
      return;
    }

    if (dataProp) {
      setData(dataProp);
      setEditData(dataProp);
      setLoading(false);
      return;
    }

    const loadData = async () => {
      if (!id) return;

      setLoading(true);
      setError(null);

      try {
        const result = await getRecord("tx_projects", Number(id));
        const record = result.record ?? result;
        setData(record);
        setEditData(record);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load project");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [id, modeProp, dataProp]);

  // Update editing state when modeProp changes
  useEffect(() => {
    if (modeProp === "edit") setIsEditing(true);
    else if (modeProp === "view") setIsEditing(false);
  }, [modeProp]);

  // Handlers
  const handleEdit = () => {
    if (data) {
      setEditData({ ...data });
      setIsEditing(true);
    }
  };

  const handleCancel = useCallback(() => {
    setEditData(data);
    setIsEditing(false);
    if (inline && onCancelInline) {
      onCancelInline();
    }
  }, [data, inline, onCancelInline]);

  const handleSave = useCallback(async () => {
    if (!editData) return;

    setSaving(true);
    dispatch(showToast({ message: "Saving...", type: "info" }));

    try {
      const result = await saveRecord("tx_projects", editData);
      const savedRecord = result.record ?? result;

      setData(savedRecord);
      setEditData(savedRecord);
      setIsEditing(false);

      dispatch(
        showToast({
          message: "Project saved successfully",
          type: "success",
        })
      );

      onSaved?.();
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : "Failed to save";
      setError(errorMsg);
      dispatch(showToast({ message: errorMsg, type: "error" }));
    } finally {
      setSaving(false);
    }
  }, [editData, dispatch, onSaved]);

  const handleDelete = useCallback(async () => {
    if (!data?.id) return;

    if (!confirm("Are you sure you want to delete this project?")) return;

    try {
      await deleteRecord("tx_projects", data.id);
      dispatch(
        showToast({
          message: "Project deleted successfully",
          type: "success",
        })
      );
      navigate("/transactions/projects");
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : "Failed to delete";
      dispatch(showToast({ message: errorMsg, type: "error" }));
    }
  }, [data?.id, dispatch, navigate]);

  const handleFieldChange = (field: keyof Project, value: unknown) => {
    if (!editData) return;
    setEditData({ ...editData, [field]: value });
  };

  // Current data for display
  const currentData = isEditing && editData ? editData : data;

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-500 dark:text-slate-400">Loading...</div>
      </div>
    );
  }

  // Error state
  if (error && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500">{error}</div>
      </div>
    );
  }

  if (!currentData) return null;

  // Render tab content
  const renderTabContent = () => {
    switch (activeTab) {
      case "overview":
        return (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Project Details Card */}
            <ComponentCard>
              <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                <FaProjectDiagram className="text-blue-500" />
                Project Details
              </h3>
              <dl className="space-y-4 text-sm">
                <div className="flex justify-between items-center">
                  <dt className="text-slate-500 dark:text-slate-400">Name</dt>
                  {isEditing ? (
                    <input
                      type="text"
                      value={editData?.name ?? ""}
                      onChange={(e) => handleFieldChange("name", e.target.value)}
                      className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                    />
                  ) : (
                    <dd className="font-medium text-slate-900 dark:text-white">
                      {currentData.name ?? "--"}
                    </dd>
                  )}
                </div>
                <div className="flex justify-between items-center">
                  <dt className="text-slate-500 dark:text-slate-400">Status</dt>
                  {isEditing ? (
                    <select
                      value={editData?.status ?? "planned"}
                      onChange={(e) => handleFieldChange("status", e.target.value)}
                      className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                    >
                      <option value="planned">Planned</option>
                      <option value="active">Active</option>
                      <option value="on_hold">On Hold</option>
                      <option value="completed">Completed</option>
                      <option value="cancelled">Cancelled</option>
                    </select>
                  ) : (
                    <dd>
                      <StatusBadge status={currentData.status} />
                    </dd>
                  )}
                </div>
                <div>
                  <dt className="text-slate-500 dark:text-slate-400 mb-1">
                    Description
                  </dt>
                  {isEditing ? (
                    <textarea
                      value={editData?.description ?? ""}
                      onChange={(e) =>
                        handleFieldChange("description", e.target.value)
                      }
                      rows={3}
                      className="w-full px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                    />
                  ) : (
                    <dd className="text-slate-900 dark:text-white">
                      {currentData.description ?? "--"}
                    </dd>
                  )}
                </div>
              </dl>
            </ComponentCard>

            {/* Timeline Card */}
            <ComponentCard>
              <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                <FaCalendar className="text-green-500" />
                Timeline
              </h3>
              <dl className="space-y-4 text-sm">
                <div className="flex justify-between items-center">
                  <dt className="text-slate-500 dark:text-slate-400">
                    Start Date
                  </dt>
                  {isEditing ? (
                    <input
                      type="date"
                      value={editData?.start_date ?? ""}
                      onChange={(e) =>
                        handleFieldChange("start_date", e.target.value)
                      }
                      className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                    />
                  ) : (
                    <dd className="text-slate-900 dark:text-white">
                      {formatDate(currentData.start_date)}
                    </dd>
                  )}
                </div>
                <div className="flex justify-between items-center">
                  <dt className="text-slate-500 dark:text-slate-400">
                    End Date
                  </dt>
                  {isEditing ? (
                    <input
                      type="date"
                      value={editData?.end_date ?? ""}
                      onChange={(e) =>
                        handleFieldChange("end_date", e.target.value)
                      }
                      className="px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
                    />
                  ) : (
                    <dd className="text-slate-900 dark:text-white">
                      {formatDate(currentData.end_date)}
                    </dd>
                  )}
                </div>
                <div className="flex justify-between items-center">
                  <dt className="text-slate-500 dark:text-slate-400">ID</dt>
                  <dd className="font-mono text-slate-600 dark:text-slate-300">
                    {currentData.id ?? "--"}
                  </dd>
                </div>
              </dl>
            </ComponentCard>
          </div>
        );

      case "comments":
        const displayName = user ? `${user.name_first} ${user.name_last}` : "You";
        return (
          <CommentsPanel
            comments={currentData.comments ?? {}}
            isEditing={isEditing}
            onChange={(val) => handleFieldChange("comments", val)}
            currentUser={displayName}
            currentUserId={user?.id}
          />
        );

      case "actions":
        const actions = currentData.actions?.items ?? [];
        return (
          <ComponentCard>
            <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
              Actions ({actions.length})
            </h3>
            {actions.length === 0 ? (
              <p className="text-slate-500 dark:text-slate-400">
                No actions for this project.
              </p>
            ) : (
              <ul className="divide-y divide-slate-200 dark:divide-slate-700">
                {actions.map((action, idx) => (
                  <li key={action.id || idx} className="py-3 flex justify-between items-center">
                    <span className="text-slate-900 dark:text-white">
                      {action.description ?? `Action #${action.id}`}
                    </span>
                    <StatusBadge status={action.status} />
                  </li>
                ))}
              </ul>
            )}
          </ComponentCard>
        );

      case "documents":
        const documents = currentData.refs?.links?.document ?? [];
        return (
          <ComponentCard>
            <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
              Documents ({documents.length})
            </h3>
            {documents.length === 0 ? (
              <p className="text-slate-500 dark:text-slate-400">
                No documents attached to this project.
              </p>
            ) : (
              <ul className="divide-y divide-slate-200 dark:divide-slate-700">
                {documents.map((doc, idx) => (
                  <li key={doc.id || idx} className="py-3">
                    <span className="text-slate-900 dark:text-white">
                      {doc.name ?? `Document #${doc.id}`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </ComponentCard>
        );

      case "history":
        return (
          <ComponentCard>
            <h3 className="font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <FaInfoCircle className="text-blue-500" />
              History
            </h3>
            <dl className="space-y-3 text-sm">
              <div className="flex justify-between items-center">
                <dt className="text-slate-500 dark:text-slate-400">Created</dt>
                <dd className="text-slate-900 dark:text-white">
                  {currentData.dt_created
                    ? new Date(currentData.dt_created * 1000).toLocaleString()
                    : "--"}
                </dd>
              </div>
              <div className="flex justify-between items-center">
                <dt className="text-slate-500 dark:text-slate-400">Modified</dt>
                <dd className="text-slate-900 dark:text-white">
                  {currentData.dt_modified
                    ? new Date(currentData.dt_modified * 1000).toLocaleString()
                    : "--"}
                </dd>
              </div>
            </dl>
          </ComponentCard>
        );

      case "raw":
        return isAdmin ? (
          <JsonFieldEditor
            label="Full Project JSON"
            value={currentData}
            readonly={!isEditing}
            onChange={(val) => {
              if (isEditing) {
                setEditData(val as Project);
              }
            }}
          />
        ) : null;

      default:
        return null;
    }
  };

  return (
    <>
      {/* Breadcrumb */}
      {!hideBreadcrumb && !inline && (
        <PageBreadcrumb
          pageTitle={
            modeProp === "add"
              ? "New Project"
              : modeProp === "edit"
              ? "Edit Project"
              : currentData.name ?? "Project Detail"
          }
        />
      )}

      {/* Main Content */}
      <div className={inline ? "" : "p-4 space-y-4"}>
        {/* Header */}
        {!inline && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate(-1)}
                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                <FaArrowLeft className="text-slate-600 dark:text-slate-400" />
              </button>
              <div>
                <h1 className="text-xl font-semibold text-slate-900 dark:text-white">
                  {currentData.name ?? "Project"}
                </h1>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  ID: {currentData.id ?? "--"} • <StatusBadge status={currentData.status} />
                </p>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2">
              {isEditing ? (
                <>
                  <button
                    onClick={handleCancel}
                    disabled={saving}
                    className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-lg transition-colors flex items-center gap-2"
                  >
                    <FaTimes size={14} />
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-2"
                  >
                    <FaSave size={14} />
                    {saving ? "Saving..." : "Save"}
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={handleEdit}
                    className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-2"
                  >
                    <FaEdit size={14} />
                    Edit
                  </button>
                  {data?.id && (
                    <button
                      onClick={handleDelete}
                      className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
                    >
                      Delete
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        )}

        {/* Tab Navigation */}
        <DetailTabs
          entityType="project"
          activeTab={activeTab}
          onTabChange={setActiveTab}
          standardTabs={["overview", "comments", "actions", "documents", "history", "raw"]}
          badges={{
            comments: commentCount || undefined,
            actions: actionCount || undefined,
            documents: documentCount || undefined,
          }}
        />

        {/* Tab Content */}
        <div className="mt-4">{renderTabContent()}</div>
      </div>
    </>
  );
}
