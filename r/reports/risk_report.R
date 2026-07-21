# R module: reports/risk_report
run_risk_report <- function(data) {
  list(module = "risk_report", rows = NROW(data), status = "configured")
}
