#!/usr/bin/env node
/**
 * List Migration Generator
 * 
 * Generates AdvancedDataTable-based list components from existing files.
 * Run with: node src/tools/generate-list-migration.js
 * 
 * This is a TEMPLATE GENERATOR - review and customize the output for each model.
 */

const fs = require('fs');
const path = require('path');

// Configuration for each model
const MODEL_CONFIGS = {
  // Products
  'catalog': { title: 'Catalog', fields: ['id', 'name', 'code', 'category'] },
  'usage': { title: 'Usage', fields: ['id', 'item', 'quantity', 'date'] },
  'specification': { title: 'Specification', fields: ['id', 'name', 'value', 'item'] },
  'matrics': { title: 'Matrics', fields: ['id', 'name', 'value', 'unit'] },
  'org_item': { title: 'Org Item', fields: ['id', 'org', 'item', 'price'] },
  'variant': { title: 'Variant', fields: ['id', 'item', 'sku', 'name'] },
  'bill_of_material': { title: 'Bill of Material', fields: ['id', 'item', 'component', 'quantity'] },
  'service': { title: 'Service', fields: ['id', 'name', 'code', 'price'] },
  'warehouse': { title: 'Warehouse', fields: ['id', 'name', 'code', 'location'] },
  'item_xref': { title: 'Item XRef', fields: ['id', 'item', 'xref_type', 'xref_value'] },
  'serial': { title: 'Serial', fields: ['id', 'item', 'serial_number', 'status'] },
  'flow': { title: 'Flow', fields: ['id', 'name', 'type', 'status'] },
  
  // Core
  'template': { title: 'Template', fields: ['id', 'name', 'type', 'content'] },
  'report': { title: 'Report', fields: ['id', 'name', 'type', 'status'] },
  'setting': { title: 'Setting', fields: ['id', 'name', 'value', 'category'] },
  
  // Docs
  'question_answer': { title: 'Question Answer', fields: ['id', 'question', 'answer', 'category'] },
  'linkage_index': { title: 'Linkage Index', fields: ['id', 'source', 'target', 'type'] },
  'document': { title: 'Document', fields: ['id', 'name', 'type', 'status'] },
  'tag': { title: 'Tag', fields: ['id', 'name', 'color', 'category'] },
  'linkage': { title: 'Linkage', fields: ['id', 'source', 'target', 'type'] },
  
  // Orgs
  'organization': { title: 'Organization', fields: ['id', 'name', 'org_type', 'status', 'is_active'] },
  'manufacturer': { title: 'Manufacturer', fields: ['id', 'name', 'code', 'status'] },
  'base_org_model': { title: 'Base Org Model', fields: ['id', 'name', 'type'] },
  'rep': { title: 'Rep', fields: ['id', 'name', 'code', 'territory'] },
  'employee': { title: 'Employee', fields: ['id', 'name', 'email', 'department', 'is_active'] },
  
  // Transactions
  'requisition': { title: 'Requisition', fields: ['id', 'req_no', 'status', 'date', 'total'] },
  'workorder': { title: 'Work Order', fields: ['id', 'wo_no', 'status', 'date', 'total'] },
  'project': { title: 'Project', fields: ['id', 'name', 'status', 'start_date', 'end_date'] },
  'purchase_receipt': { title: 'Purchase Receipt', fields: ['id', 'receipt_no', 'po', 'date', 'status'] },
  
  // Accounts
  'ledger': { title: 'Ledger', fields: ['id', 'name', 'code', 'type', 'balance'] },
  'tax_jurisdiction': { title: 'Tax Jurisdiction', fields: ['id', 'name', 'code', 'rate'] },
  'gl_journal': { title: 'GL Journal', fields: ['id', 'date', 'description', 'debit', 'credit'] },
  'term': { title: 'Term', fields: ['id', 'name', 'days', 'discount'] },
  'audit': { title: 'Audit', fields: ['id', 'action', 'user', 'timestamp', 'model'] },
  'exchange_transaction': { title: 'Exchange Transaction', fields: ['id', 'date', 'from_currency', 'to_currency', 'rate'] },
  'gl_account': { title: 'GL Account', fields: ['id', 'code', 'name', 'type', 'balance'] },
  'exchange_rate': { title: 'Exchange Rate', fields: ['id', 'from_currency', 'to_currency', 'rate', 'date'] },
  
  // Support/Campaign
  'campaign': { title: 'Campaign', fields: ['id', 'name', 'status', 'start_date', 'end_date'] },
  
  // Sync
  'connection': { title: 'Connection', fields: ['id', 'name', 'type', 'status'] },
  'bundle': { title: 'Bundle', fields: ['id', 'name', 'items', 'status'] },
  
  // Communications
  'location': { title: 'Location', fields: ['id', 'name', 'address', 'city', 'country'] },
  'phone': { title: 'Phone', fields: ['id', 'number', 'type', 'is_primary'] },
  'domain': { title: 'Domain', fields: ['id', 'name', 'status'] },
  'email': { title: 'Email', fields: ['id', 'address', 'type', 'is_primary'] },
};

