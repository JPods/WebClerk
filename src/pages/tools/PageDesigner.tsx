/* LastChecked: 2026-07-04 | WhereUsed: /page-designer | WhoCreated: Claude */
import { useEffect, useRef, useState } from "react";
import { useAppSelector } from "../../store/hooks";
import apiClient from "../../api/axios";

const PageDesigner: React.FC = () => {
  const editorRef = useRef<HTMLDivElement>(null);
  const editorInstance = useRef<any>(null);
  const { user } = useAppSelector((state) => state.auth);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (!editorRef.current || editorInstance.current) return;

    import("grapesjs").then((grapesjs) => {
      import("grapesjs/dist/css/grapes.min.css");

      editorInstance.current = grapesjs.default.init({
        container: editorRef.current!,
        height: "100%",
        width: "auto",
        storageManager: false,
        panels: { defaults: [] },
        blockManager: {
          appendTo: "#gjs-blocks",
          blocks: [
            { id: "section", label: "Section", content: '<section class="p-4"><h2>Section Title</h2><p>Content here</p></section>', category: "Basic" },
            { id: "text", label: "Text", content: '<p class="p-2">Insert text here</p>', category: "Basic" },
            { id: "image", label: "Image", content: '<img src="https://via.placeholder.com/350x150" alt="placeholder" />', category: "Basic" },
            { id: "link", label: "Link", content: '<a href="#" class="text-blue-600 underline">Link text</a>', category: "Basic" },
            { id: "two-col", label: "2 Columns", content: '<div class="flex gap-4"><div class="flex-1 p-2">Column 1</div><div class="flex-1 p-2">Column 2</div></div>', category: "Layout" },
            { id: "three-col", label: "3 Columns", content: '<div class="flex gap-4"><div class="flex-1 p-2">Col 1</div><div class="flex-1 p-2">Col 2</div><div class="flex-1 p-2">Col 3</div></div>', category: "Layout" },
          ],
        },
      });
    });

    return () => {
      if (editorInstance.current) {
        editorInstance.current.destroy();
        editorInstance.current = null;
      }
    };
  }, []);

  const handleSubmit = async () => {
    if (!editorInstance.current) return;

    const html = editorInstance.current.getHtml();
    const css = editorInstance.current.getCss();
    const content = `<style>${css}</style>\n${html}`;

    setSubmitting(true);
    setMessage(null);

    try {
      await apiClient.post("/wcapi/save/", {
        model_name: "alice_observation",
        data: {
          source: "page_designer",
          type: "template_submission",
          content,
          submitted_by: user?.id,
          notes,
        },
      });
      setMessage({ type: "success", text: "Template submitted to library successfully." });
      setNotes("");
    } catch (err: any) {
      setMessage({ type: "error", text: err?.message || "Submission failed." });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col h-full dark:bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Page Designer</h1>
        <div className="flex items-center gap-3">
          <input
            type="text"
            placeholder="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          />
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Submitting..." : "Submit to Library"}
          </button>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`px-4 py-2 text-sm ${message.type === "success" ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400" : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"}`}>
          {message.text}
        </div>
      )}

      {/* Editor layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Blocks panel */}
        <div id="gjs-blocks" className="w-48 overflow-y-auto border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800" />
        {/* Canvas */}
        <div ref={editorRef} className="flex-1" />
      </div>
    </div>
  );
};

export default PageDesigner;
