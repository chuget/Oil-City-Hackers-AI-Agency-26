import { NextResponse } from "next/server";
import { getCases } from "@/lib/data/cases";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = Number(searchParams.get("limit") ?? 20);

  try {
    const payload = await getCases(Number.isFinite(limit) ? limit : 20);
    return NextResponse.json({ ok: true, ...payload });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "Unable to load cases",
      },
      { status: 500 },
    );
  }
}
