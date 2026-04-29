import { NextResponse } from "next/server";
import { putJsonSnapshot } from "@/lib/aws/s3";
import { getCases } from "@/lib/data/cases";

export async function POST(request: Request) {
  try {
    const body = (await request.json().catch(() => ({}))) as { limit?: number };
    const limit = Number.isFinite(body.limit) ? Number(body.limit) : 50;
    const snapshot = await getCases(limit);
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const key = `case-snapshots/${snapshot.dataset}/${timestamp}.json`;
    const destination = await putJsonSnapshot(key, {
      exported_at: new Date().toISOString(),
      ...snapshot,
    });

    return NextResponse.json({ ok: true, destination });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "Unable to export cases",
      },
      { status: 500 },
    );
  }
}
