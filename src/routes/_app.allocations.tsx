import { createFileRoute } from "@tanstack/react-router";
import { ModuleStub } from "@/components/shell/ModuleStub";

export const Route = createFileRoute("/_app/allocations")({
  component: () => (
    <ModuleStub
      title="Allocations"
      kicker="Assignments"
      description="Who has what, since when, and for how long."
    />
  ),
  head: () => ({ meta: [{ title: "Allocations — AssetFlow" }] }),
});