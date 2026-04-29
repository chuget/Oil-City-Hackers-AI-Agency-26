import { NextResponse } from "next/server";
import { hasDatabaseUrl, query } from "@/lib/db";

export async function GET() {
  if (!hasDatabaseUrl()) {
    return NextResponse.json({
      ok: true,
      db: "not_configured",
      dataset: process.env.CASE_DATASET ?? "mock",
    });
  }

  try {
    await query("SELECT 1");
    return NextResponse.json({
      ok: true,
      db: "connected",
      dataset: process.env.CASE_DATASET ?? "mock",
    });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        db: "error",
        error: error instanceof Error ? error.message : "Unknown database error",
      },
      { status: 500 },
    );
  }
}
