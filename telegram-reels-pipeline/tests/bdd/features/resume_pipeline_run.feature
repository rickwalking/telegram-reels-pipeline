Feature: Resume Pipeline Run
  As a pipeline operator
  I want to resume a paused pipeline run via the API
  So that interrupted runs can continue from where they left off

  Background:
    Given a pipeline run exists in a paused state

  Scenario: Successfully resume a paused pipeline run
    When I send a POST request to resume the run
    Then the response status is 200
    And the response body contains execution_status "running"

  Scenario: Resume with operator notes records them in the projection
    When I send a POST request to resume the run with notes "Manual QA override"
    Then the response status is 200
    And the response body contains operator_notes "Manual QA override"

  Scenario: Attempt to resume a run that is already running returns 409
    Given a pipeline run exists in a running state
    When I send a POST request to resume the running run
    Then the response status is 409

  Scenario: Attempt to resume a run that does not exist returns 404
    When I send a POST request to resume a nonexistent run
    Then the response status is 404

  Scenario: Attempt to resume a completed run returns 400
    Given a pipeline run exists in a completed state
    When I send a POST request to resume the completed run
    Then the response status is 400
