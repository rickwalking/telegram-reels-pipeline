Feature: Run List Item
  Scenario: Renders run details with status badge
    Given a RunListItem with status "active"
    Then the StatusBadge should show "Active"
    And the YouTube URL should be visible
    And the timestamp should be formatted

  Scenario: Links to run detail page
    Given a RunListItem with pipelineRunId "run-001"
    Then the item should link to "/runs/run-001"

  Scenario: Truncates long YouTube URLs
    Given a RunListItem with a very long URL
    Then the URL should be truncated

  Scenario: Prefetches on pointer enter
    Given a RunListItem
    When the user hovers over the item
    Then onPrefetch should be called
