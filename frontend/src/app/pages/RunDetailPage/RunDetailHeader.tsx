import { useCallback, useState } from "react";
import { Link } from "@tanstack/react-router";
import { StatusBadge } from "@/core/atoms/statusBadge/StatusBadge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import type { StatusBadgeVariant } from "@/core/atoms/statusBadge/statusBadgeInterface";

interface RunDetailHeaderProps {
  readonly pipelineRunId: string;
  readonly executionStatus: StatusBadgeVariant;
  readonly onPause: () => Promise<void>;
  readonly onResume: () => Promise<void>;
}

export function RunDetailHeader({
  pipelineRunId,
  executionStatus,
  onPause,
  onResume,
}: RunDetailHeaderProps) {
  const [isActionPending, setIsActionPending] = useState(false);
  const isActive = executionStatus === "active";
  const isPaused = executionStatus === "paused";

  const handlePauseConfirm = useCallback(async () => {
    setIsActionPending(true);
    await onPause();
    setIsActionPending(false);
  }, [onPause]);

  const handleResume = useCallback(async () => {
    setIsActionPending(true);
    await onResume();
    setIsActionPending(false);
  }, [onResume]);

  return (
    <header className="flex items-center gap-3 px-6 py-4 border-b border-border" data-testid="run-detail-header">
      <Link to="/" className="text-sm text-muted-foreground hover:text-foreground">
        &larr; Back
      </Link>
      <h1 className="text-lg font-semibold tracking-tight">
        Run <code className="text-sm font-mono">{pipelineRunId}</code>
      </h1>
      <StatusBadge variant={executionStatus} />
      <div className="ml-auto flex gap-2">
        {isActive ? (
          <AlertDialog>
            <AlertDialogTrigger render={<Button variant="outline" size="sm" data-testid="pause-button" disabled={isActionPending} />}>
              Pause
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Pause Pipeline Run?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will pause the current pipeline run. You can resume it later.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handlePauseConfirm} data-testid="confirm-pause">
                  Pause Run
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        ) : null}
        {isPaused ? (
          <Button
            variant="outline"
            size="sm"
            onClick={handleResume}
            disabled={isActionPending}
            data-testid="resume-button"
          >
            Resume
          </Button>
        ) : null}
        <Link to="/runs/$runId/dvr" params={{ runId: pipelineRunId }}>
          <Button variant="ghost" size="sm" data-testid="dvr-link">
            DVR Timeline
          </Button>
        </Link>
      </div>
    </header>
  );
}
