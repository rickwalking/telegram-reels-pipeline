Feature: Document Carousel
  Scenario: Renders tabs for each artifact
    Given a DocumentCarousel with 3 artifacts
    Then 3 tab triggers should be visible

  Scenario: Displays JSON artifact with payload viewer
    Given a DocumentCarousel with a JSON artifact
    When the JSON tab is active
    Then the JsonPayloadViewer should render the payload

  Scenario: Displays markdown content as text
    Given a DocumentCarousel with a markdown artifact
    When the markdown tab is active
    Then the markdown content should be visible

  Scenario: Displays download link for binary artifacts
    Given a DocumentCarousel with a binary artifact
    When the binary tab is active
    Then a download link should be visible

  Scenario: Shows CopyButton for JSON artifacts
    Given a DocumentCarousel with a JSON artifact active
    Then a CopyButton should be visible

  Scenario: Calls onTabChange when a tab is clicked
    Given a DocumentCarousel with multiple artifacts
    When the user clicks a different tab
    Then onTabChange should be called with the tab name
