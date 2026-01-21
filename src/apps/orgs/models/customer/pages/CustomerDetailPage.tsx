import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import { fetchCustomers, deleteCustomer } from "../services/customerApi";
import CustomerDetail from "./CustomerDisplay";
import { dynamicData } from "../../../../../model/dynamicData";
import { useWindowManager } from "../../../../../context/WindowManagerContext";
import { PageRoutes } from "../../../../../routes/Routes";
import { useDispatch } from "react-redux";
import { showToast } from "../../../../../store/slices/toastSlice";

export default function CustomerDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();
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

  const openDetail = useCallback((targetId: number) => {
    const path = `${PageRoutes.customerDetail}/${targetId}`;
    ensureWindow(path, `Customer ${targetId}`, { maximized: false });
    activateWindow(path);
    closeWindow(location.pathname);
  }, [activateWindow, closeWindow, ensureWindow, location.pathname]);

  const handlePrev = prevId ? () => openDetail(prevId) : undefined;
  const handleNext = nextId ? () => openDetail(nextId) : undefined;

  const handleEdit = useCallback(() => {
    if (!Number.isFinite(customerId)) return;
    const path = `${PageRoutes.customerEdit}/${customerId}`;
    const label = record?.display_name || record?.name || `Customer ${customerId}`;
    ensureWindow(path, `Edit ${label}`, { maximized: false });
    activateWindow(path);
    closeWindow(location.pathname);
  }, [activateWindow, closeWindow, customerId, ensureWindow, location.pathname, record]);

  const handleDelete = useCallback(async () => {
    if (!record?.id) return;
    if (!window.confirm(`Delete customer ${record.display_name || record.name || record.id}?`)) return;
    try {
      await deleteCustomer(record.id);
      dispatch(showToast({ message: "Customer deleted successfully", type: "success" }));
      handleClose();
      navigate(PageRoutes.customerList);
    } catch (err: any) {
      dispatch(showToast({ message: err?.message || "Failed to delete customer", type: "error" }));
    }
  }, [dispatch, handleClose, navigate, record]);

  return (
    <>
      <PageBreadcrumb pageTitle="Customer Detail" />
      {loading && <div>Loading...</div>}
      {error && <div className="text-red-600">{error}</div>}
      {!loading && !error && (
        <CustomerDetail
          modeProp="view"
          dataProp={record}
          hideBreadcrumb
          onPrev={handlePrev}
          onNext={handleNext}
          onCancel={handleClose}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      )}
    </>
  );
}