function generateListComponent(modelName, config) {
  const pascalName = modelName.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join('');
  const camelName = modelName.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
  
  const columns = config.fields.map((field, idx) => {
    const width = idx === 0 ? '80px' : `${Math.floor(80 / (config.fields.length - 1))}%`;
    return `    { id: "${field}", name: "${field.charAt(0).toUpperCase() + field.slice(1).replace(/_/g, ' ')}", selector: (row) => row.${field} || "--", sortable: true, width: "${width}" },`;
  }).join('\n');

  return `import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetch${pascalName}s, delete${pascalName} } from "../services/${camelName}Api";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import ${pascalName}Detail from "./${pascalName}Detail";

export default function ${pascalName}List() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selected${pascalName}, setSelected${pascalName}] = useState<any | null>(null);
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch${pascalName}s();
      if (res.status === 200) {
        setData(res.data?.items || res.data?.data?.results || res.data?.results || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch ${config.title.toLowerCase()}s", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch ${config.title.toLowerCase()}s", error);
      dispatch(showToast({ message: "Failed to fetch ${config.title.toLowerCase()}s", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getData();
  }, [getData]);

  const handleView = useCallback((row: any) => {
    setSelected${pascalName}(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelected${pascalName}(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelected${pascalName}(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getData();
    setFormMode(null);
    setSelected${pascalName}(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelected${pascalName}(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(\`Delete ${config.title.toLowerCase()} \${row.name || row.id}?\`)) return;
    
    try {
      await delete${pascalName}(row.id);
      dispatch(showToast({ message: "${config.title} deleted successfully", type: "success" }));
      getData();
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete ${config.title.toLowerCase()}", type: "error" }));
    }
  }, [dispatch, getData]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedItems.length) return;
    if (!window.confirm(\`Delete \${selectedItems.length} ${config.title.toLowerCase()}(s)?\`)) return;

    try {
      await Promise.all(selectedItems.map((item) => delete${pascalName}(item.id)));
      dispatch(showToast({ message: \`\${selectedItems.length} ${config.title.toLowerCase()}(s) deleted\`, type: "success" }));
      getData();
      setSelectedItems([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some ${config.title.toLowerCase()}s", type: "error" }));
    }
  }, [selectedItems, dispatch, getData]);

  const columns: TableColumn<any>[] = useMemo(() => [
${columns}
    {
      id: "actions",
      name: "Actions",
      cell: (row) => (
        <div className="flex gap-2">
          <button onClick={() => handleView(row)} title="View">
            <FaEye className="text-blue-600 hover:scale-110 transition" />
          </button>
          <button onClick={() => handleEdit(row)} title="Edit">
            <FaEdit className="text-green-600 hover:scale-110 transition" />
          </button>
          <button onClick={() => handleDelete(row)} title="Delete">
            <FaTrash className="text-red-600 hover:scale-110 transition" />
          </button>
        </div>
      ),
      ignoreRowClick: true,
      allowOverflow: true,
      button: true,
      width: "100px",
    },
  ], [handleDelete, handleEdit, handleView]);

  return (
    <>
      <PageBreadcrumb pageTitle="${config.title} List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="${config.title}s"
              loading={loading}
              storageKey="${modelName}-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedItems}
              exportFileName="${modelName}s_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search ${config.title.toLowerCase()}s..."
              noDataMessage="No ${config.title.toLowerCase()}s found"
              customActions={
                <div className="flex gap-2">
                  {selectedItems.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedItems.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add ${config.title}
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <${pascalName}Detail
              inline
              modeProp={formMode}
              dataProp={selected${pascalName}}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
`;
}

// Generate all components
console.log('List Migration Generator\n');
console.log('Available models:', Object.keys(MODEL_CONFIGS).join(', '));
console.log('\nTo generate a specific model, modify this script or use it as a template.');
