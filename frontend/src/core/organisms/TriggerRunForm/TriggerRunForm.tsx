import { useCallback } from "react";
import { useForm } from "@tanstack/react-form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useBreakpoint } from "@/core/hooks/useBreakpoint";
import type { TriggerRunFormProps, TriggerRunFormValues } from "./triggerRunFormInterface";

const YOUTUBE_URL_PATTERN = /^https:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]+/;
const YOUTUBE_URL_ERROR = "Enter a valid YouTube URL (https://www.youtube.com/watch?v=...)";
const URL_REQUIRED_ERROR = "YouTube URL is required";

function validateYoutubeUrl(urlInput: string): string | undefined {
  if (urlInput.trim().length === 0) return URL_REQUIRED_ERROR;
  if (!YOUTUBE_URL_PATTERN.test(urlInput)) return YOUTUBE_URL_ERROR;
  return undefined;
}

export function TriggerRunForm({ onSubmit, isSubmitting }: TriggerRunFormProps) {
  const { isMobile } = useBreakpoint();

  const triggerForm = useForm({
    defaultValues: { youtubeUrl: "", topicFocus: "" },
    onSubmit: async ({ value: formValues }) => {
      const submitValues: TriggerRunFormValues = {
        youtubeUrl: formValues.youtubeUrl.trim(),
        topicFocus: formValues.topicFocus.trim(),
      };
      await onSubmit(submitValues);
    },
  });

  const handleFormSubmit = useCallback(
    (formEvent: React.FormEvent) => {
      formEvent.preventDefault();
      formEvent.stopPropagation();
      triggerForm.handleSubmit();
    },
    [triggerForm],
  );

  return (
    <form onSubmit={handleFormSubmit} className="space-y-4" data-testid="trigger-run-form">
      <triggerForm.Field
        name="youtubeUrl"
        validators={{ onBlur: ({ value: fieldValue }) => validateYoutubeUrl(fieldValue) }}
      >
        {(urlField) => (
          <div className="space-y-1.5">
            <label htmlFor="youtube-url-input" className="text-sm font-medium">
              YouTube URL
            </label>
            <Input
              id="youtube-url-input"
              type="url"
              autoComplete="off"
              spellCheck={false}
              autoFocus={!isMobile}
              placeholder="https://www.youtube.com/watch?v=..."
              value={urlField.state.value}
              onChange={(changeEvent) => urlField.handleChange(changeEvent.target.value)}
              onBlur={urlField.handleBlur}
              aria-invalid={urlField.state.meta.errors.length > 0}
              data-testid="youtube-url-input"
            />
            {urlField.state.meta.errors.length > 0 ? (
              <p className="text-xs text-destructive" role="alert" data-testid="url-error">
                {urlField.state.meta.errors.join(", ")}
              </p>
            ) : null}
          </div>
        )}
      </triggerForm.Field>

      <triggerForm.Field name="topicFocus">
        {(topicField) => (
          <div className="space-y-1.5">
            <label htmlFor="topic-focus-input" className="text-sm font-medium">
              Topic Focus (optional)
            </label>
            <Input
              id="topic-focus-input"
              type="text"
              placeholder="e.g., AI Safety, Machine Learning"
              value={topicField.state.value}
              onChange={(changeEvent) => topicField.handleChange(changeEvent.target.value)}
              data-testid="topic-focus-input"
            />
          </div>
        )}
      </triggerForm.Field>

      <Button type="submit" disabled={isSubmitting} className="w-full" data-testid="submit-button">
        {isSubmitting ? (
          <span className="inline-flex items-center gap-2">
            <svg
              className="size-4 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z" />
            </svg>
            Starting...
          </span>
        ) : (
          "Start Pipeline Run"
        )}
      </Button>
    </form>
  );
}
