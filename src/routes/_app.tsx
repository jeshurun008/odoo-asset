import { Outlet, createFileRoute } from "@tanstack/react-router";
import Sidebar from "@/components/shell/Sidebar";
import Topbar from "@/components/shell/Topbar";

export const Route = createFileRoute("/_app")({
  component: AppShell,
});

function AppShell() {
  return (
    <div className="min-h-screen text-foreground flex">
      <Sidebar />
      <div className="flex-1 min-w-0 flex flex-col">
        <Topbar />
        <main className="flex-1 min-w-0 px-4 md:px-6 pb-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}