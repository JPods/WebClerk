import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import PageBreadcrumb from "../../components/common/PageBreadCrumb";
import ComponentCard from "../../components/common/ComponentCard";
import PurchaseOrderForm from "../../components/PurchaseOrderForm";
import QAList from "../../components/QAList";
import LineItemModal from "../../components/modals/LineItemModal";
import { getRecord } from "../../api/wcapi";
import { firstAvailableValue } from "../../utils/optionUtils";

const PurchaseOrderDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [purchaseOrder, setPurchaseOrder] = useState<any>(null);
  const [lines, setLines] = useState<any[]>([]);
  const [vendors, setVendors] = useState<any[]>([]);
  const [addresses, setAddresses] = useState<any[]>([]);
  const [phones, setPhones] = useState<any[]>([]);
  const [emails, setEmails] = useState<any[]>([]);
  const [selectedLine, setSelectedLine] = useState<any | null>(null);
  const [lineModalOpen, setLineModalOpen] = useState(false);

  const fetchPurchaseOrder = useCallback(async () => {
    if (!id) {
      setPurchaseOrder(null);
      setLines([]);
      setVendors([]);
      setAddresses([]);
      setPhones([]);
      setEmails([]);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const detail = await getRecord("purchase_order", Number(id));
      setPurchaseOrder(detail?.record ?? null);
      const rel = detail?.related || {};
      const detected = rel["purchase_order_lines"] || rel["purchase_order_line"] || [];
      setLines(Array.isArray(detected) ? detected : []);
      setVendors(Array.isArray(rel["vendors"]) ? rel["vendors"] : []);
      setAddresses(Array.isArray(rel["addresses"]) ? rel["addresses"] : []);
      setPhones(Array.isArray(rel["phones"]) ? rel["phones"] : []);
      setEmails(Array.isArray(rel["emails"]) ? rel["emails"] : []);
    } catch (e: any) {
      setError(e?.message || "failed to load purchase_order");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchPurchaseOrder();
  }, [fetchPurchaseOrder]);

  const lineColumns = useMemo(() => {
    if (!lines.length) return [] as string[];
    const preferred = ["line_no", "item_id", "description", "qty", "price", "amount"];
    const keys = Object.keys(lines[0] || {});
    const cols = preferred.filter((key) => keys.includes(key));
    return cols.length ? cols : keys.slice(0, 8);
  }, [lines]);

  const openLineModal = (line: any) => {
    setSelectedLine(line);
    setLineModalOpen(true);
  };

  const closeLineModal = () => {
    setLineModalOpen(false);
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
      { label: "description", value: firstAvailableValue(selectedLine, ["description"]) },
    ];
  }, [selectedLine]);

  const lineModalImage = useMemo(() => {
    if (!selectedLine) {
      return "";
    }
    return firstAvailableValue(selectedLine, ["photo", "image_url", "imageUrl"]);
  }, [selectedLine]);

  if (loading) {
    return <div className="p-4 text-sm text-gray-500">loading purchase_order...</div>;
  }

  if (error) {
    return <div className="p-4 text-sm text-red-600">{error}</div>;
  }

  return (
    <>
      <PageBreadcrumb pageTitle="Purchase Order Details" />
      <div className="space-y-6">
        <ComponentCard>
          <div className="rounded bg-yellow-100 p-4 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
            locked box component - placeholder
          </div>
        </ComponentCard>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <ComponentCard>
            <div className="p-4">
              <label className="mb-2 block text-sm font-medium">vendor_search</label>
              <input
                type="text"
                className="w-full rounded border border-gray-300 p-2 text-sm dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                placeholder="vendor_search"
              />
            </div>
          </ComponentCard>
          <ComponentCard>
            <div className="flex items-center justify-between p-4">
              <div className="text-sm">
                <p>
                  <strong>purchase_order_number:</strong> {purchaseOrder?.po_num || "n/a"}
                </p>
                <p>
                  <strong>vendor_reference:</strong> {purchaseOrder?.vendor_reference || "n/a"}
                </p>
              </div>
              <button className="rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600">print</button>
            </div>
          </ComponentCard>
        </div>

        <PurchaseOrderForm
          modeProp={id ? "edit" : "add"}
          dataProp={purchaseOrder}
          onSaved={fetchPurchaseOrder}
        />

        <ComponentCard>
          <h3 className="mb-4 text-lg font-semibold">purchase_order totals</h3>
          <table className="w-full border-collapse border border-gray-300 text-sm dark:border-gray-700">
            <thead className="bg-gray-100 dark:bg-gray-800">
              <tr>
                <th className="border border-gray-300 p-2 text-right dark:border-gray-700">lines</th>
                <th className="border border-gray-300 p-2 text-right dark:border-gray-700">amount</th>
                <th className="border border-gray-300 p-2 text-right dark:border-gray-700">tax</th>
                <th className="border border-gray-300 p-2 text-right dark:border-gray-700">freight</th>
                <th className="border border-gray-300 p-2 text-right dark:border-gray-700">purchase_order_total</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border border-gray-300 p-2 text-right dark:border-gray-700">{lines.length}</td>
                <td className="border border-gray-300 p-2 text-right dark:border-gray-700">
                  ${purchaseOrder?.amount?.toFixed?.(2) ?? "0.00"}
                </td>
                <td className="border border-gray-300 p-2 text-right dark:border-gray-700">
                  ${purchaseOrder?.sales_tax?.toFixed?.(2) ?? "0.00"}
                </td>
                <td className="border border-gray-300 p-2 text-right dark:border-gray-700">
                  ${purchaseOrder?.ship_total?.toFixed?.(2) ?? "0.00"}
                </td>
                <td className="border border-gray-300 p-2 text-right font-semibold dark:border-gray-700">
                  ${purchaseOrder?.total?.toFixed?.(2) ?? "0.00"}
                </td>
              </tr>
            </tbody>
          </table>
        </ComponentCard>

        <ComponentCard>
          <div className="grid gap-4 text-sm md:grid-cols-2">
            <div>
              <h4 className="mb-1 font-medium text-gray-600 dark:text-gray-300">vendors</h4>
              {vendors.length === 0 ? (
                <div className="text-xs text-gray-400 dark:text-gray-500">no vendors linked</div>
              ) : (
                <ul className="list-disc list-inside text-xs">
                  {vendors.map((vendor, index) => (
                    <li key={index}>{vendor?.display_name || vendor?.name || vendor?.id}</li>
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
          <h3 className="mb-2 text-lg font-semibold">purchase_order lines</h3>
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
          <QAList entityType="purchase_order" entityId={purchaseOrder?.id} />
        </ComponentCard>
        <LineItemModal
          isOpen={lineModalOpen}
          onClose={closeLineModal}
          title={firstAvailableValue(selectedLine, ["description", "item_num", "itemNum"]) || "purchase_order_line"}
          fields={lineModalFields}
          imageUrl={lineModalImage || null}
        />
      </div>
    </>
  );
};

export default PurchaseOrderDetailPage;
