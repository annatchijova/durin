import { listCases } from "@/lib/api";
import { isViewId } from "@/lib/decision";
import { DashboardView } from "@/components/DashboardView";
import { BackendOfflineNotice } from "@/components/BackendOfflineNotice";

export const dynamic = "force-dynamic";

export default async function DashboardPage({ searchParams }: { searchParams: Promise<{ view?: string | string[] }> }) {
  const { view } = await searchParams;
  try {
    const { cases } = await listCases();
    return <DashboardView cases={cases} initialView={isViewId(view) ? view : "all"} />;
  } catch {
    return <BackendOfflineNotice />;
  }
}
