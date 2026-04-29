import { Pool, type QueryResultRow } from "pg";

let pool: Pool | null = null;

export function hasDatabaseUrl() {
  return Boolean(process.env.DATABASE_URL);
}

export function getPool() {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL is not configured");
  }

  pool ??= new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: process.env.DATABASE_URL.includes("localhost")
      ? false
      : { rejectUnauthorized: false },
  });

  return pool;
}

export async function query<T extends QueryResultRow>(text: string, values?: unknown[]) {
  const result = await getPool().query<T>(text, values);
  return result.rows;
}
