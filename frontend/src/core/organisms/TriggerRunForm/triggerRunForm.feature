Feature: Trigger Run Form
  Scenario: Validates YouTube URL format
    Given a TriggerRunForm
    When the user enters an invalid URL
    And submits the form
    Then an inline error should appear for the URL field

  Scenario: Submits valid form data
    Given a TriggerRunForm
    When the user enters a valid YouTube URL
    And a topic focus
    And submits the form
    Then onSubmit should be called with the form values

  Scenario: Shows loading spinner during submission
    Given a TriggerRunForm with isSubmitting true
    Then the submit button should show a loading spinner
    And the submit button should be disabled

  Scenario: URL input has correct attributes
    Given a TriggerRunForm
    Then the URL input should have type "url"
    And the URL input should have autocomplete "off"
    And the URL input should have spellcheck false
