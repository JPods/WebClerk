/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */

import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { hideToast } from "../../store/slices/toastSlice";
import { runToastAction } from "../../utils/toastActions";
import { useEffect } from "react";

const toastColors = {
  success: "#4BB543",
  error: "#FF3333",
  info: "#3399FF",
  warning: "#FF9900",
  null: "#FF3333",
};

const Toster = () => {
  const { message, type, open, duration, action } = useSelector((state: RootState) => state.toast);
  const dispatch = useDispatch();
  
  useEffect(() => {
    if (open) {
      const timer = setTimeout(() => dispatch(hideToast()), duration);
      return () => clearTimeout(timer);
    }
  }, [open, duration, dispatch]);

  if (!open) return null;
 
  return (
    <div
      style={{
        position: "fixed",
        top: "90px",
        right: "30px",
        padding: "12px 20px",
        backgroundColor: toastColors[type as keyof typeof toastColors],
        color: "#fff",
        borderRadius: "8px",
        boxShadow: "0 2px 10px rgba(0,0,0,0.2)",
        zIndex: 9999,
      }}
    >
      {message}
      {action && (
        <button type="button" data-wc="toast-action"
          onClick={() => { runToastAction(action.id); dispatch(hideToast()); }}
          style={{ marginLeft: 16, padding: "2px 10px", borderRadius: 6, border: "1px solid rgba(255,255,255,0.7)",
                   background: "transparent", color: "#fff", fontWeight: 600, cursor: "pointer" }}>
          {action.label}
        </button>
      )}
    </div>
  );
  // return (
  //   <div className={`fixed top-5 right-5 p-4 rounded text-white ${type === "success" ? "bg-green-600" : "bg-red-600"}`}>
  //     <span>{message}</span>
  //     <button className="ml-4" onClick={() => dispatch(hideToast())}>✖</button>
  //   </div>
  // );
};

export default Toster;
