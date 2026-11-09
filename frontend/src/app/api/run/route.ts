import { NextRequest, NextResponse } from "next/server";
import { runPipeline, ApiError } from "@/lib/api";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  try {
    const result = await runPipeline(body.sourceDir);
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof ApiError) return NextResponse.json({ error: error.message }, { status: error.status });
    throw error;
  }
}
