/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { useLocation, useNavigate } from "react-router-dom";

type Props = {
  title?: string;
  description?: string;
};

export default function Placeholder({ title, description }: Props) {
  const location = useLocation();
  const navigate = useNavigate();
  const label = title || "Coming soon";
  const desc = description || "This page is not yet available."

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6 text-center">
      <div className="rounded-2xl border border-dashed border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-blue-500">Placeholder</p>
        <h1 className="mt-2 text-2xl font-semibold text-gray-900 dark:text-white">{label}</h1>
        <p className="mt-2 max-w-xl text-sm text-gray-600 dark:text-gray-300">
          {desc}
        </p>
        <p className="mt-2 text-xs text-gray-400">Path: {location.pathname}</p>
        <div className="mt-4 flex flex-wrap justify-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="rounded-full bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-blue-700"
          >
            Go back
          </button>
        </div>
      </div>
    </div>
  );
}