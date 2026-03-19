Feature: JsonPayloadViewer
  Syntax-highlighted, collapsible JSON tree with copy support.

  Scenario: Renders string values with quotes
    Given a JsonPayloadViewer with data containing a string key
    Then the string value is displayed with double quotes

  Scenario: Renders number values
    Given a JsonPayloadViewer with data containing a number key
    Then the number value is displayed

  Scenario: Renders boolean values
    Given a JsonPayloadViewer with data containing a boolean key
    Then the boolean value is displayed

  Scenario: Renders null values
    Given a JsonPayloadViewer with data containing a null key
    Then the word "null" is displayed

  Scenario: Renders copy button
    Given a JsonPayloadViewer with any data
    Then a "Copy JSON" button is present

  Scenario: Supports collapsible nested objects
    Given a JsonPayloadViewer with nested object data
    Then toggle buttons are present for collapsible sections

  Scenario: Starts collapsed when configured
    Given a JsonPayloadViewer with initialCollapsed true
    Then nested sections show collapsed count hints

  Scenario: Dark mode aware
    Given a JsonPayloadViewer rendered in dark mode
    Then syntax colors adjust to dark theme tokens
