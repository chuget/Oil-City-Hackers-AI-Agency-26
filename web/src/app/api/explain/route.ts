import { NextResponse } from "next/server";
import { explainFinding } from "@/lib/aws/bedrock";
import type { GovernedFinding } from "@/types/governance";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as { finding?: GovernedFinding };

    if (!body.finding) {
      return NextResponse.json(
        { ok: false, error: "Expected request body: { finding: GovernedFinding }" },
        { status: 400 },
      );
    }

    const summary = await explainFinding(body.finding);
    return NextResponse.json({ ok: true, summary });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "Unable to explain finding",
      },
      { status: 500 },
    );
  }
}
