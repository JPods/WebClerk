import { describe, expect, it } from 'vitest';
import { refusedFrom } from '../wcapi';

// The door answers {status, code, message, error: {code, details}}. The toast shows the
// sentence; an object handed to a toast throws in React (Fable L5 M-1).
const refusal = (status: number, body: unknown) => ({ response: { status, data: body } });

describe('refusedFrom', () => {
  it('reads the door\'s sentence, code and details', () => {
    const r = refusedFrom(refusal(400, {
      status: 'fail', code: 400, message: 'Not fields of cash: bogus: not a field of cash',
      error: { code: 'unknown_field', details: ['bogus: not a field of cash'] }, data: null,
    }));
    expect(r).toEqual({
      status: 400, code: 'unknown_field',
      message: 'Not fields of cash: bogus: not a field of cash',
      details: ['bogus: not a field of cash'],
    });
  });

  it('never returns an object as the message', () => {
    const r = refusedFrom(refusal(409, { error: { code: 'over_apply', details: { available: 100 } } }), 'Failed');
    expect(typeof r.message).toBe('string');
    expect(r.message).toBe('Failed: available: 100');
    expect(r.code).toBe('over_apply');
  });

  it('falls back to the network error when there is no response', () => {
    expect(refusedFrom(new Error('Network Error')).message).toBe('Network Error');
  });
});

describe('refusedFrom names the cause behind a label', () => {
  it('appends string details', () => {
    const r = refusedFrom(refusal(400, { message: 'Invalid field values',
      error: { code: 'invalid_field', details: 'customer_id: no such customer' } }));
    expect(r.message).toBe('Invalid field values: customer_id: no such customer');
  });
  it('appends a field dict', () => {
    const r = refusedFrom(refusal(400, { message: 'Error',
      error: { code: 'validation', details: { amount: ['must be positive'] } } }));
    expect(r.message).toBe('Error: amount: must be positive');
  });
  it('does not repeat what the sentence already says', () => {
    const r = refusedFrom(refusal(400, { message: 'Not fields of cash: bogus: not a field of cash',
      error: { code: 'unknown_field', details: ['bogus: not a field of cash'] } }));
    expect(r.message).toBe('Not fields of cash: bogus: not a field of cash');
  });
});
