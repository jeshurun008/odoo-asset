import { createFileRoute } from "@tanstack/react-router";
import { ModuleStub } from "@/components/shell/ModuleStub";

export const Route = createFileRoute("/_app/reports")({
  component: () => (
    <ModuleStub
      title="Reports"
      kicker="Insights"
      description="Utilization, depreciation, and movement — sliced any way you need."
    />
  ),
  head: () => ({ meta: [{ title: "Reports — AssetFlow" }] }),
});