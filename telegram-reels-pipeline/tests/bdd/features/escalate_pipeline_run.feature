Feature: Escalate pipeline run to operator
  As a pipeline operator
  I want failed or stuck pipeline runs to be escalated automatically
  So that I can intervene and resolve issues without losing progress

  Scenario: Unknown layout triggers escalation
    Given a pipeline run "run-bdd-layout-001" is in progress
    When the pipeline encounters an unknown layout at stage "layout_detective"
    Then a layout_unknown escalation event is emitted
    And a pipeline_paused event is emitted
    And the run projection execution_status is "paused"
    And the run projection escalation_status is "layout_unknown"

  Scenario: QA exhaustion triggers escalation
    Given a pipeline run "run-bdd-qa-001" is in progress
    When the pipeline exhausts all QA retries at stage "transcript"
    Then a qa_exhausted escalation event is emitted
    And a pipeline_paused event is emitted
    And the run projection execution_status is "paused"
    And the run projection escalation_status is "qa_exhausted"
