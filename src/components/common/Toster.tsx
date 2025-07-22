
import { useSelector, useDispatch } from "react-redux";
import { RootState } from "../../store";
import { hideToast } from "../../store/slices/toastSlice";
import { useEffect } from "react";

const toastColors = {
  success: "#4BB543",
  error: "#FF3333",
  info: "#3399FF",
  warning: "#FF9900",
  null: "#FF3333",
};

const Toster = () => {
  const { message, type, open } = useSelector((state: RootState) => state.toast);
  console.log("Toast message:", type, message, open);
  const dispatch = useDispatch();
  
  useEffect(() => {
    if (open) {
      const timer = setTimeout(() => dispatch(hideToast()), 3000);
      return () => clearTimeout(timer);
    }
  }, [open, dispatch]);

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
