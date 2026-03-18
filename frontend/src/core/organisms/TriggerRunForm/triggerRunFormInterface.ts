export interface TriggerRunFormValues {
  readonly youtubeUrl: string;
  readonly topicFocus: string;
}

export interface TriggerRunFormProps {
  readonly onSubmit: (formValues: TriggerRunFormValues) => Promise<void>;
  readonly isSubmitting: boolean;
}
