/**
 * HighlightedJson — React component for JSON syntax highlighting.
 * Zero dangerouslySetInnerHTML. Zero XSS surface.
 *
 * Used by RawJsonCard, JsonCard, JsonFieldEditor, RawDataPanel, RefsPanel.
 */
import React from "react";

const TOKEN_RE =
  /("(?:\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(?:\s*:)?|\b(?:true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g;

function classForToken(token: string): string | null {
  if (/^"/.test(token)) {
    return /:$/.test(token)
      ? "text-sky-700 dark:text-sky-400"        // key
      : "text-emerald-700 dark:text-emerald-400"; // string
  }
  if (/^true$|^false$/.test(token)) return "text-amber-700 dark:text-amber-400";
  if (token === "null") return "text-rose-700 dark:text-rose-400";
  if (/^-?\d/.test(token)) return "text-violet-700 dark:text-violet-400"; // number
  return null;
}

interface HighlightedJsonProps {
  json: string;
}

export const HighlightedJson: React.FC<HighlightedJsonProps> = ({ json }) => {
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;

  for (const m of json.matchAll(TOKEN_RE)) {
    const idx = m.index!;
    if (idx > lastIndex) {
      parts.push(json.slice(lastIndex, idx));
    }
    const token = m[0];
    const cls = classForToken(token);
    parts.push(
      cls
        ? React.createElement("span", { key: parts.length, className: cls }, token)
        : token,
    );
    lastIndex = idx + token.length;
  }
  if (lastIndex < json.length) {
    parts.push(json.slice(lastIndex));
  }

  return React.createElement(React.Fragment, null, ...parts);
};
