Feature: Seasonal window scan for a single ticker

  Background:
    Given the NairaDB dataset snapshot ending 2025-12-19 is loaded
    And default classification thresholds are in use

  Scenario: Scan returns all standard windows
    When I scan the ticker "FCMB"
    Then the report contains 37 windows
    And every window shows n, up, streak, median, worst, beat market and dip statistics

  Scenario: Known Tier 1 pattern is detected
    When I scan the ticker "FCMB"
    Then the window "Oct-Dec" is classified as "Tier 1"
    And it shows 9 up years out of 9
    And its median return is 12.1% within a tolerance of 0.1 percentage points

  Scenario: Incomplete final month is excluded
    When I scan the ticker "VITAFOAM"
    Then no window ending in December 2025 is included
    And the last complete month is "2025-11"
    And the report states that December 2025 is incomplete

  Scenario: Year-end crossing window is labelled by its start year
    When I scan the ticker "VITAFOAM"
    And I open the year detail for window "Nov-Jan"
    Then the 2019 row shows entry close 3.50 on 2019-10-31
    And exit close 5.50 on 2020-01-31
    And a return of 57.1%

  Scenario: Frozen price stock is flagged
    When I scan the ticker "CWG"
    Then the report shows the "Frozen price" warning
    And no window is classified above "None" without an "Unreliable" label

  Scenario: Short history is not classified
    When I scan the ticker "BUAFOODS"
    Then every window shows the "Insufficient history" flag
    And no window is classified as "Tier 1" or "Tier 2"

  Scenario: Consistent negative window is reported
    When I scan the ticker "ETI"
    Then the window "Feb-Mar" is classified as "Negative"
    And it shows 0 up years out of 10

  Scenario: Permutation result is reproducible
    Given the permutation seed is 7 and runs are 300
    When I scan the ticker "FCMB" twice
    Then both reports show identical permutation results

  Scenario: Unknown ticker
    When I scan the tickers "NOTREAL"
    Then I see the message "No price data found for NOTREAL"
    And no report is generated
