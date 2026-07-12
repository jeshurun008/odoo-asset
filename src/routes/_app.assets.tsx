import { createFileRoute } from "@tanstack/react-router";
import { ModuleStub } from "@/components/shell/ModuleStub";

export const Route = createFileRoute("/_app/assets")({
  component: () => (
    <ModuleStub
      title="Assets"
      kicker="Inventory"
      description="Every device, tool, and tracked resource — one searchable ledger."
    />
  ),
  head: () => ({ meta: [{ title: "Assets — AssetFlow" }] }),
});