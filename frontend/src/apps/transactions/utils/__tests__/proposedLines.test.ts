import { describe, expect, it } from 'vitest';
import { isProposed, proposedLineToSend, withProposed } from '../proposedLines';

const proposal = {
  _from: 41, _new: true, line_number: 10,
  item: { item_id: 7, description: 'Widget' },
  quantity: { active: 4, staged: 10, remaining: 10 },
  price: { unit: 10 },
};

describe('a converted document\'s proposed lines (Bill, 2026-11-13)', () => {
  it('shows the proposal as unsaved lines of the record', () => {
    const shown = withProposed({ id: 3, lines: [] }, [proposal]);
    expect(shown.lines).toHaveLength(1);
    expect(shown.lines[0]).toMatchObject({ _from: 41, _new: true, _dirty: true });
    expect(isProposed(shown.lines[0])).toBe(true);
    expect(withProposed({ id: 3, lines: [] }, [])).toEqual({ id: 3, lines: [] });
  });

  it('sends an untouched line as its source line alone', () => {
    expect(proposedLineToSend({ ...proposal, _dirty: true }, proposal)).toEqual({ _from: 41, _dirty: true });
  });

  it('sends a changed quantity as quantity.active alone', () => {
    const edited = { ...proposal, _dirty: true, quantity: { active: 2, staged: 10, remaining: 2 } };
    expect(proposedLineToSend(edited, proposal)).toEqual({ _from: 41, _dirty: true, quantity: { active: 2 } });
  });

  it('sends another field the person changed, and never the form\'s own keys', () => {
    const edited = { ...proposal, id: -1, totals: { extended: 40 }, price: { unit: 9 } };
    expect(proposedLineToSend(edited, proposal)).toEqual({ _from: 41, _dirty: true, price: { unit: 9 } });
  });
});
