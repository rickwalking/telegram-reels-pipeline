Feature: Trigger Pipeline Run
  As an API consumer
  I want to trigger a new pipeline run via POST /api/runs
  So that the pipeline begins processing a YouTube video

  Scenario: Successfully trigger a pipeline run with a valid YouTube URL
    Given a valid YouTube URL "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    And a topic focus "AI and machine learning"
    When I send a POST request to "/api/runs" with the run payload
    Then the response status code should be 201
    And the response should contain a pipeline_run_id
    And the response execution_status should be "pending"
    And the response trigger_source should be "api"

  Scenario: Reject a request with an invalid YouTube URL
    Given an invalid YouTube URL "not-a-valid-url"
    When I send a POST request to "/api/runs" with the invalid payload
    Then the response status code should be 422
