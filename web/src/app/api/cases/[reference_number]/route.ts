import { NextResponse } from "next/server";
import { getCaseByReference } from "@/lib/data/cases";

interface RouteContext {
  params: Promise<{ reference_number: string }>;
}

export async function GET(_request: Request, context: RouteContext) {
  const { reference_number } = await context.params;
  const payload = await getCaseByReference(decodeURIComponent(reference_number));

  if (!payload.contract) {
    return NextResponse.json({ ok: false, ...payload }, { status: 404 });
  }

  return NextResponse.json({ ok: true, ...payload });
}
