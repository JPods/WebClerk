import { useSelector } from "react-redux";
import { createPortal } from "react-dom";
import { RootState } from "../../store";

// Renders a lightweight full-screen overlay while any API call is in flight
export default function GlobalLoadingSpinner() {
  const isLoading = useSelector((state: RootState) => state.loading.isApiLoading);

  if (!isLoading || typeof document === "undefined") return null;

  return createPortal(
    <div className="fixed inset-0 z-[99999] flex items-center justify-center bg-gray-900/30 backdrop-blur-sm">
      <div
        className="h-12 w-12 animate-spin rounded-full border-4 border-white border-t-transparent drop-shadow-lg"
        role="status"
        aria-label="Loading"
      />
    </div>,
    document.body
  );
}