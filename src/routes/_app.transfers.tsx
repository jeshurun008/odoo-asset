import { createFileRoute } from "@tanstack/react-router";
import { ModuleStub } from "@/components/shell/ModuleStub";

export const Route = createFileRoute("/_app/transfers")({
  component: () => (
    <ModuleStub
      title="Transfers"
      kicker="In motion"
      description="Movements between locations, teams, and custodians."
    />
  ),
  head: () => ({ meta: [{ title: "Transfers — AssetFlow" }] }),
});