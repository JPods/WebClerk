import React from 'react';

const linkClass = "text-blue-600 hover:underline";

const DocsIndex: React.FC = () => {
  return (
    <div className="p-6 space-y-2">
      <h1 className="text-xl font-semibold">Docs</h1>
      <ul className="list-disc pl-6">
        <li>
          <a className={linkClass} href="/readmes/index.md" target="_blank" rel="noreferrer">
            Frontend Docs Index (Markdown)
          </a>
        </li>
        <li>
          <a className={linkClass} href="/readmes/admin-workbench.md" target="_blank" rel="noreferrer">
            Admin Workbench
          </a>
        </li>
        <li>
          <a className={linkClass} href="/readmes/admin-window.md" target="_blank" rel="noreferrer">
            Admin Window
          </a>
        </li>
        <li>
          <a className={linkClass} href="/readmes/api-integration.md" target="_blank" rel="noreferrer">
            API Integration
          </a>
        </li>
        <li>
          <a className={linkClass} href="/readmes/env.md" target="_blank" rel="noreferrer">
            Environment Setup
          </a>
        </li>
        <li>
          <a className={linkClass} href="/readmes/whitelist.md" target="_blank" rel="noreferrer">
            Whitelist Tester
          </a>
        </li>
      </ul>
      <p className="text-sm text-gray-500">Tip: If your dev server doesn’t serve .md files, open them in the repo under <code>readmes/</code>.</p>
    </div>
  );
};

export default DocsIndex;
