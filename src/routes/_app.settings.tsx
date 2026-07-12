import { createFileRoute } from "@tanstack/react-router";
import { ModuleStub } from "@/components/shell/ModuleStub";

export const Route = createFileRoute("/_app/settings")({
  component: () => (
    <ModuleStub
      title="Settings"
      kicker="Workspace"
      description="Roles, integrations, and organization preferences."
    />
  ),
  head: () => ({ meta: [{ title: "Settings — AssetFlow" }] }),
});