import ComponentCard from "@/components/common/ComponentCard";
import AdvancedDataTable, { type AdvancedDataTableHandle } from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useRef} from "react";
import { getRecords } from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrashAlt } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { deleteRecord } from "@/api/wcapi";
import QuestionAnswerDisplay from "./QuestionAnswerDisplay";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function QuestionAnswerList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedQuestionAnswer, setSelectedQuestionAnswer] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<AdvancedDataTableHandle<any>>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const dispatch = useDispatch();

  const getQuestionAnswerData = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getRecords('question_answer');
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Failed to fetch question answers", error);
      dispatch(showToast({ message: "Failed to fetch question answers", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getQuestionAnswerData();
  }, [getQuestionAnswerData]);

  // Handle database search
  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    const query = terms.join(' ');
    setLoading(true);
    try {
      const list = await getRecords('question_answer', { search: query });
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Database search error:", error);
      dispatch(showToast({ message: "Search failed", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  const handleView = (row: any) => {
    setSelectedQuestionAnswer(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedQuestionAnswer(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedQuestionAnswer(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getQuestionAnswerData();
    setFormMode(null);
    setSelectedQuestionAnswer(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedQuestionAnswer(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete question answer ${row.id}?`)) {
      try {
        await deleteRecord('question_answer', row.id);
        dispatch(showToast({ message: "Question Answer deleted successfully", type: "success" }));
        getQuestionAnswerData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete question answer", type: "error" }));
      }
    }
  };

  // Hardcoded columns: id and common fields
  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "10%" },
    { name: "Question", selector: (row) => row.question || "--", sortable: true, width: "40%" },
    { name: "Answer", selector: (row) => row.answer || "--", sortable: true, width: "40%" },
    { name: "Status", selector: (row) => row.status || "--", sortable: true, width: "10%" },
  ];

  userColumns.push({
    name: "Action",
    cell: (row) => (
      <div className="flex gap-2">
        <button onClick={() => handleView(row)} title="View">
          <FaEye className="text-blue-600 hover:scale-110 transition" />
        </button>
        <button onClick={() => handleEdit(row)} title="Edit">
          <FaEdit className="text-green-600 hover:scale-110 transition" />
        </button>
        <button onClick={() => handleDelete(row)} title="Delete">
          <FaTrashAlt className="text-red-600 hover:scale-110 transition" />
        </button>
      </div>
    ),
    ignoreRowClick: true,
    allowOverflow: true,
    button: true,
  });

  // Filter data based on filterValues from ButtonToolbar
  const filteredData = useMemo(() => {
    if (Object.keys(filterValues).length === 0) return data;
    return data.filter((row: any) => {
      return Object.entries(filterValues).every(([key, value]) => {
        if (!value) return true;
        const rowValue = String(row[key] || "").toLowerCase();
        return rowValue.includes(value.toLowerCase());
      });
    });
  }, [data, filterValues]);

  // Filter columns based on visibility from ButtonToolbar
  const visibleColumns = useMemo(() => {
    if (columnVisibility.length === 0) return columns;
    return columns.filter((_: any, index: number) => columnVisibility[index] !== false);
  }, [columns, columnVisibility]);
  return (
    <>
      <ButtonToolbar
        pageTitle="Question Answer List"
        title="Question Answer"
        modelKey="question_answer"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getQuestionAnswerData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="question_answer-list"
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
      />
<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Question Answer
              </button>
            </div>
            <AdvancedDataTable
              ref={tableRef}
              columns={userColumns}
              data={filteredData}
              storageKey="question_answer_list"
              loading={loading}
              onRowActivate={handleEdit}
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
            
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              hideHeader={true}/>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <QuestionAnswerDisplay
              inline
              modeProp={formMode}
              dataProp={selectedQuestionAnswer}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}