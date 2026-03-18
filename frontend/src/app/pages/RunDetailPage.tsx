import { useParams } from "@tanstack/react-router";
import { runDetailRoute } from "@/app/routes/routeTree";

export function RunDetailPage() {
  const { runId } = useParams({ from: runDetailRoute.id });

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Run Detail</h1>
      <p className="text-muted-foreground mt-2">
        Viewing run: <code className="text-sm">{runId}</code>
      </p>
    </div>
  );
}
