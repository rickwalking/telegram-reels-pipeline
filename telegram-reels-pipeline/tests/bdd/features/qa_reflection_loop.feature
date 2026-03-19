Feature: QA Reflection Loop — Event-Sourced Gate Results
  As the pipeline system
  I want every QA gate result recorded as a domain event
  So that the full evaluation history is observable and replay-able

  Background:
    Given a fresh event bus with a fake event store

  Scenario: QA gate passes on first attempt
    Given a QA evaluation command for run "run-pass-001" stage "research" with decision "PASS" and score 92
    When the EvaluateStageOutputUseCase executes the command
    Then a "qa_gate.passed" event is emitted
    And the event carries pipeline_run_id "run-pass-001"
    And the event carries stage_name "research"
    And the event carries critique_score 92

  Scenario: QA gate requests rework
    Given a QA evaluation command for run "run-rework-002" stage "transcript" with decision "REWORK" and score 58
    When the EvaluateStageOutputUseCase executes the command
    Then a "qa_gate.rework" event is emitted
    And the event carries pipeline_run_id "run-rework-002"
    And the event carries stage_name "transcript"
    And the event carries critique_score 58

  Scenario: Best-of-three selector returns the highest scoring attempt
    Given three QA evaluation commands with scores 50, 75, and 60
    When the best attempt is selected
    Then the selected attempt has score 75

  Scenario: Best-of-three selector returns best even when all below threshold
    Given three QA evaluation commands with scores 20, 35, and 28
    When the best attempt is selected
    Then the selected attempt has score 35
