Feature: Event-Driven State Transitions
  Pipeline stage lifecycle events are recorded and projections are updated.

  Scenario: Stage completion emits event before proceeding
    Given a pipeline run in "router" stage
    When the stage completes successfully
    Then a "pipeline.stage_completed" event is recorded
    And the projection shows the next stage

  Scenario: Error emits event and marks run failed
    Given a pipeline run in "research" stage
    When an error occurs with message "agent timeout"
    Then a "pipeline.error_occurred" event is recorded
    And the projection execution status is "failed"
