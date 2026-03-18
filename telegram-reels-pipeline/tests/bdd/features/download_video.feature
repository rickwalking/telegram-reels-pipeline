Feature: Video Download Stage
  As the pipeline orchestrator
  I want to run the video download stage for a YouTube URL
  So that the event store records stage_entered and stage_completed events

  Scenario: Successfully download video emits events
    Given a pipeline run with id "run-bdd-2026-03-18"
    And a YouTube URL "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    When the download video use case executes
    Then a "pipeline.stage_entered" event is emitted for stage "research"
    And a "pipeline.stage_completed" event is emitted for stage "research"
    And all events carry the pipeline run id "run-bdd-2026-03-18"
