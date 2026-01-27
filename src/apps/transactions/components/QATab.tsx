import React, { useState } from "react";

interface QAItem {
  question: string;
  answer: string;
}

const QATab: React.FC = () => {
  const [qaList, setQAList] = useState<QAItem[]>([]);
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [adding, setAdding] = useState(false);
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [editQuestion, setEditQuestion] = useState("");
  const [editAnswer, setEditAnswer] = useState("");

  const handleAddQA = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || !answer.trim()) return;
    setQAList([...qaList, { question, answer }]);
    setQuestion("");
    setAnswer("");
    setAdding(false);
  };

  const handleDeleteQA = (idx: number) => {
    setQAList(qaList.filter((_, i) => i !== idx));
    if (expandedIdx === idx) setExpandedIdx(null);
    if (editingIdx === idx) setEditingIdx(null);
  };

  const handleEditQA = (idx: number) => {
    setEditingIdx(idx);
    setEditQuestion(qaList[idx].question);
    setEditAnswer(qaList[idx].answer);
  };

  const handleSaveEditQA = (idx: number) => {
    if (!editQuestion.trim() || !editAnswer.trim()) return;
    setQAList(
      qaList.map((qa, i) =>
        i === idx ? { question: editQuestion, answer: editAnswer } : qa,
      ),
    );
    setEditingIdx(null);
  };

  return (
    <div className="w-full mt-8 p-6 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 shadow">
      <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
        QA List
      </h3>
      <div className="mb-6">
        {qaList.length === 0 && (
          <div className="text-slate-400">No Q&A yet.</div>
        )}
        {qaList.map((qa, idx) => (
          <div
            key={idx}
            className="mb-2 border-b border-slate-200 dark:border-slate-700"
          >
            <div className="flex justify-between items-center">
              <button
                type="button"
                className="flex-1 text-left py-2 px-2 font-medium text-slate-800 dark:text-slate-200 focus:outline-none flex justify-between items-center"
                onClick={() => setExpandedIdx(expandedIdx === idx ? null : idx)}
              >
                <span>{qa.question}</span>
                <span className="ml-2 text-xs">
                  {expandedIdx === idx ? "▲" : "▼"}
                </span>
              </button>
              <div className="flex gap-2 ml-2">
                <button
                  type="button"
                  className="text-blue-600 hover:underline text-xs"
                  onClick={() => handleEditQA(idx)}
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="text-red-600 hover:underline text-xs"
                  onClick={() => handleDeleteQA(idx)}
                >
                  Delete
                </button>
              </div>
            </div>
            {editingIdx === idx ? (
              <form
                className="py-2 px-4 bg-slate-50 dark:bg-slate-900/30 rounded"
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSaveEditQA(idx);
                }}
              >
                <div className="mb-2">
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Question
                  </label>
                  <input
                    type="text"
                    value={editQuestion}
                    onChange={(e) => setEditQuestion(e.target.value)}
                    className="w-full rounded border border-slate-300 dark:border-slate-600 px-2 py-1 text-xs bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                    required
                  />
                </div>
                <div className="mb-2">
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Answer
                  </label>
                  <textarea
                    value={editAnswer}
                    onChange={(e) => setEditAnswer(e.target.value)}
                    className="w-full rounded border border-slate-300 dark:border-slate-600 px-2 py-1 text-xs bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
                    required
                    rows={2}
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-xs font-medium"
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    className="px-3 py-1 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded text-xs font-medium"
                    onClick={() => setEditingIdx(null)}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : expandedIdx === idx ? (
              <div className="py-2 px-4 text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-900/30 rounded">
                {qa.answer}
              </div>
            ) : null}
          </div>
        ))}
      </div>
      {adding ? (
        <form onSubmit={handleAddQA} className="space-y-3 mb-2">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Question
            </label>
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              className="w-full rounded border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
              placeholder="Enter question"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Answer
            </label>
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              className="w-full rounded border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
              placeholder="Enter answer"
              required
              rows={2}
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium"
            >
              Add
            </button>
            <button
              type="button"
              className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded text-sm font-medium"
              onClick={() => setAdding(false)}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button
          type="button"
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium"
          onClick={() => setAdding(true)}
        >
          + Add Q&A
        </button>
      )}
    </div>
  );
};

export default QATab;
