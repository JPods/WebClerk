import React, { useState } from "react";

const DocumentsTab: React.FC = () => {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setUploading(true);
    setMessage(null);
    // Simulate upload
    setTimeout(() => {
      setUploading(false);
      setMessage("Document uploaded!");
      setTitle("");
      setFile(null);
    }, 1000);
  };

  return (
    <div className="w-full mt-8 p-6 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 shadow">
      <h3 className="font-semibold text-slate-900 dark:text-white mb-4">
        Upload Document
      </h3>
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded border border-slate-300 dark:border-slate-600 px-3 py-2 text-sm bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
            placeholder="Document title"
            required
          />
        </div>
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Attachment
          </label>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="w-full text-sm"
            required
          />
        </div>
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm font-medium"
          disabled={uploading}
        >
          {uploading ? "Uploading..." : "Upload"}
        </button>
        {message && <div className="mt-3 text-green-600">{message}</div>}
      </form>
    </div>
  );
};

export default DocumentsTab;
