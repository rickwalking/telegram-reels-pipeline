Feature: Pause Pipeline Run
  As a pipeline operator
  I want to pause an in-progress pipeline run
  So that I can temporarily halt processing without losing state

  Scenario: Pause active run
    Given a pipeline run "run-bdd-active-001" is in progress at stage "research"
    When I send a pause request for run "run-bdd-active-001" with reason "scheduled maintenance"
    Then the response execution_status is "in_progress"
    And a "pipeline.run_paused" event is emitted for run "run-bdd-active-001"
    And the event contains reason "scheduled maintenance"

  Scenario: Attempt to pause already-completed run returns 400
    Given a pipeline run "run-bdd-completed-001" has completed
    When I send a pause request for run "run-bdd-completed-001" with reason "no reason"
    Then a ValidationError is raised with "completed" in the message
    And no "pipeline.run_paused" event is emitted
