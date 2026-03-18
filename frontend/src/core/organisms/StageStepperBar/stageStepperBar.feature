Feature: Stage Stepper Bar
  Scenario: Renders all pipeline stages in order
    Given a StageStepperBar with 7 stages
    Then all 7 stages should be visible in an ordered list

  Scenario: Marks active stage with aria-current
    Given a StageStepperBar with activeStageIndex 2
    Then the third stage should have aria-current="step"

  Scenario: Calls onStageClick when a stage is clicked
    Given a StageStepperBar with stages
    When the user clicks the second stage
    Then onStageClick should be called with index 1

  Scenario: Renders horizontal on desktop
    Given a desktop viewport
    Then the stepper should display horizontally

  Scenario: Renders vertical on mobile
    Given a mobile viewport
    Then the stepper should display vertically
