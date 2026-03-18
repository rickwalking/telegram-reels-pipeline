import { Suspense } from "react";
import { DashboardRunList } from "./DashboardRunList";
import { DashboardTriggerDialog } from "./DashboardTriggerDialog";

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-2 p-6" data-testid="dashboard-skeleton">
      {Array.from({ length: 3 }, (_, skeletonIndex) => (
        <div
          key={skeletonIndex}
          className="h-14 rounded-lg border border-border bg-muted/50 animate-pulse"
        />
      ))}
    </div>
  );
}

export function DashboardPage() {
  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Pipeline Runs</h1>
          <p className="text-sm text-muted-foreground mt-1">
            View and manage pipeline runs.
          </p>
        </div>
        <DashboardTriggerDialog />
      </div>
      <Suspense fallback={<DashboardSkeleton />}>
        <DashboardRunList />
      </Suspense>
    </div>
  );
}
