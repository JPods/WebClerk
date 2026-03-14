/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * WcapiRouteHandler - Universal route handler for /wcapi/get/ style URLs
 * 
 * This component reads model_name and id from query parameters and renders
 * the appropriate detail or list component.
 * 
 * Usage: /wcapi/get/?model_name=purchase&id=38 -> renders PurchaseDetail
 */
import React, { Suspense, lazy } from "react";
import { useSearchParams } from "react-router-dom";

// Lazy load detail components to avoid circular imports
const PurchaseDetail = lazy(() => import("../apps/transactions/models/purchase/pages/PurchaseDetail"));
const OrderDetail = lazy(() => import("../apps/transactions/models/order/pages/OrderDetail"));
const InvoiceDetail = lazy(() => import("../apps/transactions/models/invoice/pages/InvoiceDetail"));
const ProposalDetail = lazy(() => import("../apps/transactions/models/proposal/pages/ProposalDetail"));
const ItemDetail = lazy(() => import("../apps/products/models/item/pages/ItemDetail"));
const CustomerDetailPage = lazy(() => import("../apps/orgs/models/customer/pages/CustomerDetail"));
const VendorDetail = lazy(() => import("../apps/orgs/models/vendor/pages/VendorDetail"));
const ContactDetail = lazy(() => import("../apps/core/models/contact/pages/ContactDetail"));

// Model name to component mapping
const MODEL_DETAIL_MAP: Record<string, React.LazyExoticComponent<React.ComponentType<any>>> = {
  // Transactions
  "purchase": PurchaseDetail,
  "order": OrderDetail,
  "invoice": InvoiceDetail,
  "proposal": ProposalDetail,
  "quote": ProposalDetail,
  
  // Products
  "item": ItemDetail,
  "product": ItemDetail,
  
  // Organizations
  "customer": CustomerDetailPage,
  "vendor": VendorDetail,
  
  // Core
  "contact": ContactDetail,
};

// Loading fallback
const LoadingFallback = () => (
  <div className="flex items-center justify-center h-64">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
    <span className="ml-2 text-gray-600">Loading...</span>
  </div>
);

export default function WcapiRouteHandler() {
  const [searchParams] = useSearchParams();
  
  const modelName = searchParams.get("model_name");
  const id = searchParams.get("id");
  
  // If no model_name, show error
  if (!modelName) {
    return (
      <div className="p-4 text-red-600">
        <h2 className="text-lg font-semibold">Missing model_name parameter</h2>
        <p>URL should be: /wcapi/get/?model_name=&lt;model&gt;&amp;id=&lt;id&gt;</p>
      </div>
    );
  }
  
  // Normalize model name
  const normalizedModel = modelName.toLowerCase().replace(/-/g, "_");
  
  // Find the component
  const DetailComponent = MODEL_DETAIL_MAP[normalizedModel];
  
  if (!DetailComponent) {
    return (
      <div className="p-4 text-red-600">
        <h2 className="text-lg font-semibold">Unknown model: {modelName}</h2>
        <p>Supported models: {Object.keys(MODEL_DETAIL_MAP).join(", ")}</p>
      </div>
    );
  }
  
  // Render the component with id passed as prop or via URL params
  // Most detail components read id from URL params, so we need to handle this
  return (
    <Suspense fallback={<LoadingFallback />}>
      <DetailComponent 
        recordId={id ? parseInt(id, 10) : undefined}
        id={id ? parseInt(id, 10) : undefined}
      />
    </Suspense>
  );
}
