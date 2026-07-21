# R module: forecasting/garch
run_garch <- function(data) {
  list(module = "garch", rows = NROW(data), status = "configured")
}
