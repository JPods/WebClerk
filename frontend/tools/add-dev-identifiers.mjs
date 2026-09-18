#!/usr/bin/env node
/**
 * add-dev-identifiers.mjs
 *
 * Adds DevIdentifier hover-badges to all Detail, Panel, and Card components.
 *
 * Usage:
 *   node add-dev-identifiers.mjs           # dry-run (shows what would change)
 *   node add-dev-identifiers.mjs --apply   # actually modify files
 */
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

const ROOT = path.resolve(import.meta.dirname, '..');
const SRC = path.join(ROOT, 'src');

const DRY_RUN = !process.argv.includes('--apply');

// ─── File discovery ─────────────────────────────────────────────────────────
/** Filename patterns to match (case-insensitive) */
const MATCH_PATTERNS = [
  /Detail\.tsx$/i,
  /Panel\.tsx$/i,
  /Card\.tsx$/i,
  /Base\.tsx$/i,
  /Modal\.tsx$/i,
];

/** Directories to search */
const SEARCH_DIRS = [
  'src/apps',
  'src/components',
];

/** Files/patterns to skip */
const SKIP = [
  'qqq_',           // legacy drafts
  '.test.',          // tests
  '.spec.',          // tests
  'DevIdentifier',   // don't modify ourselves
  'DevBadge',        // don't modify the other badge
  'DetailFeatureBadge', // don't modify the feature badge
  'node_modules',
  'types.ts',        // type-only files
  'usePermissions',  // hooks
  'documentUpload',  // utility
  '/index.ts',       // barrels
  '/index.tsx',      // barrels
  'print/',          // print templates
  'TransactionToolbar', // toolbar
  'SimpleDetail',    // shared helper, not a detail page
];

function findFiles() {
  const files = new Set();
  for (const dir of SEARCH_DIRS) {
    const absDir = path.join(ROOT, dir);
    try {
      const found = execSync(
        `find "${absDir}" -name '*.tsx' -type f`,
        { encoding: 'utf-8' }
      ).trim().split('\n').filter(Boolean);
      
      for (const f of found) {
        const base = path.basename(f);
        if (MATCH_PATTERNS.some(p => p.test(base))) {
          files.add(f);
        }
      }
    } catch {
      // dir may not exist
    }
  }
  
  // Also include specific utility files
  const utilDir = path.join(ROOT, 'src/apps/utils');
  try {
    const utilFiles = execSync(
      `find "${utilDir}" -name '*.tsx' -type f`,
      { encoding: 'utf-8' }
    ).trim().split('\n').filter(Boolean);
    utilFiles.forEach(f => files.add(f));
  } catch {
    // dir may not exist
  }
  
  return [...files].filter(f => !SKIP.some(s => f.includes(s))).sort();
}

// ─── Variant detection ──────────────────────────────────────────────────────
function getVariant(fileName) {
  if (/Detail/i.test(fileName))  return 'indigo';
  if (/Panel/i.test(fileName))   return 'teal';
  if (/Card/i.test(fileName))    return 'amber';
  if (/Modal/i.test(fileName))   return 'rose';
  return 'indigo';
}

const VARIANT_ARG = {
  indigo: '',            // default, omit
  teal:   ", 'teal'",
  amber:  ", 'amber'",
  rose:   ", 'rose'",
};

// ─── Processing ─────────────────────────────────────────────────────────────
function processFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf-8');
  const baseName = path.basename(filePath, '.tsx');
  const variant = getVariant(baseName);
  const variantArg = VARIANT_ARG[variant];

  // Skip re-exports / tiny files
  const lines = content.split('\n');
  if (lines.length <= 5) return { skip: 're-export / tiny' };
  if (content.includes('export { default }')) return { skip: 're-export' };

  // Already processed
  if (content.includes('withDevIdentifier') || content.includes('<DevIdentifier')) {
    return { skip: 'already has DevIdentifier' };
  }

  // ── Pattern B: const Name = ...; export default Name; ──────────────────
  const patternB = content.match(/^export\s+default\s+(\w+)\s*;?\s*$/m);
  if (patternB) {
    const compName = patternB[1];
    // Make sure it's actually a component (starts with uppercase)
    if (compName[0] !== compName[0].toUpperCase()) return { skip: 'default export is not a component' };

    // Add import after last existing import
    content = addImport(content);

    // Replace export line
    content = content.replace(
      new RegExp(`^(export\\s+default\\s+)${compName}(\\s*;?)\\s*$`, 'm'),
      `export default withDevIdentifier(${compName}, '${compName}'${variantArg});`
    );

    if (!DRY_RUN) fs.writeFileSync(filePath, content);
    return { ok: compName, pattern: 'B', variant };
  }

  // ── Pattern A: export default function Name(...) ───────────────────────
  const patternA = content.match(/^(\s*)export\s+default\s+function\s+(\w+)\s*\(/m);
  if (patternA) {
    const [, indent, compName] = patternA;

    // Add import after last existing import
    content = addImport(content);

    // Remove 'export default' from function declaration
    content = content.replace(
      /^(\s*)export\s+default\s+function\s+(\w+)/m,
      `${indent}function ${compName}`
    );

    // Append new export at end of file
    content = content.trimEnd() + `\n\nexport default withDevIdentifier(${compName}, '${compName}'${variantArg});\n`;

    if (!DRY_RUN) fs.writeFileSync(filePath, content);
    return { ok: compName, pattern: 'A', variant };
  }

  return { skip: 'unrecognized export pattern' };
}

function addImport(content) {
  const importLine = `import { withDevIdentifier } from '@/components/common/DevIdentifier';`;

  // Already has it
  if (content.includes('withDevIdentifier')) return content;

  // Find the last import statement and insert after it
  const lines = content.split('\n');
  let lastImportIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (/^\s*import\s/.test(lines[i])) {
      // Track the end of multi-line imports
      let j = i;
      while (j < lines.length && !lines[j].includes(';') && !lines[j].match(/['"];\s*$/)) {
        j++;
      }
      lastImportIdx = j;
    }
  }

  if (lastImportIdx >= 0) {
    lines.splice(lastImportIdx + 1, 0, importLine);
  } else {
    // No imports found, add at top
    lines.unshift(importLine);
  }

  return lines.join('\n');
}

// ─── Main ───────────────────────────────────────────────────────────────────
console.log(DRY_RUN ? '=== DRY RUN (use --apply to write) ===' : '=== APPLYING CHANGES ===');
console.log();

const files = findFiles();
console.log(`Found ${files.length} candidate files\n`);

let modified = 0;
let skipped = 0;
const errors = [];

for (const f of files) {
  const rel = path.relative(ROOT, f);
  try {
    const result = processFile(f);
    if (result.ok) {
      console.log(`  ✅ ${rel}  →  ${result.ok} (${result.pattern}, ${result.variant})`);
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
