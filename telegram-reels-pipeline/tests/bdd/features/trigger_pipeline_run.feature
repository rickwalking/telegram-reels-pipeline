Feature: Trigger Pipeline Run
  As a System Operator
  I want to trigger a new pipeline run via the REST API
  So that I can start processing a YouTube URL

  Scenario: Successfully trigger a new pipeline run
    Given the API is running
    When I send a POST request to "/api/runs" with a valid YouTube URL
    Then I should receive a 201 response with the new run ID
