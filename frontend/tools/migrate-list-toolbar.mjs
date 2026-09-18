#!/usr/bin/env node
/**
 * migrate-list-toolbar.mjs
 *
 * Migrates *List.tsx files from PageBreadcrumb to ButtonToolbar.
 * Uses ContactList.tsx as the reference pattern.
 *
 * Usage:
 *   node tools/migrate-list-toolbar.mjs           # dry-run
 *   node tools/migrate-list-toolbar.mjs --apply   # write changes
 */
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

const ROOT = path.resolve(import.meta.dirname, '..');
const DRY_RUN = !process.argv.includes('--apply');

// ─── Skip patterns ──────────────────────────────────────────────────────────
const SKIP = [
  'qqq_',
  'Mob.tsx',
  'node_modules',
  'ContactList.tsx',     // already done (reference)
  'ContactList1.tsx',    // variant
  'OrgEntityList.tsx',   // custom pattern
  'OrgList.tsx',         // custom pattern
  'RecordListColumn.tsx',// utility
  'vendor - Copy',       // copy folder
];

// ─── Discover files ──────────────────────────────────────────────────────────
function findListFiles() {
  const raw = execSync(
    `find "${path.join(ROOT, 'src/apps')}" -name "*List*.tsx" -type f`,
    { encoding: 'utf-8' }
  ).trim().split('\n').filter(Boolean);

  return raw
    .filter(f => !SKIP.some(s => f.includes(s)))
    .filter(f => /List\.tsx$/.test(f))  // only files ending with List.tsx
    .sort();
}

