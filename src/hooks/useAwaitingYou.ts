import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Matches app/schemas/allocation.py::AssetAllocationResponse
interface AssetAllocationResponse {
  id: string;
  asset_id: string;
  status: "ACTIVE" | "OVERDUE" | "RETURNED";
}

// Matches app/schemas/audit.py::AuditCycleResponse
interface AuditCycleResponse {
  id: string;
  name: string;
  status: "PLANNED" | "IN_PROGRESS" | "CLOSED";
}

export interface AwaitingItem {
  id: string;
  label: string;
  to: string;
  kind: "overdue" | "audit";
}

/**
 * Real actionable items only. There is no "approve allocation" or "confirm
 * booking" workflow in the backend (allocations/bookings have no pending
 * state) — so this surfaces what actually exists: overdue allocations and
 * audits still in progress. Returns an empty list if nothing needs
 * attention, rather than showing placeholder items.
 */
export function useAwaitingYou() {
  const allocationsQuery = useQuery({
    queryKey: ["allocations", "overdue-check"],
    queryFn: () =>
      api.get<PaginatedResponse<AssetAllocationResponse>>(
        "/allocations?page_size=100"
      ),
  });

  const auditsQuery = useQuery({
    queryKey: ["audits", "in-progress-check"],
    queryFn: () =>
      api.get<PaginatedResponse<AuditCycleResponse>>("/audits?page_size=100"),
  });

  const isLoading = allocationsQuery.isLoading || auditsQuery.isLoading;
  const isError = allocationsQuery.isError || auditsQuery.isError;

  const items: AwaitingItem[] = [];

  const overdueCount =
    allocationsQuery.data?.items.filter((a) => a.status === "OVERDUE")
      .length ?? 0;

  if (overdueCount > 0) {
    items.push({
      id: "overdue-allocations",
      label:
        overdueCount === 1
          ? "1 asset overdue for return"
          : `${overdueCount} assets overdue for return`,
      to: "/allocations",
      kind: "overdue",
    });
  }

  const inProgressAudits =
    auditsQuery.data?.items.filter((a) => a.status === "IN_PROGRESS") ?? [];

  for (const audit of inProgressAudits) {
    items.push({
      id: `audit-${audit.id}`,
      label: `${audit.name} — in progress`,
      to: "/audits",
      kind: "audit",
    });
  }

  return { items, isLoading, isError };
}
