import { createFileRoute } from "@tanstack/react-router";
import { ModuleStub } from "@/components/shell/ModuleStub";

export const Route = createFileRoute("/_app/maintenance")({
  component: () => (
    <ModuleStub
      title="Maintenance"
      kicker="Care"
      description="Preventive schedules, work orders, and downtime logs."
    />
  ),
  head: () => ({ meta: [{ title: "Maintenance — AssetFlow" }] }),
});