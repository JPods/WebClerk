import { useCallback } from "react";
import { useLocation } from "react-router-dom";
import CustomerDetail from "./CustomerDisplay";
import { useWindowManager } from "../../../../../context/WindowManagerContext";

export default function CustomerAddPage() {
  const location = useLocation();
  const { closeWindow } = useWindowManager();

  const handleClose = useCallback(() => {
    closeWindow(location.pathname);
  }, [closeWindow, location.pathname]);

  return (
    <>
      <CustomerDetail modeProp="add" hideBreadcrumb onCancel={handleClose} onSaved={handleClose} />
    </>
  );
}
