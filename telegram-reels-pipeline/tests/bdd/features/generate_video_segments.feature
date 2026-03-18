Feature: Generate Video Segments
  As the pipeline orchestrator
  I want to execute the FFmpeg segment generation stage
  So that the pipeline emits structured events with segment artifact paths

  Background:
    Given an EventBus with no subscribers

  Scenario: Emits stage_entered when segment generation begins
    Given a GenerateSegmentsCommand with pipeline_run_id "run-20260318-abc123"
    When the GenerateVideoSegmentsUseCase executes the command
    Then a "pipeline.stage_entered" event is emitted
    And the event stage is "ffmpeg_engineer"
    And the event data includes pipeline_run_id "run-20260318-abc123"

  Scenario: Emits stage_completed with segment artifact paths
    Given a GenerateSegmentsCommand with pipeline_run_id "run-20260318-abc123"
    When the GenerateVideoSegmentsUseCase executes the command
    Then a "pipeline.stage_completed" event is emitted
    And the event stage is "ffmpeg_engineer"
    And the stage_completed event data includes at least one ".mp4" artifact path

  Scenario: stage_entered is published before stage_completed
    Given a GenerateSegmentsCommand with pipeline_run_id "run-20260318-abc123"
    When the GenerateVideoSegmentsUseCase executes the command
    Then "pipeline.stage_entered" is published before "pipeline.stage_completed"

  Scenario: Artifact paths include the pipeline run identifier
    Given a GenerateSegmentsCommand with pipeline_run_id "run-20260318-abc123"
    When the GenerateVideoSegmentsUseCase executes the command
    Then every artifact path in stage_completed contains "run-20260318-abc123"

  Scenario: Empty pipeline_run_id is rejected at command construction
    Given an empty pipeline_run_id
    When a GenerateSegmentsCommand is constructed
    Then a ValueError is raised with message "pipeline_run_id must not be empty"
