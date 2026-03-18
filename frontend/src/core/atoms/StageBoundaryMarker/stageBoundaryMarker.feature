Feature: StageBoundaryMarker
  A decorative divider between pipeline stages on the DVR timeline.

  Scenario: Renders with aria-hidden true
    Given a StageBoundaryMarker for stage "ROUTER"
    Then the root element has aria-hidden true

  Scenario: Displays stage name
    Given a StageBoundaryMarker for stage "ROUTER"
    Then the stage name "ROUTER" is visible

  Scenario: Displays duration in a time element
    Given a StageBoundaryMarker with duration 42.5 seconds
    Then a time element shows "42.5s"
    And the time element has a valid ISO datetime attribute

  Scenario: Formats long durations with minutes
    Given a StageBoundaryMarker with duration 125 seconds
    Then the time element shows "2m 5s"

  Scenario: Uses tabular-nums for duration display
    Given a StageBoundaryMarker with any duration
    Then the duration element has font-variant-numeric tabular-nums
