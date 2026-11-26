Feature: CSV import

  Scenario: TradingView export with Unix timestamps
    Given a CSV file "NSENG_FCMB, 1D.csv" with columns "time,open,high,low,close,Volume"
    And the time column contains Unix seconds
    When I upload the file
    Then the import succeeds for ticker "FCMB"
    And the summary shows first date 2025-01-02 and last date 2025-01-06

  Scenario: Invalid prices are rejected
    Given a CSV file "x.csv" containing a close price of 0
    When I upload the file
    Then the import reports 1 invalid row
    And the row is excluded from analysis
