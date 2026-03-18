import { useCallback, useState } from "react";
import { useBreakpoint } from "@/core/hooks/useBreakpoint";
import { TriggerRunForm } from "@/core/organisms/TriggerRunForm/TriggerRunForm";
import { useTriggerRun } from "@/app/hooks/useTriggerRun";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import type { TriggerRunFormValues } from "@/core/organisms/TriggerRunForm/triggerRunFormInterface";

export function DashboardTriggerDialog() {
  const { isMobile } = useBreakpoint();
  const { triggerPipelineRun, isSubmitting } = useTriggerRun();
  const [isOpen, setIsOpen] = useState(false);

  const handleFormSubmit = useCallback(
    async (formValues: TriggerRunFormValues) => {
      await triggerPipelineRun({
        youtubeUrl: formValues.youtubeUrl,
        topicFocus: formValues.topicFocus || undefined,
      });
      setIsOpen(false);
    },
    [triggerPipelineRun],
  );

  const handleOpenDialog = useCallback(() => {
    setIsOpen(true);
  }, []);

  const formContent = (
    <TriggerRunForm onSubmit={handleFormSubmit} isSubmitting={isSubmitting} />
  );

  return (
    <>
      <Button onClick={handleOpenDialog} data-testid="trigger-run-button">
        Trigger New Run
      </Button>
      {isMobile ? (
        <Drawer open={isOpen} onOpenChange={setIsOpen}>
          <DrawerContent>
            <DrawerHeader>
              <DrawerTitle>Start Pipeline Run</DrawerTitle>
            </DrawerHeader>
            <div className="p-4">{formContent}</div>
          </DrawerContent>
        </Drawer>
      ) : (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Start Pipeline Run</DialogTitle>
            </DialogHeader>
            {formContent}
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
