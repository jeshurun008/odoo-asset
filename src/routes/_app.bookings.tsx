import { createFileRoute } from "@tanstack/react-router";
import { ModuleStub } from "@/components/shell/ModuleStub";

export const Route = createFileRoute("/_app/bookings")({
  component: () => (
    <ModuleStub
      title="Bookings"
      kicker="Scheduling"
      description="Reserve shared assets, rooms, and vehicles without collisions."
    />
  ),
  head: () => ({ meta: [{ title: "Bookings — AssetFlow" }] }),
});