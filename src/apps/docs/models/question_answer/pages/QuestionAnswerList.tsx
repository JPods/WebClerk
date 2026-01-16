import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import AdvancedDataTable from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { getRecords } from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrashAlt } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { deleteRecord } from "@/api/wcapi";
import QuestionAnswerDisplay from "./QuestionAnswerDisplay";

export default function QuestionAnswerList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedQuestionAnswer, setSelectedQuestionAnswer] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

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

  return (
    <>
      <PageBreadcrumb pageTitle="Question Answer List" />
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
              columns={userColumns}
              data={data}
              storageKey="question_answer_list"
              loading={loading}
              onRowActivate={handleEdit}
            />
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