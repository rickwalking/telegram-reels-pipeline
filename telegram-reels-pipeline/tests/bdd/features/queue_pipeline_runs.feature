Feature: Queue Pipeline Runs
  As a System Operator
  I want incoming pipeline requests to be queued and processed sequentially
  So that the system does not exceed memory or CPU constraints

  Scenario: First run starts immediately when no other runs are active
    Given no pipeline runs exist in the system
    When I trigger a new pipeline run with URL "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    And the orchestrator claims the next pending run
    Then the claimed run execution_status should be "in_progress"
    And exactly 1 event should be emitted for the claimed run

  Scenario: Second run queues while first is active
    Given a pipeline run with URL "https://www.youtube.com/watch?v=first11chars" is "in_progress"
    When I trigger a new pipeline run with URL "https://www.youtube.com/watch?v=second1chars"
    Then the new run execution_status should be "pending"
    And the system should have 2 total pipeline runs
