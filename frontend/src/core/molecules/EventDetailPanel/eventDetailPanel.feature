Feature: EventDetailPanel
  Side panel (desktop) / bottom sheet (mobile) showing event details.

  Scenario: Shows empty state when no event selected
    Given no event is selected
    Then the panel shows "Select an event to view details"

  Scenario: Displays event name
    Given an event "pipeline.stage_entered" is selected
    Then the event name is displayed as heading

  Scenario: Displays event ID with copy button
    Given an event with ID "evt-abc123" is selected
    Then the event ID is displayed
    And a "Copy ID" button is available

  Scenario: Displays timestamp in time element
    Given an event with timestamp "2026-03-18T10:00:00Z"
    Then a time element shows the timestamp

  Scenario: Displays stage when present
    Given an event with stage "router"
    Then the stage name "router" is shown

  Scenario: Hides stage when null
    Given an event with no stage
    Then no stage label is shown

  Scenario: Shows JSON payload viewer
    Given an event with payload data
    Then the JsonPayloadViewer is rendered

  Scenario: Close button fires callback
    Given an event is selected
    When the close button is clicked
    Then onClose callback is invoked
