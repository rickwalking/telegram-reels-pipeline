Feature: Analyze Transcript Stage
  As the pipeline orchestrator
  I want the transcript analysis stage to emit lifecycle events
  So that observers can track stage progress in real time

  Background:
    Given a pipeline run with id "run-abc-123"

  Scenario: Stage emits entered and completed events for the transcript stage
    Given a fresh AnalyzeTranscriptUseCase with a recording event emitter
    When the use case executes an AnalyzeTranscriptCommand for the pipeline run
    Then a stage_entered event is emitted with stage name "transcript"
    And a stage_completed event is emitted with stage name "transcript"

  Scenario: Stage entered is always emitted before stage completed
    Given a fresh AnalyzeTranscriptUseCase with a recording event emitter
    When the use case executes an AnalyzeTranscriptCommand for the pipeline run
    Then the stage_entered event is recorded before the stage_completed event

  Scenario: Custom stage name is propagated to both lifecycle events
    Given a fresh AnalyzeTranscriptUseCase with a recording event emitter
    When the use case executes an AnalyzeTranscriptCommand with stage name "custom-transcript"
    Then a stage_entered event is emitted with stage name "custom-transcript"
    And a stage_completed event is emitted with stage name "custom-transcript"
