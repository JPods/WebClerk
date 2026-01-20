// TypeScript interface for Linkage model
export interface Linkage {
  id: number;
  purpose?: string;
  name?: string;
  note?: string;
  refs?: {
    links?: Record<string, number[]>;
  };
  // Add other fields as needed for strict alignment
}
