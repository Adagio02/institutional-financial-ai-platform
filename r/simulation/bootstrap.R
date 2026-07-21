# R module: simulation/bootstrap
run_bootstrap <- function(data) {
  list(module = "bootstrap", rows = NROW(data), status = "configured")
}
