/** FieldRow's lock on a stamp this login may change (the document date, 2026-11-27). */
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/react';
import FieldRow from '../FieldRow';

const record = { id: 5, dt_created: 1_791_000_000_000 };
const row = (props: any) => render(
  <FieldRow field="dt_created" label="dt_created" data={record} onChange={vi.fn()} {...props} />);
const q = (c: HTMLElement, s: string) => c.querySelector(`[data-wc="${s}"]`);

describe('FieldRow unlockable stamp', () => {
  it('shows the lock button only when unlockable and editing', () => {
    expect(q(row({ isEditing: true, unlockable: true }).container, 'unlock-dt_created')).not.toBeNull();
    expect(q(row({ isEditing: false, unlockable: true }).container, 'unlock-dt_created')).toBeNull();
    expect(q(row({ isEditing: true }).container, 'unlock-dt_created')).toBeNull();
  });

  it('locked is the stamp; unlocked is the date widget, and it locks again', () => {
    const { container } = row({ isEditing: true, unlockable: true });
    expect(container.querySelector('[data-wc-dt="dt_created"]')).toBeNull();
    fireEvent.click(q(container, 'unlock-dt_created')!);
    expect(container.querySelector('[data-wc-dt="dt_created"]')).not.toBeNull();
    fireEvent.click(q(container, 'lock-dt_created')!);
    expect(container.querySelector('[data-wc-dt="dt_created"]')).toBeNull();
  });
});
