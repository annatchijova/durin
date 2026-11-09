import { listCases } from "@/lib/api";
import { DashboardView } from "@/components/DashboardView";
import { BackendOfflineNotice } from "@/components/BackendOfflineNotice";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  try {
    const { cases } = await listCases();
    return <DashboardView cases={cases} />;
  } catch {
    return <BackendOfflineNotice />;
  }
}
