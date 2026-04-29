import { hasDatabaseUrl, query } from "@/lib/db";

export interface TableSummary {
  table_schema: string;
  table_name: string;
}

export async function listAvailableTables(): Promise<TableSummary[]> {
  if (!hasDatabaseUrl()) return [];

  return query<TableSummary>(`
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema IN ('ab', 'fed', 'general', 'public')
      AND table_type = 'BASE TABLE'
    ORDER BY table_schema, table_name
  `);
}
