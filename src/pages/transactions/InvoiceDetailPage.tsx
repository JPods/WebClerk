import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router";

import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import ComponentCard from "../../components/common/ComponentCard";
import InvoiceForm from "../../components/InvoiceForm";
import QAList from "../../components/QAList";
import LineItemModal from "../../components/modals/LineItemModal";
import { getRecord } from "../../api/wcapi";
import { firstAvailableValue } from "../../utils/optionUtils";

const InvoiceDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [invoice, setInvoice] = useState<any>(null);
  const [lines, setLines] = useState<any[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [addresses, setAddresses] = useState<any[]>([]);
  const [phones, setPhones] = useState<any[]>([]);
  const [emails, setEmails] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedLine, setSelectedLine] = useState<any | null>(null);
  const [isLineModalOpen, setIsLineModalOpen] = useState(false);

  const fetchInvoice = useCallback(async () => {
    if (!id) {
      setInvoice(null);
      setLines([]);
      setCustomers([]);
      setAddresses([]);
      setPhones([]);
      setEmails([]);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await getRecord("invoice", Number(id));
      setInvoice(res?.record ?? null);
      const rel = res?.related || {};
      const detected = rel["invoice_line"] || rel["invoice_lines"] || [];
      setLines(Array.isArray(detected) ? detected : []);
      setCustomers(Array.isArray(rel["customers"]) ? rel["customers"] : []);
      setAddresses(Array.isArray(rel["addresses"]) ? rel["addresses"] : []);
      setPhones(Array.isArray(rel["phones"]) ? rel["phones"] : []);
      setEmails(Array.isArray(rel["emails"]) ? rel["emails"] : []);
    } catch (err: any) {
      setError(err?.message || "failed to load invoice");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchInvoice();
  }, [fetchInvoice]);

  const lineColumns = useMemo(() => {
    if (!lines.length) {
      return [] as string[];
    }
    const preferred = ["line_no", "item_id", "description", "qty", "price", "amount"];
    const keys = Object.keys(lines[0] || {});
    const cols = preferred.filter((key) => keys.includes(key));
    return cols.length ? cols : keys.slice(0, 8);
  }, [lines]);

  const openLineModal = (line: any) => {
    setSelectedLine(line);
    setIsLineModalOpen(true);
  };

  const closeLineModal = () => {
    setIsLineModalOpen(false);
    setSelectedLine(null);
  };

  const lineModalFields = useMemo(() => {
    if (!selectedLine) {
      return [];
    }
    return [
      { label: "item_num", value: firstAvailableValue(selectedLine, ["item_num", "itemNum"]) },
      { label: "qty_ordered", value: firstAvailableValue(selectedLine, ["qty_ordered", "qtyOrdered"]) },
      { label: "qty_change", value: firstAvailableValue(selectedLine, ["qty_change", "qtyChange"]) },
      { label: "unit_price", value: firstAvailableValue(selectedLine, ["unit_price", "unitPrice"]) },
      { label: "discount", value: firstAvailableValue(selectedLine, ["discount"]) },
      { label: "extended_price", value: firstAvailableValue(selectedLine, ["extended_price", "extendedPrice"]) },
      { label: "description", value: firstAvailableValue(selectedLine, ["description", "Description"]) },
    ];
  }, [selectedLine]);

  const lineModalImage = useMemo(() => {
    if (!selectedLine) {
      return "";
    }
    return firstAvailableValue(selectedLine, ["photo", "image_url", "imageUrl"]);
  }, [selectedLine]);

  if (loading) {
    return <div className="p-4 text-sm text-gray-500">loading invoice...</div>;
  }

  if (error) {
    return <div className="p-4 text-sm text-red-600">{error}</div>;
  }

  return (
    <>
      <PageBreadcrumb pageTitle="Invoice Details" />
      <div className="space-y-6">
        <ComponentCard>
          <div className="rounded bg-yellow-100 p-4 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
            locked box component - placeholder
          </div>
        </ComponentCard>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <ComponentCard>
            <div className="p-4">
              <label className="mb-2 block text-sm font-medium">customer_name_search</label>
              <input
                type="text"
                className="w-full rounded border border-gray-300 p-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                placeholder="customer_name_search"
              />
            </div>
          </ComponentCard>
          <ComponentCard>
            <div className="flex items-center justify-between p-4">
              <div className="text-sm">
                <p>
                  <strong>sales_order_number:</strong> {invoice?.order_num || "n/a"}
                </p>
                <p>
                  <strong>customer_po_number:</strong> {invoice?.customer_po || "n/a"}
                </p>
              </div>
              <button className="rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600">print</button>
            </div>
          </ComponentCard>
        </div>

        <InvoiceForm
          modeProp={id ? "edit" : "add"}
          dataProp={invoice}
          onSaved={fetchInvoice}
        />

        <ComponentCard>
          <h3 className="mb-4 text-lg font-semibold">order_totals</h3>
          <table className="w-full border-collapse border border-gray-300 text-sm dark:border-gray-700">
            <thead className="bg-gray-100 dark:bg-gray-800">
              <tr>
                <th className="border border-gray-300 p-2 text-right dark:border-gray-700">lines</th>
                <th className="border border-gray-300 p-2 text-right dark:border-gray-700">amount</th>
                <th className="border border-gray-300 p-2 text-right dark:border-gray-700">tax</th>
                <th className="border border-gray-300 p-2 text-right dark:border-gray-700">freight</th>
                <th className="border border-gray-300 p-2 text-right dark:border-gray-700">order_total</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border border-gray-300 p-2 text-right dark:border-gray-700">{lines.length}</td>
                <td className="border border-gray-300 p-2 text-right dark:border-gray-700">
                  ${invoice?.amount?.toFixed?.(2) ?? "0.00"}
                </td>
                <td className="border border-gray-300 p-2 text-right dark:border-gray-700">
                  ${invoice?.sales_tax?.toFixed?.(2) ?? "0.00"}
                </td>
                <td className="border border-gray-300 p-2 text-right dark:border-gray-700">
                  ${invoice?.ship_total?.toFixed?.(2) ?? "0.00"}
                </td>
                <td className="border border-gray-300 p-2 text-right font-semibold dark:border-gray-700">
                  ${invoice?.total?.toFixed?.(2) ?? "0.00"}
                </td>
              </tr>
            </tbody>
          </table>
        </ComponentCard>

        <ComponentCard>
          <div className="grid gap-4 text-sm md:grid-cols-2">
            <div>
              <h4 className="mb-1 font-medium text-gray-600 dark:text-gray-300">customers</h4>
              {customers.length === 0 ? (
                <div className="text-xs text-gray-400 dark:text-gray-500">no customers linked</div>
              ) : (
                <ul className="list-disc list-inside text-xs">
                  {customers.map((customer, index) => (
                    <li key={index}>{customer?.display_name || customer?.name || customer?.id}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h4 className="mb-1 font-medium text-gray-600 dark:text-gray-300">phones</h4>
              {phones.length === 0 ? (
                <div className="text-xs text-gray-400 dark:text-gray-500">no phones linked</div>
              ) : (
                <ul className="list-disc list-inside text-xs">
                  {phones.map((phone, index) => (
                    <li key={index}>{phone?.number || phone?.name || phone?.id}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h4 className="mb-1 font-medium text-gray-600 dark:text-gray-300">emails</h4>
              {emails.length === 0 ? (
                <div className="text-xs text-gray-400 dark:text-gray-500">no emails linked</div>
              ) : (
                <ul className="list-disc list-inside text-xs">
                  {emails.map((email, index) => (
                    <li key={index}>{email?.email || email?.name || email?.id}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h4 className="mb-1 font-medium text-gray-600 dark:text-gray-300">addresses</h4>
              {addresses.length === 0 ? (
                <div className="text-xs text-gray-400 dark:text-gray-500">no addresses linked</div>
              ) : (
                <ul className="list-disc list-inside text-xs">
                  {addresses.map((address, index) => (
                    <li key={index}>{address?.display || address?.address1 || address?.id}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </ComponentCard>

        <ComponentCard>
          <h3 className="mb-2 text-lg font-semibold">invoice_lines</h3>
          {lines.length === 0 ? (
            <div className="text-sm text-gray-500 dark:text-gray-400">no lines</div>
          ) : (
            <div className="overflow-auto">
              <table className="min-w-full text-xs">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    {lineColumns.map((column) => (
                      <th
                        key={column}
                        className="border-b px-2 py-1 text-left font-semibold text-gray-700 dark:border-gray-700 dark:text-gray-200"
                      >
                        {column}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {lines.map((line, index) => (
                    <tr
                      key={index}
                      className="cursor-pointer odd:bg-white even:bg-gray-50 transition hover:bg-blue-50 dark:odd:bg-gray-900 dark:even:bg-gray-800 dark:hover:bg-gray-700"
                      onClick={() => openLineModal(line)}
                    >
                      {lineColumns.map((column) => (
                        <td key={column} className="border-b px-2 py-1 dark:border-gray-800">
                          {String(line?.[column] ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </ComponentCard>

        <ComponentCard>
          <QAList entityType="invoice" entityId={invoice?.id} />
        </ComponentCard>

        <LineItemModal
          isOpen={isLineModalOpen}
          onClose={closeLineModal}
          title={firstAvailableValue(selectedLine, ["description", "Description", "item_num", "itemNum"]) || "invoice_line"}
          fields={lineModalFields}
          imageUrl={lineModalImage || null}
        />
      </div>
    </>
  );
};

export default InvoiceDetailPage;
