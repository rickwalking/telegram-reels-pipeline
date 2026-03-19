Feature: Stage Step
  Scenario: Renders stage name and status circle
    Given a StageStep with stageName "router" and status "completed"
    Then the step should display "router"
    And the status circle should have a green color

  Scenario: Displays formatted duration
    Given a StageStep with durationSeconds 125
    Then the step should display "2m 5s"
    And the duration should use tabular-nums font variant

  Scenario: Pulses when active with motion allowed
    Given a StageStep with status "active" and isActive true
    And the user allows animations
    Then the status circle should have a pulse animation

  Scenario: Does not pulse when reduced motion is preferred
    Given a StageStep with status "active" and isActive true
    And the user prefers reduced motion
    Then the status circle should not pulse

  Scenario: Touch target meets minimum size
    Given any StageStep
    Then the button should have at least 44x44px touch target
