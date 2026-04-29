import { NextResponse } from "next/server";
import { hasDatabaseUrl } from "@/lib/db";
import { listAvailableTables } from "@/lib/data/schemaProbe";

export async function GET() {
  if (!hasDatabaseUrl()) {
    return NextResponse.json({
      ok: true,
      source: "fixture",
      tables: [],
      message: "DATABASE_URL is not configured.",
    });
  }

  try {
    const tables = await listAvailableTables();
    return NextResponse.json({ ok: true, source: "database", tables });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "Unknown database error",
      },
      { status: 500 },
    );
  }
}
