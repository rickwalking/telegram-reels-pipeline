Feature: Detect Camera Layout
  As the pipeline system
  I want to detect the camera layout for a pipeline run
  So that downstream stages can apply the correct framing strategy

  Background:
    Given a DetectCameraLayoutUseCase with a fake event emitter

  Scenario: Successfully detecting a known layout emits stage events
    Given the layout detector returns a known layout "duo_split"
    When the use case executes with pipeline_run_id "run-known-001"
    Then a stage_entered event is emitted for the LAYOUT_DETECTIVE stage
    And a stage_completed event is emitted for the LAYOUT_DETECTIVE stage
    And no escalation_requested event is emitted

  Scenario: Unknown layout triggers escalation instead of completion
    Given the layout detector returns an unknown layout
    When the use case executes with pipeline_run_id "run-unknown-001"
    Then a stage_entered event is emitted for the LAYOUT_DETECTIVE stage
    And an escalation_requested event is emitted for the LAYOUT_DETECTIVE stage
    And no stage_completed event is emitted

  Scenario: Command requires a non-empty pipeline_run_id
    Given a DetectLayoutCommand with an empty pipeline_run_id
    Then creating the command raises a ValueError

  Scenario: Stage name defaults to layout_detective
    Given a DetectLayoutCommand with pipeline_run_id "run-default-001"
    Then the command stage_name is "layout_detective"
