import { notFound } from "next/navigation";
import { getCase, ApiError } from "@/lib/api";
import { CaseJourneyView } from "@/components/CaseJourneyView";

export const dynamic = "force-dynamic";

export default async function CasePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const caseData = await getCase(id);
    return <CaseJourneyView caseData={caseData} />;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  }
}
