/**
 * FormattingContext — the formatting a record's screen uses (utils/formatting.ts): the model's
 * definition overlaid by the party org's. DbForm provides it; the line grid, the totals, the
 * panels and the prints read it. Outside a provider it is the shipped formatting.
 */
import React, { createContext, useContext } from 'react';
import { SHIPPED_FORMATTING, type Formatting } from '@/utils/formatting';

const FormattingContext = createContext<Formatting>(SHIPPED_FORMATTING);

export const FormattingProvider: React.FC<{ value: Formatting; children: React.ReactNode }> = ({ value, children }) => (
  <FormattingContext.Provider value={value}>{children}</FormattingContext.Provider>
);

export function useFormatting(): Formatting {
  return useContext(FormattingContext);
}