// ─── Derive metadata from file ──────────────────────────────────────────────
function deriveModelInfo(filePath, content) {
  const base = path.basename(filePath, '.tsx');

  // Extract pageTitle from <PageBreadcrumb pageTitle="..." />
  const pageTitleMatch = content.match(/<PageBreadcrumb\s+pageTitle=["']([^"']+)["']/);
  const pageTitle = pageTitleMatch ? pageTitleMatch[1] : base.replace(/List$/, '') + ' List';

  // Derive model label: "Item List" → "Item", "GL Journal List" → "GL Journal"
  const title = pageTitle.replace(/\s*List\s*$/, '');

  // Derive model key: "Item" → "item", "GL Journal" → "gl_journal", "Exchange Rate" → "exchange_rate"
  const modelKey = title
    .replace(/([a-z])([A-Z])/g, '$1_$2')
    .replace(/\s+/g, '_')
    .toLowerCase();

  // Find selection state variable name
  const selMatch = content.match(/\bconst\s+\[(\w+),\s*set\w+\]\s*=\s*useState<[^>]*>\(\s*\[\]\s*\)/g);
  let selectedVar = null;
  let setSelectedVar = null;
  if (selMatch) {
    // Find the state that looks like selectedXxx (for selection, not data)
    for (const m of selMatch) {
      const vMatch = m.match(/\[(\w+),\s*(set\w+)\]/);
      if (vMatch && /^selected/i.test(vMatch[1])) {
        selectedVar = vMatch[1];
        setSelectedVar = vMatch[2];
      }
    }
  }

  // Check for handleBulkDelete
  const hasBulkDelete = /handleBulkDelete/.test(content);

  // Check for existing handleAdd
  const hasHandleAdd = /handleAdd/.test(content);

  // Check for searchDatabase state
  const hasSearchDatabase = /searchDatabase/.test(content);

  // Check for filters
  const hasFilters = /\bfilters\b.*ColumnFilter/.test(content);

  // Check for handleDatabaseSearch
  const hasDatabaseSearch = /handleDatabaseSearch/.test(content);

  // Check for loading state
  const hasLoading = /\[loading,/.test(content);

  // Find data state variable
  const dataMatch = content.match(/\bconst\s+\[(data|rawData),\s*(set\w+)\]\s*=\s*useState/);
  const dataVar = dataMatch ? dataMatch[1] : 'data';

  return {
    pageTitle,
    title,
    modelKey,
    selectedVar,
    setSelectedVar,
    hasBulkDelete,
    hasHandleAdd,
    hasSearchDatabase,
    hasFilters,
    hasDatabaseSearch,
    hasLoading,
    dataVar,
  };
}

// ─── Process one file ────────────────────────────────────────────────────────
function processFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf-8');
  const rel = path.relative(ROOT, filePath);

  // Must contain PageBreadcrumb to migrate
  if (!content.includes('PageBreadcrumb') && !content.includes('PageBreadCrumb')) {
    return { skip: 'no PageBreadcrumb' };
  }

  // Already has ButtonToolbar
  if (content.includes('ButtonToolbar')) {
    return { skip: 'already has ButtonToolbar' };
  }

  const info = deriveModelInfo(filePath, content);

  // ── Step 1: Replace/add imports ──────────────────────────────────────────
  // Remove PageBreadcrumb import
  content = content.replace(
    /^import\s+PageBreadcrumb\s+from\s+["'][^"']+["'];\s*\n/m,
    ''
  );

  // Add ButtonToolbar import + useRef & useCallback if missing
  // Find last import line to insert after
  const lines = content.split('\n');
  let lastImportIdx = 0;
  for (let i = 0; i < lines.length; i++) {
    if (/^\s*import\s/.test(lines[i])) {
      let j = i;
      while (j < lines.length && !lines[j].includes(';') && !/['"];?\s*$/.test(lines[j])) {
        j++;
      }
      lastImportIdx = j;
    }
  }

  // Build imports to add
  const newImports = [];
  newImports.push(`import ButtonToolbar from "@/components/common/ButtonToolbar";`);

  // Add useRef if not present
  if (!content.includes('useRef')) {
    // Patch react import to include useRef
    content = content.replace(
      /(import\s+{[^}]*)(}\s+from\s+["']react["'])/,
      (match, before, after) => {
        if (before.includes('useRef')) return match;
        return `${before.trimEnd()}, useRef${after}`;
      }
    );
  }

  // Add useCallback if not present
  if (!content.includes('useCallback')) {
    content = content.replace(
      /(import\s+{[^}]*)(}\s+from\s+["']react["'])/,
      (match, before, after) => {
        if (before.includes('useCallback')) return match;
        return `${before.trimEnd()}, useCallback${after}`;
      }
    );
  }

  // Check if AdvancedDataTableHandle is imported
  const hasADTHandleImport = content.includes('AdvancedDataTableHandle');

  // Re-split after modifications
  const lines2 = content.split('\n');
  lastImportIdx = 0;
  for (let i = 0; i < lines2.length; i++) {
    if (/^\s*import\s/.test(lines2[i])) {
      let j = i;
      while (j < lines2.length && !lines2[j].includes(';') && !/['"];?\s*$/.test(lines2[j])) {
        j++;
      }
      lastImportIdx = j;
    }
  }

  // Insert ButtonToolbar import
  lines2.splice(lastImportIdx + 1, 0, ...newImports);
  content = lines2.join('\n');

  // If AdvancedDataTableHandle not imported, add it to the existing AdvancedDataTable import
  if (!hasADTHandleImport && content.includes('AdvancedDataTable')) {
    content = content.replace(
      /import\s+AdvancedDataTable\s+from/,
      'import AdvancedDataTable, { type AdvancedDataTableHandle } from'
    );
    // Also handle case where it's already a named import
    if (!content.includes('AdvancedDataTableHandle')) {
      content = content.replace(
        /import\s+AdvancedDataTable,\s*{([^}]*)}\s+from/,
        (match, named) => {
          if (named.includes('AdvancedDataTableHandle')) return match;
          // Trim trailing comma/whitespace to avoid double commas
          const trimmed = named.trimEnd().replace(/,\s*$/, '');
          return `import AdvancedDataTable, {${trimmed}, type AdvancedDataTableHandle } from`;
        }
      );
    }
  }

  // ── Step 2: Add missing state variables ──────────────────────────────────
  // Find the component function body start
  const funcBodyMatch = content.match(/((?:export\s+default\s+)?(?:function\s+\w+|const\s+\w+\s*(?::\s*React\.FC\s*)?=\s*)\([^)]*\)\s*(?::\s*\w+\s*)?(?:=>)?\s*\{)/);
  if (!funcBodyMatch) {
    return { skip: 'could not find component body' };
  }

  // Find the first state declaration to insert our new state after it
  const stateInsertions = [];

  if (!content.includes('searchTerm') || !content.match(/\[searchTerm,\s*setSearchTerm\]/)) {
    stateInsertions.push('  const [searchTerm, setSearchTerm] = useState("");');
  }
  if (!content.includes('filterValues') || !content.match(/\[filterValues,/)) {
    stateInsertions.push('  const [filterValues, setFilterValues] = useState<Record<string, string>>({});');
  }
  if (!content.includes('filtersOpen') || !content.match(/\[filtersOpen,/)) {
    stateInsertions.push('  const [filtersOpen, setFiltersOpen] = useState(false);');
  }
  if (!content.includes('columnVisibility') || !content.match(/\[columnVisibility,/)) {
    stateInsertions.push('  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);');
  }

  // Add refs
  const refInsertions = [];
  if (!content.includes('tableRef')) {
    refInsertions.push('  const tableRef = useRef<AdvancedDataTableHandle<any>>(null);');
  }
  if (!content.includes('columnBtnRef')) {
    refInsertions.push('  const columnBtnRef = useRef<HTMLButtonElement>(null);');
  }
  if (!content.includes('importInputRef')) {
    refInsertions.push('  const importInputRef = useRef<HTMLInputElement>(null);');
  }

  if (stateInsertions.length > 0 || refInsertions.length > 0) {
    // Insert after the last existing useState or useRef line
    const cLines = content.split('\n');
    let insertAfterIdx = -1;
    for (let i = 0; i < cLines.length; i++) {
      if (/useState|useRef/.test(cLines[i]) && /const\s+\[/.test(cLines[i])) {
        insertAfterIdx = i;
      }
    }
    if (insertAfterIdx === -1) {
      // fallback: insert after component declaration
      for (let i = 0; i < cLines.length; i++) {
        if (funcBodyMatch[0] && cLines[i].includes('{') && i > 5) {
          insertAfterIdx = i;
          break;
        }
      }
    }
    if (insertAfterIdx >= 0) {
      const allInsertions = [...stateInsertions, ...refInsertions];
      cLines.splice(insertAfterIdx + 1, 0, ...allInsertions);
      content = cLines.join('\n');
    }
  }

  // ── Step 3: Add filteredData memo if not present ─────────────────────────
  if (!content.includes('filteredData')) {
    const dataVar = info.dataVar;
    const filteredDataBlock = `
  // Filter data based on filterValues from ButtonToolbar
  const filteredData = useMemo(() => {
    if (Object.keys(filterValues).length === 0) return ${dataVar};
    return ${dataVar}.filter((row: any) => {
      return Object.entries(filterValues).every(([key, value]) => {
        if (!value) return true;
        const rowValue = String(row[key] || "").toLowerCase();
        return rowValue.includes(value.toLowerCase());
      });
    });
  }, [${dataVar}, filterValues]);`;

    // Also add visibleColumns if we have columns and columnVisibility
    const visibleColumnsBlock = `

  // Filter columns based on visibility from ButtonToolbar
  const visibleColumns = useMemo(() => {
    if (columnVisibility.length === 0) return columns;
    return columns.filter((_: any, index: number) => columnVisibility[index] !== false);
  }, [columns, columnVisibility]);`;

    // Insert before the return statement
    const returnIdx = content.lastIndexOf('\n  return (');
    if (returnIdx >= 0) {
      content = content.slice(0, returnIdx) + filteredDataBlock + visibleColumnsBlock + content.slice(returnIdx);
    }
  }

  // ── Step 4: Replace <PageBreadcrumb ... /> with <ButtonToolbar ... /> ────
  const toolbarJsx = buildToolbarJsx(info);
  content = content.replace(
    /\s*<PageBreadcrumb\s+pageTitle=["'][^"']+["']\s*\/>\s*\n?/,
    '\n' + toolbarJsx + '\n'
  );

  // ── Step 5: Update AdvancedDataTable to use filteredData and visibleColumns
  // Replace data={data} with data={filteredData}
  content = content.replace(
    /(<AdvancedDataTable(?![A-Za-z])[\s\S]*?)data=\{data\}/,
    '$1data={filteredData}'
  );

  // Replace columns={columns} with columns={visibleColumns}
  content = content.replace(
    /(<AdvancedDataTable(?![A-Za-z])[\s\S]*?)columns=\{columns\}/,
    '$1columns={visibleColumns}'
  );

  // Add ref={tableRef} to AdvancedDataTable if not present
  if (!content.match(/<AdvancedDataTable(?![A-Za-z])[\s\S]*?ref=/)) {
    content = content.replace(
      /<AdvancedDataTable(?![A-Za-z])/,
      '<AdvancedDataTable\n              ref={tableRef}'
    );
  }

  // Add externalSearchTerm and onExternalSearchTermChange if not present
  if (!content.includes('externalSearchTerm')) {
    content = content.replace(
      /(<AdvancedDataTable(?![A-Za-z])[\s\S]*?)(\/>\s*)/,
      (match, before, after) => {
        if (before.includes('externalSearchTerm')) return match;
        return `${before}\n              externalSearchTerm={searchTerm}\n              onExternalSearchTermChange={setSearchTerm}${after}`;
      }
    );
  }

  // Add filtersOpen props if not present
  if (!content.includes('filtersOpen={filtersOpen}')) {
    content = content.replace(
      /(<AdvancedDataTable(?![A-Za-z])[\s\S]*?)(\/>\s*)/,
      (match, before, after) => {
        if (before.includes('filtersOpen={filtersOpen}')) return match;
        return `${before}\n              filtersOpen={filtersOpen}\n              onFiltersOpenChange={setFiltersOpen}${after}`;
      }
    );
  }

  // Add hideHeader={true} if not present
  if (!content.includes('hideHeader')) {
    content = content.replace(
      /(<AdvancedDataTable(?![A-Za-z])[\s\S]*?)(\/>\s*)/,
      (match, before, after) => {
        if (before.includes('hideHeader')) return match;
        return `${before}\n              hideHeader={true}${after}`;
      }
    );
  }

  // ── Step 6: Add useMemo import if not present ────────────────────────────
  if (!content.includes('useMemo')) {
    content = content.replace(
      /(import\s+{[^}]*)(}\s+from\s+["']react["'])/,
      (match, before, after) => {
        if (before.includes('useMemo')) return match;
        return `${before.trimEnd()}, useMemo${after}`;
      }
    );
  }

  if (!DRY_RUN) fs.writeFileSync(filePath, content);
  return { ok: info.modelKey, pageTitle: info.pageTitle };
}

// ─── Build ButtonToolbar JSX ─────────────────────────────────────────────────
function buildToolbarJsx(info) {
  const { pageTitle, title, modelKey, selectedVar, hasBulkDelete, hasSearchDatabase, hasFilters, hasLoading } = info;

  const props = [];
  props.push(`        pageTitle="${pageTitle}"`);
  props.push(`        title="${title}"`);
  props.push(`        modelKey="${modelKey}"`);
  props.push(`        searchTerm={searchTerm}`);
  props.push(`        onSearchTermChange={setSearchTerm}`);
  props.push(`        handleAddInline={handleAdd}`);

  if (hasBulkDelete) {
    props.push(`        handleBulkDelete={handleBulkDelete}`);
  }

  props.push(`        tableRef={tableRef}`);
  props.push(`        columnBtnRef={columnBtnRef}`);
  props.push(`        importInputRef={importInputRef}`);

  if (selectedVar) {
    props.push(`        selectedRows={${selectedVar}}`);
    props.push(`        selectedCount={${selectedVar}.length}`);
  }

  props.push(`        totalCount={data.length}`);
  props.push(`        filteredCount={filteredData.length}`);
  props.push(`        onRefresh={getData}`);

  if (hasLoading) {
    props.push(`        loading={loading}`);
  }

  if (hasSearchDatabase) {
    props.push(`        enableDatabaseSearch`);
    props.push(`        searchDatabase={searchDatabase}`);
    props.push(`        onSearchModeChange={setSearchDatabase}`);
  }

  // Column management
  props.push(`        columns={columns}`);
  props.push(`        columnVisibility={columnVisibility}`);
  props.push(`        onColumnVisibilityChange={setColumnVisibility}`);
  props.push(`        storageKey="${modelKey}-list"`);

  // Filters
  if (hasFilters) {
    props.push(`        filters={filters}`);
  }
  props.push(`        filterValues={filterValues}`);
  props.push(`        onFilterValuesChange={setFilterValues}`);
  props.push(`        filtersOpen={filtersOpen}`);
  props.push(`        onFiltersOpenChange={setFiltersOpen}`);

  return `      <ButtonToolbar\n${props.join('\n')}\n      />`;
}

// ─── Main ───────────────────────────────────────────────────────────────────
console.log(DRY_RUN ? '=== DRY RUN (use --apply to write) ===' : '=== APPLYING CHANGES ===');
console.log();

const files = findListFiles();
console.log(`Found ${files.length} candidate List files\n`);

let modified = 0, skipped = 0;
const errors = [];

for (const f of files) {
  const rel = path.relative(ROOT, f);
  try {
    const result = processFile(f);
    if (result.ok) {
      console.log(`  ✅ ${rel}  →  ${result.ok} ("${result.pageTitle}")`);
      modified++;
    } else {
      console.log(`  ⏭️  ${rel}  — ${result.skip}`);
      skipped++;
    }
  } catch (err) {
    console.log(`  ❌ ${rel}  — ${err.message}`);
    errors.push({ file: rel, error: err.message });
  }
}

console.log(`\n─── Summary ───`);
console.log(`  Modified: ${modified}`);
console.log(`  Skipped:  ${skipped}`);
console.log(`  Errors:   ${errors.length}`);
if (errors.length) {
  console.log('\nErrors:');
  errors.forEach(e => console.log(`  ${e.file}: ${e.error}`));
}
if (DRY_RUN) {
  console.log('\n👆 This was a DRY RUN. Run with --apply to modify files.');
}
