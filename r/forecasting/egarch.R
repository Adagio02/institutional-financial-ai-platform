# R module: forecasting/egarch
run_egarch <- function(data) {
  list(module = "egarch", rows = NROW(data), status = "configured")
}
