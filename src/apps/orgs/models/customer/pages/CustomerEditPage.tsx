import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { fetchCustomers } from "../services/customerApi";
import CustomerDetail from "./CustomerDisplay";
import { dynamicData } from "../../../../../model/dynamicData";
import { useWindowManager } from "../../../../../context/WindowManagerContext";
import { PageRoutes } from "../../../../../routes/Routes";

export default function CustomerEditPage() {
  const { id } = useParams();
  const location = useLocation();
  const { ensureWindow, activateWindow, closeWindow } = useWindowManager();
  const [record, setRecord] = useState<dynamicData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const customerId = Number(id);

  useEffect(() => {
    if (!Number.isFinite(customerId)) return;
    setLoading(true);
    setError(null);
    fetchCustomers(customerId)
      .then((res) => {
        const data = res?.data?.data?.record || res?.data?.data || res?.data;
        setRecord(data || null);
      })
      .catch((err) => {
        setError(err?.message || "Failed to load customer.");
      })
      .finally(() => setLoading(false));
  }, [id, customerId]);

  const listOrder = useMemo(() => {
    try {
      const raw = localStorage.getItem("customer-list-order");
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [] as number[];
    }
  }, [customerId]);

  const currentIndex = useMemo(() => listOrder.indexOf(customerId), [listOrder, customerId]);
  const prevId = currentIndex > 0 ? listOrder[currentIndex - 1] : null;
  const nextId = currentIndex >= 0 && currentIndex < listOrder.length - 1 ? listOrder[currentIndex + 1] : null;

  const handleClose = useCallback(() => {
    closeWindow(location.pathname);
  }, [closeWindow, location.pathname]);

  const openEdit = useCallback((targetId: number) => {
    const path = `${PageRoutes.customerEdit}/${targetId}`;
    ensureWindow(path, `Edit Customer ${targetId}`, { maximized: false });
    activateWindow(path);
    closeWindow(location.pathname);
  }, [activateWindow, closeWindow, ensureWindow, location.pathname]);

  const handlePrev = prevId ? () => openEdit(prevId) : undefined;
  const handleNext = nextId ? () => openEdit(nextId) : undefined;

  return (
    <>
      <PageBreadcrumb pageTitle="Edit Customer" />
      {loading && <div>Loading...</div>}
      {error && <div className="text-red-600">{error}</div>}
      {!loading && !error && (
        <CustomerDetail
          modeProp="edit"
          dataProp={record}
          hideBreadcrumb
          onPrev={handlePrev}
          onNext={handleNext}
          onCancel={handleClose}
        />
      )}
    </>
  );
}
