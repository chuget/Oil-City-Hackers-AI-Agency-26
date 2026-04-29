import { NextResponse } from "next/server";
import { governContract } from "@/lib/governance";
import type { ContractCandidate } from "@/types/governance";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as { contract?: ContractCandidate };

    if (!body.contract) {
      return NextResponse.json(
        { ok: false, error: "Expected request body: { contract: ContractCandidate }" },
        { status: 400 },
      );
    }

    const finding = await governContract(body.contract);
    return NextResponse.json({ ok: true, finding });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "Unable to govern contract",
      },
      { status: 500 },
    );
  }
}
