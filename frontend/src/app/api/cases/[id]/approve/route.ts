import { NextRequest, NextResponse } from "next/server";
import { approveProposal, ApiError } from "@/lib/api";

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = await request.json().catch(() => ({}));
  const approverId = typeof body.approverId === "string" ? body.approverId : "";
  try {
    const result = await approveProposal(id, approverId);
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof ApiError) return NextResponse.json({ error: error.message }, { status: error.status });
    throw error;
  }
}
