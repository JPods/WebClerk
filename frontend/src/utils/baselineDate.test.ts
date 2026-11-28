/** dt_created on every form and list; never twice, never reordered (Bill, 2026-11-27). */
import { describe, expect, it } from 'vitest';
import { sectionsWithBaselineDate, listWithBaselineDate, formNamesBaselineDate } from './baselineDate';

const header = (cols: any[]) => ({ type: 'header', layout: 'three-column', columns: cols });
const dt = { field: 'dt_created', label: 'dt_created' };

describe('form', () => {
  it("adds dt_created at the end of the header's last column when the layout does not name it", () => {
    const layout = { sections: [header([{ fields: [{ field: 'ida' }] }, { fields: [{ field: 'status' }] }]), { type: 'tabs' }] };
    const out = sectionsWithBaselineDate(layout);
    expect(out[0].columns[0].fields).toEqual([{ field: 'ida' }]);
    expect(out[0].columns[1].fields).toEqual([{ field: 'status' }, dt]);
    expect(out[1]).toEqual({ type: 'tabs' });
    expect((layout.sections[0] as any).columns[1].fields).toEqual([{ field: 'status' }]);   // the layout itself untouched
  });

  it('leaves a form that names it, in its sections or a card its header draws, as it is', () => {
    const named = { sections: [header([{ fields: [{ field: 'dt_created' }, { field: 'ida' }] }])] };
    expect(sectionsWithBaselineDate(named)).toBe(named.sections);
    const carded = { sections: [{ type: 'header', header: { cards: ['dates'] } }], card: { dates: { fields: [{ field: 'dt_created' }] } } };
    expect(formNamesBaselineDate(carded)).toBe(true);
    expect(sectionsWithBaselineDate(carded)).toBe(carded.sections);
  });

  it('a form with no three-column header gets one holding dt_created first', () => {
    const out = sectionsWithBaselineDate({ sections: [{ type: 'tabs' }] });
    expect(out).toEqual([header([{ fields: [dt] }]), { type: 'tabs' }]);
  });

  it('adds dt_journaled beside it when the record carries one and the layout does not name it', () => {
    const journaled = { field: 'dt_journaled', label: 'dt_journaled' };
    const out = sectionsWithBaselineDate({ sections: [header([{ fields: [{ field: 'ida' }] }])] }, true);
    expect(out[0].columns[0].fields).toEqual([{ field: 'ida' }, dt, journaled]);
    const named = { sections: [header([{ fields: [dt, { field: 'dt_journaled' }] }])] };
    expect(sectionsWithBaselineDate(named, true)).toBe(named.sections);
    const half = sectionsWithBaselineDate({ sections: [header([{ fields: [dt] }])] }, true);
    expect(half[0].columns[0].fields).toEqual([dt, journaled]);
  });
});

describe('list', () => {
  const fields = ['id', 'ida', 'status', 'dt_created'];
  it('puts dt_created after the stored columns when they do not name it', () => {
    expect(listWithBaselineDate(['status', 'ida'], fields)).toEqual(['status', 'ida', 'dt_created']);
  });
  it('never shows it twice or moves it', () => {
    expect(listWithBaselineDate(['dt_created', 'ida'], fields)).toEqual(['dt_created', 'ida']);
    const specs = [{ field: 'ida' }, { field: 'dt_created', visible: false }, { field: 'status' }];
    expect(listWithBaselineDate(specs, fields)).toBe(specs);
  });
  it('adds nothing for a model without dt_created', () => {
    expect(listWithBaselineDate(['ida'], ['id', 'ida'])).toEqual(['ida']);
  });
});
