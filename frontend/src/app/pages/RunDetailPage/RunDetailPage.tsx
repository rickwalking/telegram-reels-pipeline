import { Suspense } from "react";
import { RunDetailContent } from "./RunDetailContent";

function RunDetailSkeleton() {
  return (
    <div className="flex flex-col gap-4 p-6" data-testid="run-detail-skeleton">
      <div className="h-10 w-64 rounded-md bg-muted/50 animate-pulse" />
      <div className="flex gap-2">
        {Array.from({ length: 7 }, (_, skeletonIndex) => (
          <div
            key={skeletonIndex}
            className="h-8 w-24 rounded-md bg-muted/50 animate-pulse"
          />
        ))}
      </div>
      <div className="h-64 rounded-lg bg-muted/50 animate-pulse" />
    </div>
  );
}

export function RunDetailPage() {
  return (
    <Suspense fallback={<RunDetailSkeleton />}>
      <RunDetailContent />
    </Suspense>
  );
}
