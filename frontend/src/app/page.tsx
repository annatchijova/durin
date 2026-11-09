import { listCases } from "@/lib/api";
import { DashboardView } from "@/components/DashboardView";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const { cases } = await listCases();
  return <DashboardView cases={cases} />;
}
