import { NextRequest, NextResponse } from "next/server";
import { askChat, ApiError } from "@/lib/api";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  const question = typeof body.question === "string" ? body.question : "";
  try {
    const result = await askChat(question);
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof ApiError) return NextResponse.json({ error: error.message }, { status: error.status });
    throw error;
  }
}
