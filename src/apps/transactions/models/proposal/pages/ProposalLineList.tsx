/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import { useEffect, useState } from "react";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import ComponentCard from "../../../../../components/common/ComponentCard";
import { ProposalLine } from "../types/proposalLineType";
import { useColumnContextMenu } from "@/hooks/useColumnContextMenu";

interface ProposalLineListProps {
  proposalId: number;
  onEdit?: (line: ProposalLine) => void;
  onView?: (line: ProposalLine) => void;
  onAdd?: () => void;
  onDelete?: (lineId: number) => void;
}

export default function ProposalLineList({
  proposalId,
  onEdit,
  onView,
  onAdd,
  onDelete
}: ProposalLineListProps) {
  const [lines, setLines] = useState<ProposalLine[]>([]);
  const [loading, setLoading] = useState(false);

  // Placeholder data - in real implementation, fetch from API
  useEffect(() => {
    setLoading(true);
    // Simulate API call
    setTimeout(() => {
      setLines([
        {
          id: 1,
          parent_id: proposalId,
          parent_ref_id: proposalId,
          item: { description: "Sample Item 1" },
          quantity: { staged: 10 },
          price: { unit: 100 },
          cost: { unit: 80 },
          dt_created: new Date().toISOString(),
          dt_modified: new Date().toISOString(),
          version: 1
        }
      ]);
      setLoading(false);
    }, 500);
  }, [proposalId]);

  const columns: any[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "10%" },
    {
      name: "Item",
      selector: (row) => row.item?.description || "--",
      sortable: true,
      width: "30%"
    },
    {
      name: "Quantity",
      selector: (row) => row.quantity?.staged || 0,
      sortable: true,
      width: "15%"
    },
    {
      name: "Unit Price",
      selector: (row) => row.price?.unit || 0,
      sortable: true,
      width: "15%"
    },
    {
      name: "Actions",
      cell: (row) => (
        <div className="flex gap-2">
          {onView && (
            <button onClick={() => onView(row)} title="View">
              <FaEye className="text-blue-600 hover:scale-110 transition" />
            </button>
          )}
          {onEdit && (
            <button onClick={() => onEdit(row)} title="Edit">
              <FaEdit className="text-green-600 hover:scale-110 transition" />
            </button>
          )}
          {onDelete && (
            <button onClick={() => onDelete(row.id)} title="Delete">
              <FaTrash className="text-red-600 hover:scale-110 transition" />
            </button>
          )}
        </div>
      ),
      ignoreRowClick: true,
      allowOverflow: true,
      button: true,
      width: "20%"
    }
  ];


  const columnCtx = useColumnContextMenu("proposal_line_list", columns);
  return (
    <ComponentCard>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Proposal Lines</h3>
        {onAdd && (
          <button
            onClick={onAdd}
            className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600"
          >
            <FaPlus />
            Add Line
          </button>
        )}
      </div>
      <div className="overflow-x-auto">
        <DataGrid
          columns={columns.map((col) => ({
            ...col,
            name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
          }))}
          data={lines}
          storageKey="proposal_line_list"
          onRowActivate={onEdit}
          loading={loading}
              allFields={columnCtx.allFields}
              namedViews={columnCtx.namedViews}
              onDeleteColumn={columnCtx.onDeleteColumn}
              onAddColumn={columnCtx.onAddColumn}
              onSaveLayout={columnCtx.onSaveLayout}
              onSaveLayoutAs={columnCtx.onSaveLayoutAs}
              onLoadView={columnCtx.onLoadView}
        />
      </div>
    </ComponentCard>
  );
}