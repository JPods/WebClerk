#!/usr/bin/env node
/**
 * fix-onrefresh.mjs
 *
 * Fixes the onRefresh={getData} references in migrated List files.
 * The migration script hardcoded `getData` but each file uses its own
 * fetch function name (e.g., getCustomerData, fetchActions, etc.).
 *
 * Also fixes handleAdd references where the actual function has a different name.
 *
 * Usage:
 *   node tools/fix-onrefresh.mjs           # dry-run
 *   node tools/fix-onrefresh.mjs --apply   # write changes
 */
import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';

const ROOT = path.resolve(import.meta.dirname, '..');
const DRY_RUN = !process.argv.includes('--apply');

console.log(DRY_RUN ? '=== DRY RUN ===' : '=== APPLYING ===');
console.log();

// Find all List files that have onRefresh={getData}
const files = execSync(
  `grep -rl 'onRefresh={getData}' "${path.join(ROOT, 'src/apps')}" --include='*List.tsx'`,
  { encoding: 'utf-8' }
).trim().split('\n').filter(Boolean);

console.log(`Found ${files.length} files with onRefresh={getData}\n`);

let fixed = 0, already = 0;
const errors = [];

for (const filePath of files) {
  const rel = path.relative(ROOT, filePath);
  let content = fs.readFileSync(filePath, 'utf-8');

  // Check if getData is actually defined in the file (outside of onRefresh)
  const contentWithoutOnRefresh = content.replace(/onRefresh=\{getData\}/g, '');
  if (/\bgetData\b/.test(contentWithoutOnRefresh)) {
    console.log(`  ✓ ${rel} — getData exists, OK`);
    already++;
    continue;
  }

  // Find the actual data-fetching function
  // Pattern: const xxxData = useCallback(async () => { ... setLoading(true) ... fetch...
  // Common patterns:
  //   const getCustomerData = useCallback(async () => {
  //   const fetchActions = useCallback(async () => {
  //   const getWorkorderData = useCallback(async () => {
  //   const fetchData = useCallback(async () => {

  // Strategy: find all useCallback functions that call setLoading or fetch*
  const fetchFnMatch = content.match(
    /const\s+(get\w+Data|fetch\w+|load\w+)\s*=\s*useCallback\s*\(\s*async/
  );

  // Also try non-useCallback patterns
  const fetchFnMatch2 = content.match(
    /const\s+(get\w+Data|fetch\w+|load\w+)\s*=\s*async\s*\(/
  );

  // Also try: function-style with setLoading
  const fetchFnMatch3 = content.match(
    /const\s+(get\w+|fetch\w+|load\w+)\s*=\s*(?:useCallback\s*\(\s*)?async\s*\(\)\s*=>\s*\{[\s\S]*?setLoading\s*\(\s*true\s*\)/
  );

  let actualFn = null;

  if (fetchFnMatch) {
    actualFn = fetchFnMatch[1];
  } else if (fetchFnMatch3) {
    actualFn = fetchFnMatch3[1];
  } else if (fetchFnMatch2) {
    actualFn = fetchFnMatch2[1];
  }

  // Fallback: look for useEffect that calls a specific function
  if (!actualFn) {
    const effectMatch = content.match(
      /useEffect\s*\(\s*\(\)\s*=>\s*\{\s*\n?\s*(get\w+|fetch\w+|load\w+)\s*\(\)/
    );
    if (effectMatch) {
      actualFn = effectMatch[1];
    }
  }

  if (!actualFn) {
    console.log(`  ❌ ${rel} — could not find fetch function`);
    errors.push(rel);
    continue;
  }

  // Replace onRefresh={getData} with onRefresh={actualFn}
  content = content.replace('onRefresh={getData}', `onRefresh={${actualFn}}`);

  // ── Also fix handleAdd if it doesn't exist ──
  if (content.includes('handleAddInline={handleAdd}')) {
    const contentWithoutToolbar = content.replace(/handleAddInline=\{handleAdd\}/g, '');
    if (!/\bhandleAdd\b/.test(contentWithoutToolbar)) {
      // handleAdd doesn't exist — look for alternatives
      // Check for handleAddNew, openAdd, etc.
      const addMatch = content.match(/const\s+(handleAdd\w+|openAdd\w*|addNew\w*)\s*=/);
      if (addMatch) {
        content = content.replace('handleAddInline={handleAdd}', `handleAddInline={${addMatch[1]}}`);
        console.log(`  🔧 ${rel} — getData→${actualFn}, handleAdd→${addMatch[1]}`);
      } else {
        // Check for inline navigation to add route
        const navAddMatch = content.match(/navigate\s*\(\s*['"`][^'"`]*\/add/);
        if (navAddMatch) {
          // handleAdd doesn't exist and navigates — remove handleAddInline prop
          content = content.replace(/\s*handleAddInline=\{handleAdd\}\n?/, '\n');
          console.log(`  🔧 ${rel} — getData→${actualFn}, removed handleAddInline (nav-based add)`);
        } else {
          // Just remove handleAddInline since there's no add function
          content = content.replace(/\s*handleAddInline=\{handleAdd\}\n?/, '\n');
          console.log(`  🔧 ${rel} — getData→${actualFn}, removed handleAddInline (no add fn)`);
        }
      }
    } else {
      console.log(`  ✅ ${rel} — getData→${actualFn}`);
    }
  } else {
    console.log(`  ✅ ${rel} — getData→${actualFn}`);
  }

  if (!DRY_RUN) {
    fs.writeFileSync(filePath, content);
  }
  fixed++;
}

console.log(`\n─── Summary ───`);
console.log(`  Fixed:    ${fixed}`);
console.log(`  Already OK: ${already}`);
console.log(`  Errors:   ${errors.length}`);
if (errors.length) {
  console.log('  Problem files:');
  errors.forEach(e => console.log(`    ${e}`));
}
if (DRY_RUN) console.log('\n👆 DRY RUN. Use --apply to write.');
