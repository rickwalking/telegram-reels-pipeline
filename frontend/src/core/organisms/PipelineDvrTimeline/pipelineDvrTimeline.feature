Feature: PipelineDvrTimeline
  Main timeline organism with event markers, stage boundaries, and keyboard navigation.

  Scenario: Shows loading state
    Given events are being fetched
    Then a loading indicator is displayed

  Scenario: Shows error state with retry
    Given fetching events failed
    Then an error message is displayed
    And a retry button is available

  Scenario: Shows empty state
    Given no events exist for the run
    Then a "No events recorded" message is displayed

  Scenario: Renders event markers for each event
    Given 3 events exist for the run
    Then 3 event marker buttons are rendered

  Scenario: Selects event on click
    Given events are displayed
    When the user clicks an event marker
    Then onSelectEvent is called with the event ID

  Scenario: Keyboard Right navigates to next event
    Given event "evt-0" is selected
    When the user presses ArrowRight
    Then onSelectEvent is called with "evt-1"

  Scenario: Keyboard Left wraps to last event
    Given event "evt-0" is selected
    When the user presses ArrowLeft
    Then onSelectEvent is called with the last event ID

  Scenario: Virtualizes large event lists
    Given more than 50 events exist
    Then a virtualization notice is displayed

  Scenario: Renders stage boundary markers
    Given stage boundaries are provided
    Then boundary dividers appear between stages
