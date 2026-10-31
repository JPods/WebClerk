import { describe, expect, it } from 'vitest';
import { windowChannel } from '@/utils/windowChannel';

// Bill, 2026-10-30: + add opens a card or a floating window on the same page; its save must
// reach the panel there as well as in other WC3 windows.
describe('windowChannel', () => {
  it('delivers a message to listeners on its own page', () => {
    const heard: unknown[] = [];
    const off = windowChannel.on('record-saved', (msg) => heard.push(msg.model));
    windowChannel.send({ type: 'record-saved', model: 'phone', id: 7 });
    off();
    windowChannel.send({ type: 'record-saved', model: 'phone', id: 8 });
    expect(heard).toEqual(['phone']);
  });
});
