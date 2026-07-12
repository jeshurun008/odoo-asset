import { createFileRoute } from "@tanstack/react-router";
import { ModuleStub } from "@/components/shell/ModuleStub";

export const Route = createFileRoute("/_app/audits")({
  component: () => (
    <ModuleStub
      title="Audits"
      kicker="Verification"
      description="Cycle counts and reconciliation across every location."
    />
  ),
  head: () => ({ meta: [{ title: "Audits — AssetFlow" }] }),
});