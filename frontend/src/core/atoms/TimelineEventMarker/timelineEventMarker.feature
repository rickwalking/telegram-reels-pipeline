Feature: TimelineEventMarker
  A color-coded button that marks a pipeline event on the DVR timeline.

  Scenario: Renders button with accessible label
    Given a TimelineEventMarker for event "pipeline.stage_entered"
    Then the marker renders a button element
    And the button has an aria-label containing the event name

  Scenario: Minimum touch target size
    Given a TimelineEventMarker for any event
    Then the button has minimum 44x44px via Tailwind min-w-11 min-h-11

  Scenario: Color coded by event type
    Given a TimelineEventMarker for event "pipeline.stage_completed"
    Then the dot indicator uses the green color class

  Scenario: Calls onSelect with event ID when clicked
    Given a TimelineEventMarker with eventId "evt-123"
    When the user clicks the marker
    Then onSelect is called with "evt-123"

  Scenario: Shows selected state
    Given a TimelineEventMarker that is selected
    Then the button has aria-pressed true
    And the button has a visible ring border

  Scenario: Displays short event name
    Given a TimelineEventMarker for event "pipeline.stage_entered"
    Then the label shows "stage_entered"
