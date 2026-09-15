/**
 * HighlightedJson — React component for JSON syntax highlighting.
 * Zero dangerouslySetInnerHTML. Zero XSS surface.
 *
 * Uses --db-* CSS variables for theme-aware coloring.
 * Used by RawJsonCard, JsonCard, JsonFieldEditor, RawDataPanel, RefsPanel.
 */
import React from "react";

const TOKEN_RE =
  /("(?:\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(?:\s*:)?|\b(?:true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g;

function styleForToken(token: string): React.CSSProperties | null {
  if (/^"/.test(token)) {
    return /:$/.test(token)
      ? { color: 'var(--db-accent, #2563EB)' }           // key
      : { color: 'var(--db-accent-green, #198754)' };     // string
  }
  if (/^true$|^false$/.test(token)) return { color: 'var(--db-accent-gold, #D97706)' };
  if (token === "null") return { color: 'var(--db-accent-red, #dc3545)' };
  if (/^-?\d/.test(token)) return { color: 'var(--db-accent-purple, #6f42c1)' }; // number
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
    const style = styleForToken(token);
    parts.push(
      style
        ? React.createElement("span", { key: parts.length, style }, token)
        : token,
    );
    lastIndex = idx + token.length;
  }
  if (lastIndex < json.length) {
    parts.push(json.slice(lastIndex));
  }

  return React.createElement(React.Fragment, null, ...parts);
};
