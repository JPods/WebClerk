/**
 * PrintPreviewModal - Preview document before printing
 * Shows formatted document with print options
 */
import React, { useState, useRef } from "react";
import {
  FaTimes,
  FaPrint,
  FaDownload,
  FaExpand,
  FaCompress,
  FaCog,
  FaEnvelope,
} from "react-icons/fa";

interface PrintOptions {
  showPrices: boolean;
  showCosts: boolean;
  showNotes: boolean;
  showTerms: boolean;
  copies: number;
  paperSize: "letter" | "a4";
}

interface PrintPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentType: string;
  documentNumber: string;
  children: React.ReactNode;
  onPrint?: (options: PrintOptions) => void;
  onEmail?: () => void;
  onDownloadPdf?: () => void;
}

const PrintPreviewModal: React.FC<PrintPreviewModalProps> = ({
  isOpen,
  onClose,
  documentType,
  documentNumber,
  children,
  onPrint,
  onEmail,
  onDownloadPdf,
}) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showOptions, setShowOptions] = useState(false);
  const [options, setOptions] = useState<PrintOptions>({
    showPrices: true,
    showCosts: false,
    showNotes: true,
    showTerms: true,
    copies: 1,
    paperSize: "letter",
  });
  const printRef = useRef<HTMLDivElement>(null);

  if (!isOpen) return null;

  const handlePrint = () => {
    if (onPrint) {
      onPrint(options);
    } else {
      const previewNode = printRef.current;
      if (!previewNode) {
        window.print();
        return;
      }

      const printWindow = window.open("", "_blank", "width=1024,height=768");
      if (!printWindow) {
        window.print();
        return;
      }

      const styles = Array.from(
        document.querySelectorAll('style, link[rel="stylesheet"]'),
      )
        .map((node) => node.outerHTML)
        .join("\n");

      const pageSize = options.paperSize === "a4" ? "A4" : "Letter";

      printWindow.document.open();
      printWindow.document.write(`
        <!doctype html>
        <html>
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Print ${documentType} ${documentNumber}</title>
            ${styles}
            <style>
              @page { size: ${pageSize}; margin: 0; }
              html, body {
                margin: 0;
                padding: 0;
                background: white;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
              }
            </style>
          </head>
          <body>
            ${previewNode.innerHTML}
          </body>
        </html>
      `);
      printWindow.document.close();

      const runPrint = () => {
        printWindow.focus();
        printWindow.print();
        printWindow.close();
      };

      if (printWindow.document.readyState === "complete") {
        setTimeout(runPrint, 150);
      } else {
        printWindow.onload = () => setTimeout(runPrint, 150);
      }
    }
  };

  const updateOption = <K extends keyof PrintOptions>(
    key: K,
    value: PrintOptions[K],
  ) => {
    setOptions((prev) => ({ ...prev, [key]: value } as PrintOptions));
  };

  return (
    <div
      className={`fixed inset-0 z-50 ${
        isFullscreen ? "" : "flex items-center justify-center"
      }`}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 print:hidden" onClick={onClose} />

      {/* Modal */}
      <div
        className={`relative bg-white dark:bg-slate-800 shadow-xl flex flex-col ${
          isFullscreen
            ? "w-full h-full"
            : "w-full max-w-5xl max-h-[90vh] rounded-lg"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 print:hidden">
          <div className="flex items-center gap-3">
            <FaPrint className="text-slate-400" />
            <div>
              <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                Print Preview
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {documentType} #{documentNumber}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Options toggle */}
            <button
              onClick={() => setShowOptions(!showOptions)}
              className={`p-2 rounded-lg transition-colors ${
                showOptions
                  ? "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
                  : "text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700"
              }`}
              title="Print options"
            >
              <FaCog size={16} />
            </button>

            {/* Fullscreen toggle */}
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
            >
              {isFullscreen ? <FaCompress size={16} /> : <FaExpand size={16} />}
            </button>

            {/* Close button */}
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              title="Close"
            >
              <FaTimes size={16} />
            </button>
          </div>
        </div>

        {/* Options panel */}
        {showOptions && (
          <div className="px-6 py-4 bg-slate-50 dark:bg-slate-900/50 border-b border-slate-200 dark:border-slate-700 print:hidden">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {/* Show prices */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={options.showPrices}
                  onChange={(e) => updateOption("showPrices", e.target.checked)}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-slate-700 dark:text-slate-300">
                  Show Prices
                </span>
              </label>

              {/* Show costs */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={options.showCosts}
                  onChange={(e) => updateOption("showCosts", e.target.checked)}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-slate-700 dark:text-slate-300">
                  Show Costs
                </span>
              </label>

              {/* Show notes */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={options.showNotes}
                  onChange={(e) => updateOption("showNotes", e.target.checked)}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-slate-700 dark:text-slate-300">
                  Show Notes
                </span>
              </label>

              {/* Show terms */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={options.showTerms}
                  onChange={(e) => updateOption("showTerms", e.target.checked)}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-slate-700 dark:text-slate-300">
                  Show Terms
                </span>
              </label>

              {/* Copies */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-700 dark:text-slate-300">
                  Copies:
                </span>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={options.copies}
                  onChange={(e) =>
                    updateOption("copies", parseInt(e.target.value) || 1)
                  }
                  className="w-16 px-2 py-1 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800"
                />
              </div>

              {/* Paper size */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-700 dark:text-slate-300">
                  Paper:
                </span>
                <select
                  value={options.paperSize}
                  onChange={(e) =>
                    updateOption("paperSize", e.target.value as "letter" | "a4")
                  }
                  className="px-2 py-1 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800"
                >
                  <option value="letter">Letter</option>
                  <option value="a4">A4</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* Preview content */}
        <div className="flex-1 overflow-auto p-6 bg-slate-100 dark:bg-slate-900 print:p-0 print:bg-white print:overflow-visible">
          <div className="flex justify-center print:block">
            <div
              ref={printRef}
              className="shadow-lg print:shadow-none print:m-0"
            >
              {children}
            </div>
          </div>
        </div>

        {/* Footer with actions */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-200 dark:border-slate-700 print:hidden">
          <div className="text-sm text-slate-500 dark:text-slate-400">
            Paper size:{" "}
            {options.paperSize === "letter" ? '8.5" × 11"' : "210mm × 297mm"}
          </div>

          <div className="flex items-center gap-3">
            {/* Email button */}
            {onEmail && (
              <button
                onClick={onEmail}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors"
              >
                <FaEnvelope size={14} />
                Email
              </button>
            )}

            {/* Download PDF button */}
            {onDownloadPdf && (
              <button
                onClick={onDownloadPdf}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors"
              >
                <FaDownload size={14} />
                Download PDF
              </button>
            )}

            {/* Print button */}
            <button
              onClick={handlePrint}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
            >
              <FaPrint size={14} />
              Print {options.copies > 1 ? `(${options.copies} copies)` : ""}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PrintPreviewModal;
