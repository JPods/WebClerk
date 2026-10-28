import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import CollapsiblePanel from '@/apps/common/components/CollapsiblePanel';

vi.mock('@/api/wcapi', () => ({
  getRecord: vi.fn(() => Promise.reject(Object.assign(new Error('Request failed'), { response: { data: { message: 'refused' } } }))),
  getRecords: vi.fn(),
}));

import SpecPanel from '../SpecPanel';

describe('SpecPanel in a frame', () => {
  it('shows a refused read as the frame error', async () => {
    render(<CollapsiblePanel label="Spec" collapsible={false}><SpecPanel itemId={625} /></CollapsiblePanel>);
    expect(await screen.findByText('refused')).toBeTruthy();
  });
});
