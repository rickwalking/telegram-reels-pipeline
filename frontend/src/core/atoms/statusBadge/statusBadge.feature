Feature: StatusBadge
  The StatusBadge atom renders a colored badge for pipeline run statuses.

  Scenario: Renders pending variant with default label
    Given a StatusBadge with variant "pending"
    Then the badge displays "Pending"
    And the badge has variant "pending"

  Scenario: Renders active variant with default label
    Given a StatusBadge with variant "active"
    Then the badge displays "Active"
    And the badge has variant "active"

  Scenario: Renders completed variant with default label
    Given a StatusBadge with variant "completed"
    Then the badge displays "Completed"
    And the badge has variant "completed"

  Scenario: Renders failed variant with default label
    Given a StatusBadge with variant "failed"
    Then the badge displays "Failed"
    And the badge has variant "failed"

  Scenario: Renders paused variant with default label
    Given a StatusBadge with variant "paused"
    Then the badge displays "Paused"
    And the badge has variant "paused"

  Scenario: Renders with custom label
    Given a StatusBadge with variant "active" and label "Processing"
    Then the badge displays "Processing"

  Scenario: Accepts custom className
    Given a StatusBadge with variant "completed" and className "ml-2"
    Then the badge has additional class "ml-2"
