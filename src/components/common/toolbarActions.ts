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
  FilePlus, FloppyDisk, ArrowCounterClockwise, Trash,
  TrashSimple, Funnel, ListBullets, Prohibit,
  SortAscending, Printer,
} from '@phosphor-icons/react';
import type { Icon as PhosphorIcon } from '@phosphor-icons/react';

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
  /** Phosphor duotone icon component */
  phosphor: PhosphorIcon;
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
    phosphor: FilePlus,
    minimal: 'Add',
    emoji: '+',
  },
  save: {
    png: { button_glass: 'OK', OSX: 'Done' },
    phosphor: FloppyDisk,
    minimal: 'Save',
    emoji: '💾',
  },
  discard: {
    png: { button_glass: 'Cancel', OSX: 'Cancel' },
    phosphor: ArrowCounterClockwise,
    minimal: 'Discard',
    emoji: '↩',
  },
  deleteRecord: {
    png: { button_glass: 'Delete Record', OSX: 'DeleteRecord' },
    phosphor: Trash,
    minimal: 'Delete',
    emoji: '🗑',
  },
  deleteSelection: {
    png: { button_glass: 'Delete Selection', OSX: 'DeleteSelection' },
    phosphor: TrashSimple,
    minimal: 'Del Sel',
    emoji: '🗑',
  },
  filter: {
    png: { button_glass: 'Query', OSX: 'Query' },
    phosphor: Funnel,
    minimal: 'Filter',
    emoji: '🔍',
  },
  showAll: {
    png: { button_glass: 'ShowAll', OSX: 'ShowAll' },
    phosphor: ListBullets,
    minimal: 'All',
    emoji: '📋',
  },
  showSubset: {
    png: { button_glass: 'ShowSubset', OSX: 'ShowSubset' },
    phosphor: Funnel,
    minimal: 'Subset',
    emoji: '📎',
  },
  omit: {
    png: { button_glass: 'OmitSelection', OSX: 'DeleteSelection' },
    phosphor: Prohibit,
    minimal: 'Omit',
    emoji: '🚫',
  },
  sort: {
    png: { button_glass: 'OrderBy', OSX: 'OrderBy' },
    phosphor: SortAscending,
    minimal: 'Sort',
    emoji: '↕',
  },
  print: {
    png: { button_glass: 'Print', OSX: 'Print' },
    phosphor: Printer,
    minimal: 'Print',
    emoji: '🖨',
  },
};

// All available style names (for the picker)
export const BUTTON_STYLES = ['button_glass', 'OSX', 'phosphor', 'minimal'] as const;
export type ButtonStyleName = typeof BUTTON_STYLES[number];
