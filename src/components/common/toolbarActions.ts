/**
 * Toolbar action definitions — maps each action to glass, phosphor, and minimal styles.
 * Import these in any toolbar that uses ToolbarIcon.
 */
import {
  FilePlus, FloppyDisk, ArrowCounterClockwise, Trash,
  TrashSimple, Funnel, ListBullets, Prohibit,
  SortAscending, Printer,
} from '@phosphor-icons/react';
import type { ToolbarAction } from './ToolbarIcon';

export const TB: Record<string, ToolbarAction> = {
  addRecord:       { glass: 'AddRecord',        phosphor: FilePlus,              minimal: 'Add',     emoji: '+' },
  save:            { glass: 'OK',               phosphor: FloppyDisk,            minimal: 'Save',    emoji: '💾' },
  discard:         { glass: 'Cancel',           phosphor: ArrowCounterClockwise, minimal: 'Discard', emoji: '↩' },
  deleteRecord:    { glass: 'Delete Record',    phosphor: Trash,                 minimal: 'Delete',  emoji: '🗑' },
  deleteSelection: { glass: 'Delete Selection', phosphor: TrashSimple,           minimal: 'Del Sel', emoji: '🗑' },
  filter:          { glass: 'Query',            phosphor: Funnel,                minimal: 'Filter',  emoji: '🔍' },
  showAll:         { glass: 'ShowAll',          phosphor: ListBullets,           minimal: 'All',     emoji: '📋' },
  showSubset:      { glass: 'ShowSubset',       phosphor: Funnel,                minimal: 'Subset',  emoji: '📎' },
  omit:            { glass: 'OmitSelection',    phosphor: Prohibit,              minimal: 'Omit',    emoji: '🚫' },
  sort:            { glass: 'OrderBy',          phosphor: SortAscending,         minimal: 'Sort',    emoji: '↕' },
  print:           { glass: 'Print',            phosphor: Printer,               minimal: 'Print',   emoji: '🖨' },
};
