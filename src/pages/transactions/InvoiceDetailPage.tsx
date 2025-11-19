import { useEffect, useState } from "react";
import { useParams } from "react-router";

import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import ComponentCard from "../../components/common/ComponentCard";
import InvoiceForm from "../../components/InvoiceForm";
import InvoicesList from "../../components/InvoicesList";
import QAList from "../../components/QAList";
import { getRecord } from "../../api/wcapi";

export default function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [invoice, setInvoice] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      fetchInvoice();
    } else {
      setLoading(false);
    }
  }, [id]);

  const fetchInvoice = async () => {
    try {
      const res = await getRecord('invoice', parseInt(id!));
      setInvoice(res.record);
    } catch (error) {
      console.error("Failed to fetch invoice", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <>
      <PageBreadcrumb pageTitle="Invoice Details" />
      <div className="space-y-6">
        {/* Locked Box Placeholder */}
        <ComponentCard>
          <div className="p-4 bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 rounded">
            Locked Box Component - Placeholder
          </div>
        </ComponentCard>

        {/* Customer Name Search and Print */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ComponentCard>
            <div className="p-4">
              <label className="block text-sm font-medium mb-2">customer_name_search</label>
              <input type="text" className="w-full p-2 border rounded" placeholder="customer_name_search" />
            </div>
          </ComponentCard>
          <ComponentCard>
            <div className="p-4 flex items-center justify-between">
              <div>
                <p className="text-sm"><strong>sales_order_number:</strong> {invoice?.order_num || 'N/A'}</p>
                <p className="text-sm"><strong>customer_po_number:</strong> {invoice?.customer_po || 'N/A'}</p>
              </div>
              <button className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                print
              </button>
            </div>
          </ComponentCard>
        </div>

        {/* Invoice Form */}
        <InvoiceForm
          modeProp={id ? 'edit' : 'add'}
          dataProp={invoice}
          onSaved={() => {
            if (id) fetchInvoice();
          }}
        />

        {/* Order Totals */}
        <ComponentCard>
          <h3 className="text-lg font-semibold mb-4">Order Totals</h3>
          <table className="w-full border-collapse border border-gray-300">
            <thead>
              <tr className="bg-gray-100">
                <th className="border border-gray-300 p-2 text-right">Lines</th>
                <th className="border border-gray-300 p-2 text-right">Amount</th>
                <th className="border border-gray-300 p-2 text-right">Tax</th>
                <th className="border border-gray-300 p-2 text-right">Freight</th>
                <th className="border border-gray-300 p-2 text-right">Order Total</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border border-gray-300 p-2 text-right">{invoice?.order_num || 'N/A'}</td>
                <td className="border border-gray-300 p-2 text-right">${invoice?.amount?.toFixed(2) || '0.00'}</td>
                <td className="border border-gray-300 p-2 text-right">${invoice?.sales_tax?.toFixed(2) || '0.00'}</td>
                <td className="border border-gray-300 p-2 text-right">${invoice?.ship_total?.toFixed(2) || '0.00'}</td>
                <td className="border border-gray-300 p-2 text-right font-bold">${invoice?.total?.toFixed(2) || '0.00'}</td>
              </tr>
            </tbody>
          </table>
        </ComponentCard>

        {/* Product Tree Placeholder */}
        <ComponentCard>
          <h3 className="text-lg font-semibold mb-4">Product Tree</h3>
          <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded">
            Product Tree Component - Placeholder
          </div>
        </ComponentCard>

        {/* Items List Placeholder */}
        <ComponentCard>
          <h3 className="text-lg font-semibold mb-4">Items List</h3>
          <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded">
            Items List Component - Placeholder
          </div>
        </ComponentCard>

        {/* Invoice Lines List Placeholder */}
        <ComponentCard>
          <h3 className="text-lg font-semibold mb-4">Invoice Lines</h3>
          <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded">
            Invoice Lines List Component - Placeholder
          </div>
        </ComponentCard>

        {/* QA List */}
        <ComponentCard>
          <QAList entityType="invoice" entityId={invoice?.id} />
        </ComponentCard>

        {/* QA Form Placeholder */}
        <ComponentCard>
          <h3 className="text-lg font-semibold mb-4">QA Form</h3>
          <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded">
            QA Form Component - Placeholder (Modal for editing QA)
          </div>
        </ComponentCard>

        {/* Invoice Line Popup Placeholder */}
        <ComponentCard>
          <h3 className="text-lg font-semibold mb-4">Invoice Line Popup</h3>
          <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded">
            Invoice Line Popup Component - Placeholder
          </div>
        </ComponentCard>
      </div>
    </>
  );
}
