Feature: Copy Button
  Scenario: Copies content to clipboard on click
    Given a CopyButton with content "hello world" and label "Copy"
    When the user clicks the button
    Then the clipboard should contain "hello world"
    And the button should show a checkmark confirmation

  Scenario: Shows accessible confirmation announcement
    Given a CopyButton with content "payload text" and label "Copy JSON"
    When the user clicks the button
    Then the confirmation region should have aria-live="polite"

  Scenario: Renders ghost variant
    Given a CopyButton with variant "ghost"
    Then the button should not have a visible border

  Scenario: Resets confirmation after delay
    Given a CopyButton that was just clicked
    When 2 seconds pass
    Then the button should return to its default label
