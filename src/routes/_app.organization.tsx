import { createFileRoute } from "@tanstack/react-router";
import { ModuleStub } from "@/components/shell/ModuleStub";

export const Route = createFileRoute("/_app/organization")({
  component: () => (
    <ModuleStub
      title="Organization"
      kicker="Structure"
      description="Locations, teams, and ownership — the map behind every asset."
    />
  ),
  head: () => ({ meta: [{ title: "Organization — AssetFlow" }] }),
});