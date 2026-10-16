import { describe, it, expect } from 'vitest';
import { applyDerived } from './derivedFields';

const type = (prev: any, field: string, value: string) =>
  applyDerived('contact', prev, { ...prev, [field]: value }, field);

describe('applyDerived — contact attention', () => {
  it('fills an empty attention from the first name, then follows the last name', () => {
    const a = type({ name_first: '', name_last: '', attention: '' }, 'name_first', 'Susy');
    expect(a.attention).toBe('Susy');
    const b = type(a, 'name_last', 'Que');
    expect(b.attention).toBe('Susy Que');
  });

  it('never overwrites an attention the user typed', () => {
    const r = type({ name_first: 'Susy', name_last: '', attention: 'Ms. Que' }, 'name_last', 'Que');
    expect(r.attention).toBe('Ms. Que');
  });

  it('leaves other fields and other models alone', () => {
    const r = type({ name_first: 'Susy', name_last: 'Que', attention: '' }, 'title', 'Owner');
    expect(r.attention).toBe('');
    const o = applyDerived('order', { attention: '' }, { attention: '', name_first: 'x' }, 'name_first');
    expect(o.attention).toBe('');
  });
});
