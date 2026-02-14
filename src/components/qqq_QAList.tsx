import { useEffect, useState } from "react";
import DataTable, { TableColumn } from 'react-data-table-component';
import { getRecords } from "../api/wcapi";

interface QA {
  id: number;
  seq: number;
  question: string;
  answer: string;
  url: string;
  imagePath: string;
  idGroup: number;
}

interface QAListProps {
  entityType?: string; // 'contact', 'sales_order', etc.
  entityId?: number;
}

export default function QAList({ entityType, entityId }: QAListProps) {
  const [data, setData] = useState<QA[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (entityType && entityId) {
      fetchQA();
    }
  }, [entityType, entityId]);

  const fetchQA = async () => {
    setLoading(true);
    try {
      // Assuming QA is a separate model or related
      // For now, placeholder
      const qaData: QA[] = [
        { id: 1, seq: 1, question: 'Sample Question', answer: 'Sample Answer', url: '', imagePath: '', idGroup: 1 },
      ];
      setData(qaData);
    } catch (error) {
      console.error("Failed to fetch QA", error);
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  const columns: TableColumn<QA>[] = [
    { name: 'Seq', selector: (row) => row.seq, sortable: true },
    { name: 'Question', selector: (row) => row.question },
    { name: 'Answer', selector: (row) => row.answer },
    { name: 'URL', selector: (row) => row.url, cell: (row) => row.url ? <a href={row.url} target="_blank" rel="noopener noreferrer">Link</a> : '' },
    { name: 'Image', selector: (row) => row.imagePath, cell: (row) => row.imagePath ? <img src={row.imagePath} alt="QA" width="60" height="60" /> : '' },
    { name: 'Group', selector: (row) => row.idGroup, sortable: true },
  ];

  return (
    <div>
      <h5>QAs ({data.length})</h5>
      <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
        <DataTable
          columns={columns}
          data={data}
          progressPending={loading}
          pagination
          theme="default"
          highlightOnHover
          pointerOnHover
        />
      </div>
    </div>
  );
}