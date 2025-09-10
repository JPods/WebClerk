import { Cross } from "../../icons";

export const Toast = ({ show, removeToast, toastData }) => {
  const { type, heading, description } = toastData;

  return (
    <div className={`app_toast ${show ? "show" : "hide"}`}>
      <div className={`app_toast_cover ${type && type}`}>
        <div className="app_toast_content">
          <h5>{heading}</h5>
          {description && <p>{description}</p>}
        </div>
        <button onClick={() => removeToast()}>
          <Cross />
        </button>
      </div>
    </div>
  );
};
