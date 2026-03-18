import { useParams } from "@tanstack/react-router";
import { runDvrRoute } from "@/app/routes/routeTree";

export function RunDvrPage() {
  const { runId } = useParams({ from: runDvrRoute.id });

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Pipeline DVR</h1>
      <p className="text-muted-foreground mt-2">
        Live event stream for run:{" "}
        <code className="text-sm">{runId}</code>
      </p>
    </div>
  );
}
