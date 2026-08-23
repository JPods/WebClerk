/* LastChecked: 2026-08-21 | WhereUsed: Router.tsx | WhoCreated: Bill+Claude */
/**
 * WcapiRouteHandler - Universal route handler for /wcapi/get/ style URLs
 *
 * Reads model_name and id from query parameters, renders ModelDetailPage
 * for contact/org/item models, UiDetail for transactions.
 *
 * Usage: /wcapi/get/?model_name=purchase&id=38
 */
import React, { Suspense, lazy } from "react";
import { useSearchParams } from "react-router-dom";

const ModelDetailPage = lazy(() => import("../components/common/ModelDetailPage"));
const UiDetail = lazy(() => import("../apps/transactions/components/TransactionDetail"));

const TRANSACTION_MODELS = new Set(['purchase', 'order', 'invoice', 'proposal', 'quote', 'receipt', 'workorder', 'requisition', 'payment']);

export default function WcapiRouteHandler() {
  const [searchParams] = useSearchParams();
  const modelName = searchParams.get("model_name");
  const id = searchParams.get("id");

  if (!modelName) {
    return (
      <div className="p-4 text-red-600">
        <h2 className="text-lg font-semibold">Missing model_name parameter</h2>
        <p>URL should be: /wcapi/get/?model_name=&lt;model&gt;&amp;id=&lt;id&gt;</p>
      </div>
    );
  }

  const normalized = modelName.toLowerCase().replace(/-/g, "_");
  const recordId = id ? parseInt(id, 10) : undefined;

  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" /></div>}>
      {TRANSACTION_MODELS.has(normalized)
        ? <UiDetail modelName={normalized === 'quote' ? 'proposal' : normalized} recordId={recordId} />
        : <ModelDetailPage modelName={normalized} recordId={recordId} />
      }
    </Suspense>
  );
}
