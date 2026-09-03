/**
 * Toolbar action definitions — maps each action to all available button styles.
 *
 * Each style set lives in src/components/ui/button/{style_name}/
 * with a README.md describing the set. The system auto-discovers
 * available PNG sets by folder name.
 *
 * To add a new PNG button set:
 *   1. Create folder: src/components/ui/button/{name}/
 *   2. Add PNGs matching the file names in the 'png' field below
 *   3. Add README.md describing the set
 *   4. Add the folder name to AVAILABLE_PNG_STYLES
 *   5. Add the png filename mapping to TB entries if filenames differ
 */
import {
  FilePlus, Save, RotateCcw, Trash,
  Trash2, Filter, List, Ban,
  ArrowUpNarrowWide, Printer, X,
  type LucideIcon,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Available PNG button style folders
// ---------------------------------------------------------------------------
export const AVAILABLE_PNG_STYLES = ['button_glass', 'OSX'] as const;

// ---------------------------------------------------------------------------
// Action definition
// ---------------------------------------------------------------------------
export interface ToolbarAction {
  /** PNG filenames per style folder (without .png extension) */
  png: Record<string, string>;
  /** Lucide icon component */
  icon: LucideIcon;
  /** Text label for minimal style */
  minimal: string;
  /** Optional emoji for minimal style */
  emoji?: string;
}

// ---------------------------------------------------------------------------
// All toolbar actions
// ---------------------------------------------------------------------------
export const TB: Record<string, ToolbarAction> = {
  addRecord: {
    png: { button_glass: 'AddRecord', OSX: 'NewRecord' },
    icon: FilePlus,
    minimal: 'Add',
    emoji: '+',
  },
  save: {
    png: { button_glass: 'OK', OSX: 'Done' },
    icon: Save,
    minimal: 'Save',
    emoji: '💾',
  },
  discard: {
    png: { button_glass: 'Cancel', OSX: 'Cancel' },
    icon: RotateCcw,
    minimal: 'Discard',
    emoji: '↩',
  },
  cancel: {
    png: { button_glass: 'Cancel', OSX: 'Cancel' },
    icon: X,
    minimal: 'Cancel',
    emoji: '✕',
  },
  deleteRecord: {
    png: { button_glass: 'Delete Record', OSX: 'DeleteRecord' },
    icon: Trash,
    minimal: 'Delete',
    emoji: '🗑',
  },
  deleteSelection: {
    png: { button_glass: 'Delete Selection', OSX: 'DeleteSelection' },
    icon: Trash2,
    minimal: 'Del Sel',
    emoji: '🗑',
  },
  filter: {
    png: { button_glass: 'Query', OSX: 'Query' },
    icon: Filter,
    minimal: 'Filter',
    emoji: '🔍',
  },
  showAll: {
    png: { button_glass: 'ShowAll', OSX: 'ShowAll' },
    icon: List,
    minimal: 'All',
    emoji: '📋',
  },
  showSubset: {
    png: { button_glass: 'ShowSubset', OSX: 'ShowSubset' },
    icon: Filter,
    minimal: 'Subset',
    emoji: '📎',
  },
  omit: {
    png: { button_glass: 'OmitSelection', OSX: 'DeleteSelection' },
    icon: Ban,
    minimal: 'Omit',
    emoji: '🚫',
  },
  sort: {
    png: { button_glass: 'OrderBy', OSX: 'OrderBy' },
    icon: ArrowUpNarrowWide,
    minimal: 'Sort',
    emoji: '↕',
  },
  print: {
    png: { button_glass: 'Report', OSX: 'Report' },
    icon: Printer,
    minimal: 'Report',
    emoji: '🖨',
  },
  modelMenu: {
    png: { button_glass: 'Globe', OSX: 'Globe' },
    icon: List,
    minimal: 'Menu',
    emoji: '☰',
  },
};

// All available style names (for the picker)
export const BUTTON_STYLES = ['button_glass', 'OSX', 'lucide', 'minimal'] as const;
export type ButtonStyleName = typeof BUTTON_STYLES[number];
