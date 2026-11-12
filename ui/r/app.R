library(shiny)
library(shinydashboard)
library(jsonlite)
library(ggplot2)
library(plotly)
library(dplyr)
library(DT)
library(scales)
library(lubridate)
library(tidyr)


# ============================================================
# FINAI V4.2
# Institutional Financial AI Platform
# Interview Dashboard
# ============================================================


`%||%` <- function(x, default) {
  if (
    is.null(x) ||
      length(x) == 0
  ) {
    return(default)
  }

  if (
    length(x) == 1 &&
      is.character(x) &&
      identical(x, "")
  ) {
    return(default)
  }

  x
}


# ============================================================
# PATHS
# ============================================================


artifact_root <- Sys.getenv(
  "FINAI_ARTIFACT_ROOT",
  unset = "/app/artifacts"
)


v41_directory <- file.path(
  artifact_root,
  "v41"
)


v40_directory <- file.path(
  artifact_root,
  "v40"
)


# Research program (V5.6 / V009) and forward shadow tests.
# The V4.1 intraday loop above is kept as a legacy track.

research_root <- Sys.getenv(
  "FINAI_RESEARCH_ROOT",
  unset = "/app/research"
)

ask_finai_url <- Sys.getenv(
  "FINAI_ASK_URL",
  unset = "http://127.0.0.1:8502"
)

v009_status_path <- file.path(
  artifact_root,
  "v009-shadow-monitoring",
  "latest_status.json"
)

shadow_status_path <- file.path(
  research_root,
  "shadow",
  "status.json"
)

research_ledger_path <- file.path(
  artifact_root,
  "v56_research_attempt_ledger.csv"
)

research_versions <- c(
  "005",
  "006",
  "007",
  "008"
)


latest_learning_path <- file.path(
  v41_directory,
  "latest_learning_cycle.json"
)


v41_champion_path <- file.path(
  v41_directory,
  "champion.json"
)


v40_champion_path <- file.path(
  v40_directory,
  "champion.json"
)


shadow_path <- file.path(
  v41_directory,
  "shadow",
  "shadow_candidate.json"
)


# ============================================================
# VISUAL PALETTE
# ============================================================


COLOR_BG <- "#101318"

COLOR_GRID <- "#2a3038"

COLOR_TEXT <- "#c7cdd4"

COLOR_MUTED <- "#7f8996"

COLOR_CYAN <- "#2dd4bf"

COLOR_GREEN <- "#4ade80"

COLOR_RED <- "#f87171"

COLOR_ORANGE <- "#fb923c"

COLOR_PURPLE <- "#c084fc"

COLOR_YELLOW <- "#facc15"

COLOR_BLUE <- "#60a5fa"

COLOR_PINK <- "#f472b6"


MODEL_COLORS <- c(
  COLOR_CYAN,
  COLOR_GREEN,
  COLOR_ORANGE,
  COLOR_PURPLE,
  COLOR_BLUE,
  COLOR_PINK,
  COLOR_YELLOW,
  COLOR_RED
)


# ============================================================
# JSON HELPERS
# ============================================================


safe_read_json <- function(path) {
  if (
    is.null(path) ||
      !file.exists(path)
  ) {
    return(NULL)
  }

  tryCatch(
    jsonlite::fromJSON(
      path,
      simplifyVector = FALSE
    ),
    error = function(error) {
      message(
        paste(
          "Could not read JSON:",
          path,
          error$message
        )
      )

      NULL
    }
  )
}


latest_evaluation_path <- function() {
  if (!dir.exists(v41_directory)) {
    return(NULL)
  }

  files <- list.files(
    v41_directory,
    pattern = "^evaluation_.*\\.json$",
    full.names = TRUE
  )

  if (length(files) == 0) {
    return(NULL)
  }

  info <- file.info(
    files
  )

  files[
    which.max(
      info$mtime
    )
  ]
}


read_latest_learning <- function() {
  safe_read_json(
    latest_learning_path
  )
}


read_evaluations <- function() {
  path <- latest_evaluation_path()

  if (is.null(path)) {
    return(NULL)
  }

  raw <- safe_read_json(
    path
  )

  if (is.null(raw)) {
    return(NULL)
  }

  if (!is.null(raw$models)) {
    return(
      raw$models
    )
  }

  raw
}


read_champion <- function() {
  champion <- safe_read_json(
    v41_champion_path
  )

  if (!is.null(champion)) {
    return(champion)
  }

  safe_read_json(
    v40_champion_path
  )
}


read_shadow <- function() {
  safe_read_json(
    shadow_path
  )
}


# ============================================================
# VALUE HELPERS
# ============================================================


number_or_zero <- function(value) {
  value <- value %||% 0

  result <- suppressWarnings(
    as.numeric(value)
  )

  if (
    length(result) == 0 ||
      is.na(result[1]) ||
      is.infinite(result[1])
  ) {
    return(0)
  }

  result[1]
}


safe_character <- function(
  value,
  default = "N/A"
) {
  value <- value %||% default

  if (length(value) == 0) {
    return(default)
  }

  as.character(
    value[1]
  )
}


percent_text <- function(value) {
  scales::percent(
    number_or_zero(value),
    accuracy = 0.01
  )
}


integer_text <- function(value) {
  format(
    round(
      number_or_zero(value)
    ),
    big.mark = ",",
    scientific = FALSE
  )
}


artifact_age <- function(path) {
  if (!file.exists(path)) {
    return("Unavailable")
  }

  modified <- file.info(
    path
  )$mtime

  seconds <- as.numeric(
    difftime(
      Sys.time(),
      modified,
      units = "secs"
    )
  )

  if (seconds < 60) {
    return(
      paste0(
        round(seconds),
        " sec ago"
      )
    )
  }

  if (seconds < 3600) {
    return(
      paste0(
        round(seconds / 60),
        " min ago"
      )
    )
  }

  if (seconds < 86400) {
    return(
      paste0(
        round(
          seconds / 3600,
          1
        ),
        " hr ago"
      )
    )
  }

  paste0(
    round(
      seconds / 86400,
      1
    ),
    " days ago"
  )
}


# ============================================================
# DATA FRAME BUILDERS
# ============================================================


metric_dataframe <- function(evaluations) {
  if (
    is.null(evaluations) ||
      length(evaluations) == 0
  ) {
    return(
      data.frame()
    )
  }

  rows <- lapply(
    evaluations,
    function(model) {
      data.frame(
        model = safe_character(
          model$model_name,
          "unknown"
        ),
        balanced_accuracy = number_or_zero(
          model$balanced_accuracy
        ),
        macro_f1 = number_or_zero(
          model$macro_f1
        ),
        net_return = number_or_zero(
          model$net_return
        ),
        maximum_drawdown = number_or_zero(
          model$maximum_drawdown
        ),
        positive_fold_fraction = number_or_zero(
          model$positive_fold_fraction
        ),
        composite_score = number_or_zero(
          model$composite_score
        ),
        trade_count = number_or_zero(
          model$trade_count
        ),
        stringsAsFactors = FALSE
      )
    }
  )

  dplyr::bind_rows(
    rows
  )
}


fold_dataframe <- function(
  evaluations,
  winner
) {
  if (
    is.null(evaluations) ||
      length(evaluations) == 0
  ) {
    return(
      data.frame()
    )
  }

  selected <- NULL

  for (model in evaluations) {
    model_name <- safe_character(
      model$model_name,
      ""
    )

    if (
      identical(
        model_name,
        winner
      )
    ) {
      selected <- model
      break
    }
  }

  if (
    is.null(selected) ||
      is.null(selected$folds)
  ) {
    return(
      data.frame()
    )
  }

  rows <- lapply(
    selected$folds,
    function(fold) {
      data.frame(
        fold = number_or_zero(
          fold$fold
        ),
        net_return = number_or_zero(
          fold$net_return
        ),
        balanced_accuracy = number_or_zero(
          fold$balanced_accuracy
        ),
        macro_f1 = number_or_zero(
          fold$macro_f1
        ),
        maximum_drawdown = number_or_zero(
          fold$maximum_drawdown
        ),
        stringsAsFactors = FALSE
      )
    }
  )

  dplyr::bind_rows(
    rows
  )
}


# ============================================================
# PLOTLY HELPERS
# ============================================================


empty_plotly <- function(message) {
  plotly::plot_ly() |>
    plotly::layout(
      paper_bgcolor = COLOR_BG,
      plot_bgcolor = COLOR_BG,
      annotations = list(
        list(
          text = message,
          x = 0.5,
          y = 0.5,
          xref = "paper",
          yref = "paper",
          showarrow = FALSE,
          font = list(
            size = 15,
            color = COLOR_MUTED
          )
        )
      ),
      xaxis = list(
        visible = FALSE
      ),
      yaxis = list(
        visible = FALSE
      )
    ) |>
    plotly::config(
      displaylogo = FALSE
    )
}


plotly_dark_layout <- function(
  plot,
  x_title = "",
  y_title = ""
) {
  plot |>
    plotly::layout(
      paper_bgcolor = COLOR_BG,
      plot_bgcolor = COLOR_BG,
      font = list(
        color = COLOR_TEXT,
        family = "Arial"
      ),
      margin = list(
        l = 70,
        r = 30,
        b = 70,
        t = 25
      ),
      hoverlabel = list(
        bgcolor = "#1d2229",
        bordercolor = "#3a4654",
        font = list(
          color = "#ffffff"
        )
      ),
      xaxis = list(
        title = x_title,
        color = "#aab2bc",
        gridcolor = COLOR_GRID,
        zerolinecolor = "#555f6b",
        linecolor = "#343b44",
        tickcolor = "#343b44"
      ),
      yaxis = list(
        title = y_title,
        color = "#aab2bc",
        gridcolor = COLOR_GRID,
        zerolinecolor = "#555f6b",
        linecolor = "#343b44",
        tickcolor = "#343b44"
      ),
      legend = list(
        orientation = "h",
        x = 0,
        y = 1.12,
        font = list(
          color = COLOR_TEXT
        )
      )
    ) |>
    plotly::config(
      displaylogo = FALSE,
      responsive = TRUE
    )
}


# ============================================================
# RESEARCH PROGRAM BUILDERS
# ============================================================


optional_number <- function(value) {
  result <- suppressWarnings(
    as.numeric(value %||% NA)
  )

  if (length(result) == 0) {
    return(NA_real_)
  }

  result[1]
}


read_research_history <- function() {
  rows <- lapply(
    research_versions,
    function(version) {
      report <- safe_read_json(
        file.path(
          artifact_root,
          paste0("v56-research-", version),
          "research_report.json"
        )
      )

      if (is.null(report)) {
        return(NULL)
      }

      metrics <- report$metrics %||% list()

      rank_ic <- report$mean_rebalance_rank_ic %||%
        report$mean_oos_rank_ic %||%
        report$mean_rebalance_residual_rank_ic

      data.frame(
        version = paste0("V", version),
        net_return = optional_number(metrics$cumulative_net_return),
        sharpe = optional_number(metrics$annualized_sharpe),
        max_drawdown = optional_number(metrics$maximum_drawdown),
        rank_ic = optional_number(rank_ic),
        gates_passed = isTRUE(report$eligible_to_freeze_candidate) ||
          isTRUE(report$eligible_to_create_new_locked_candidate),
        blocking_gates = paste(
          unlist(report$blocking_reasons %||% list()),
          collapse = ", "
        ),
        stringsAsFactors = FALSE
      )
    }
  )

  rows <- Filter(
    Negate(is.null),
    rows
  )

  if (length(rows) == 0) {
    return(data.frame())
  }

  frame <- do.call(rbind, rows)

  ledger <- tryCatch(
    utils::read.csv(
      research_ledger_path,
      stringsAsFactors = FALSE
    ),
    error = function(error) NULL
  )

  if (
    !is.null(ledger) &&
      all(c("Candidate", "Decision", "Reason") %in% names(ledger))
  ) {
    key <- sub(
      "^(V[0-9]+).*$",
      "\\1",
      ledger$Candidate
    )

    frame$decision <- ledger$Decision[match(frame$version, key)]
    frame$reason <- ledger$Reason[match(frame$version, key)]
  }

  frame
}


shadow_dataframe <- function(status) {
  strategies <- status$strategies %||% list()

  if (length(strategies) == 0) {
    return(data.frame())
  }

  rows <- lapply(
    strategies,
    function(strategy) {
      open_period <- strategy$open_period %||% list()

      data.frame(
        strategy = safe_character(strategy$id, ""),
        class = safe_character(strategy$status_class, ""),
        verdict = toupper(safe_character(strategy$verdict, "")),
        progress = paste0(
          strategy$completed %||% 0,
          " / ",
          strategy$needed %||% "?"
        ),
        benchmark = safe_character(strategy$benchmark, ""),
        open_since = safe_character(open_period$since, ""),
        open_unrealized = optional_number(open_period$unrealized_gross),
        stringsAsFactors = FALSE
      )
    }
  )

  do.call(rbind, rows)
}


milestone_bar <- function(
  label,
  done,
  target
) {
  percent <- max(
    0,
    min(100, round(100 * done / target))
  )

  div(
    class = "milestone",
    div(
      class = "milestone-head",
      span(label),
      span(
        class = "milestone-count",
        paste0(done, " / ", target, " periods")
      )
    ),
    div(
      class = "milestone-track",
      div(
        class = if (done >= target) {
          "milestone-fill milestone-done"
        } else {
          "milestone-fill"
        },
        style = paste0("width: ", percent, "%;")
      )
    )
  )
}


flag_row <- function(
  label,
  value
) {
  div(
    class = "flag-row",
    span(label),
    span(
      class = if (isTRUE(value)) "flag-yes" else "flag-no",
      if (isTRUE(value)) "Yes" else "No"
    )
  )
}


# ============================================================
# UI HELPERS
# ============================================================


metric_card <- function(
  output_id,
  title,
  icon_name
) {
  div(
    class = "metric-card",
    div(
      class = "metric-card-top",
      div(
        class = "metric-icon",
        icon(
          icon_name
        )
      ),
      div(
        class = "metric-title",
        title
      )
    ),
    div(
      class = "metric-value",
      textOutput(
        output_id,
        inline = TRUE
      )
    )
  )
}


section_header <- function(
  title,
  subtitle = NULL
) {
  div(
    class = "section-header",
    h2(
      title
    ),
    if (!is.null(subtitle)) {
      p(
        subtitle
      )
    }
  )
}


chart_panel <- function(
  title,
  subtitle,
  output_id,
  height = "360px"
) {
  div(
    class = "dashboard-panel chart-panel",
    div(
      class = "panel-header",
      h3(
        title
      ),
      span(
        subtitle
      )
    ),
    plotlyOutput(
      output_id,
      height = height
    )
  )
}


# ============================================================
# USER INTERFACE
# ============================================================


ui <- dashboardPage(
  skin = "black",
  dashboardHeader(
    title = span(
      class = "brand-title",
      "FINAI",
      span(
        class = "brand-version",
        "V4.2"
      )
    )
  ),
  dashboardSidebar(
    width = 245,
    div(
      class = "sidebar-platform-label",
      "INSTITUTIONAL RESEARCH"
    ),
    sidebarMenu(
      id = "tabs",
      menuItem(
        "Research Program",
        tabName = "program",
        icon = icon("flask"),
        selected = TRUE
      ),
      menuItem(
        "Ask FinAI",
        href = ask_finai_url,
        newtab = TRUE,
        icon = icon("comments")
      ),
      menuItem(
        "Legacy Intraday (V4.1)",
        tabName = "executive",
        icon = icon("archive")
      ),
      menuItem(
        "Model Lab",
        tabName = "models",
        icon = icon("bar-chart")
      ),
      menuItem(
        "Validation",
        tabName = "validation",
        icon = icon("check-circle")
      ),
      menuItem(
        "Research",
        tabName = "research",
        icon = icon("flask")
      ),
      menuItem(
        "Architecture",
        tabName = "architecture",
        icon = icon("sitemap")
      )
    ),
    div(
      class = "sidebar-footer",
      div(
        class = "status-dot"
      ),
      span(
        "PAPER / SHADOW ONLY"
      )
    )
  ),
  dashboardBody(
    tags$head(
      tags$meta(
        name = "viewport",
        content = "width=device-width, initial-scale=1"
      ),
      tags$link(
        rel = "stylesheet",
        type = "text/css",
        href = "custom.css"
      )
    ),
    div(
      class = "top-status-strip",
      div(
        span(
          class = "status-label",
          "V009"
        ),
        span(
          class = "status-value",
          textOutput(
            "top_v009",
            inline = TRUE
          )
        )
      ),
      div(
        span(
          class = "status-label",
          "SYSTEM"
        ),
        span(
          class = "status-value",
          textOutput(
            "top_system_status",
            inline = TRUE
          )
        )
      ),
      div(
        span(
          class = "status-label",
          "LEGACY SYMBOL"
        ),
        span(
          class = "status-value",
          textOutput(
            "top_symbol",
            inline = TRUE
          )
        )
      ),
      div(
        span(
          class = "status-label",
          "LEGACY INTERVAL"
        ),
        span(
          class = "status-value",
          textOutput(
            "top_interval",
            inline = TRUE
          )
        )
      ),
      div(
        span(
          class = "status-label",
          "LEGACY ARTIFACT"
        ),
        span(
          class = "status-value",
          textOutput(
            "artifact_freshness",
            inline = TRUE
          )
        )
      )
    ),
    tabItems(
      # ======================================================
      # RESEARCH PROGRAM (V5.6 / V009)
      # ======================================================
      tabItem(
        tabName = "program",
        section_header(
          "Research program",
          paste(
            "Daily cross-sectional research (V5.6 / V009) and forward",
            "shadow tests. V009 is performance-blind until its lock."
          )
        ),
        fluidRow(
          column(
            width = 3,
            metric_card(
              "v009_designation",
              "V009 forward test",
              "hourglass-half"
            )
          ),
          column(
            width = 3,
            metric_card(
              "v009_periods",
              "Periods to next milestone",
              "calendar"
            )
          ),
          column(
            width = 3,
            metric_card(
              "shadow_health",
              "Shadow strategies",
              "eye"
            )
          ),
          column(
            width = 3,
            metric_card(
              "research_freshness",
              "V009 data refreshed",
              "database"
            )
          )
        ),
        fluidRow(
          column(
            width = 5,
            div(
              class = "dashboard-panel",
              div(
                class = "panel-header",
                h3("V009 milestones"),
                span("Toward the 52-period one-shot lock")
              ),
              uiOutput("v009_milestones")
            )
          ),
          column(
            width = 7,
            div(
              class = "dashboard-panel",
              div(
                class = "panel-header",
                h3("Forward shadow tests"),
                span("Paper tracking; verdicts only at the final period")
              ),
              DTOutput("shadow_table")
            )
          )
        ),
        fluidRow(
          column(
            width = 12,
            div(
              class = "dashboard-panel",
              div(
                class = "panel-header",
                h3("Development research history"),
                span("V5.6 candidates on the already-observed development window")
              ),
              DTOutput("research_history_table")
            )
          )
        ),
        div(
          class = "paper-only-banner",
          icon("info-circle"),
          span(
            paste(
              "Gates are fixed in advance and are never lowered to force a promotion.",
              "The V4.1 1-minute AAPL loop is shown under Legacy Intraday for reference."
            )
          )
        )
      ),


      # ======================================================
      # LEGACY INTRADAY (V4.1) - formerly Executive
      # ======================================================
      tabItem(
        tabName = "executive",
        section_header(
          "Legacy intraday track (V4.1)",
          paste(
            "AAPL 1-minute learning loop, kept for reference.",
            "This is not the primary research program."
          )
        ),
        div(
          class = "legacy-banner",
          icon("archive"),
          span(
            paste(
              "LEGACY: predicts 5 one-minute bars ahead on a single stock.",
              "Its candidates are expected to fail the gates; the primary",
              "program is under Research Program."
            )
          )
        ),
        fluidRow(
          column(
            width = 3,
            metric_card(
              "system_status",
              "System",
              "server"
            )
          ),
          column(
            width = 3,
            metric_card(
              "champion_status",
              "Champion",
              "trophy"
            )
          ),
          column(
            width = 3,
            metric_card(
              "candidate_name",
              "Latest candidate",
              "bar-chart"
            )
          ),
          column(
            width = 3,
            metric_card(
              "holdout_return",
              "Holdout return",
              "line-chart"
            )
          )
        ),
        fluidRow(
          column(
            width = 8,
            chart_panel(
              "Model ranking",
              "Composite research score",
              "composite_plot",
              "380px"
            )
          ),
          column(
            width = 4,
            div(
              class = "dashboard-panel governance-panel",
              div(
                class = "panel-header",
                h3(
                  "Governance pipeline"
                ),
                span(
                  "Promotion state"
                )
              ),
              uiOutput(
                "governance_pipeline"
              )
            )
          )
        ),
        fluidRow(
          column(
            width = 6,
            chart_panel(
              "Economic performance",
              "Net return after modeled costs",
              "return_plot",
              "350px"
            )
          ),
          column(
            width = 6,
            chart_panel(
              "Risk / return map",
              "Return relative to maximum drawdown",
              "risk_return_plot",
              "350px"
            )
          )
        ),
        fluidRow(
          column(
            width = 12,
            div(
              class = "dashboard-panel",
              div(
                class = "panel-header",
                h3(
                  "Latest learning cycle"
                ),
                span(
                  "Current V4.1 research artifact"
                )
              ),
              DTOutput(
                "latest_table"
              )
            )
          )
        )
      ),


      # ======================================================
      # MODEL LAB
      # ======================================================

      tabItem(
        tabName = "models",
        section_header(
          "Model laboratory",
          paste(
            "Compare predictive quality,",
            "economic performance and stability."
          )
        ),
        fluidRow(
          column(
            width = 6,
            chart_panel(
              "Classification quality",
              "Balanced accuracy versus macro F1",
              "classification_plot",
              "390px"
            )
          ),
          column(
            width = 6,
            chart_panel(
              "Fold consistency",
              "Fraction of profitable walk-forward folds",
              "consistency_plot",
              "390px"
            )
          )
        ),
        fluidRow(
          column(
            width = 6,
            chart_panel(
              "Economic performance",
              "Net strategy return by model",
              "model_return_plot",
              "360px"
            )
          ),
          column(
            width = 6,
            chart_panel(
              "Drawdown comparison",
              "Maximum drawdown by model",
              "drawdown_plot",
              "360px"
            )
          )
        ),
        fluidRow(
          column(
            width = 12,
            div(
              class = "dashboard-panel",
              div(
                class = "panel-header",
                h3(
                  "Model leaderboard"
                ),
                span(
                  paste(
                    "Sortable research metrics across",
                    "all evaluated candidates"
                  )
                )
              ),
              DTOutput(
                "model_table"
              )
            )
          )
        )
      ),


      # ======================================================
      # VALIDATION
      # ======================================================

      tabItem(
        tabName = "validation",
        section_header(
          "Validation & governance",
          paste(
            "Walk-forward testing, historical qualification",
            "and prospective shadow validation."
          )
        ),
        fluidRow(
          column(
            width = 4,
            metric_card(
              "historical_status",
              "Historical qualification",
              "check-circle"
            )
          ),
          column(
            width = 4,
            metric_card(
              "shadow_status",
              "Shadow validation",
              "eye"
            )
          ),
          column(
            width = 4,
            metric_card(
              "execution_status",
              "Execution",
              "lock"
            )
          )
        ),
        fluidRow(
          column(
            width = 6,
            chart_panel(
              "Walk-forward returns",
              "Green = profitable fold · Red = losing fold",
              "fold_return_plot",
              "370px"
            )
          ),
          column(
            width = 6,
            chart_panel(
              "Walk-forward accuracy",
              "Balanced accuracy across folds",
              "fold_accuracy_plot",
              "370px"
            )
          )
        ),
        fluidRow(
          column(
            width = 6,
            chart_panel(
              "Fold drawdown",
              "Maximum drawdown across validation windows",
              "fold_drawdown_plot",
              "350px"
            )
          ),
          column(
            width = 6,
            chart_panel(
              "Accuracy vs return",
              "Validation relationship by fold",
              "fold_scatter_plot",
              "350px"
            )
          )
        ),
        fluidRow(
          column(
            width = 12,
            div(
              class = "dashboard-panel",
              div(
                class = "panel-header",
                h3(
                  "Governance decision"
                ),
                span(
                  "Current model-promotion state"
                )
              ),
              uiOutput(
                "governance_detail"
              )
            )
          )
        )
      ),


      # ======================================================
      # RESEARCH
      # ======================================================

      tabItem(
        tabName = "research",
        section_header(
          "Research diagnostics",
          paste(
            "Detailed quantitative evaluation",
            "for model review and interviews."
          )
        ),
        fluidRow(
          column(
            width = 12,
            div(
              class = "dashboard-panel",
              div(
                class = "panel-header",
                h3(
                  "Research matrix"
                ),
                span(
                  "Searchable evaluation dataset"
                )
              ),
              DTOutput(
                "research_table"
              )
            )
          )
        ),
        fluidRow(
          column(
            width = 12,
            div(
              class = "dashboard-panel",
              div(
                class = "panel-header",
                h3(
                  "Research methodology"
                ),
                span(
                  "End-to-end model-development process"
                )
              ),
              div(
                class = "methodology-grid",
                div(
                  class = "method-card",
                  h4(
                    "01 · DATA"
                  ),
                  p(
                    paste(
                      "AAPL target market with SPY and QQQ",
                      "cross-market context."
                    )
                  )
                ),
                div(
                  class = "method-card",
                  h4(
                    "02 · FEATURES"
                  ),
                  p(
                    paste(
                      "Momentum, volatility, regime,",
                      "relative-market and cost-aware signals."
                    )
                  )
                ),
                div(
                  class = "method-card",
                  h4(
                    "03 · VALIDATION"
                  ),
                  p(
                    paste(
                      "Purged walk-forward testing followed",
                      "by untouched holdout evaluation."
                    )
                  )
                ),
                div(
                  class = "method-card",
                  h4(
                    "04 · GOVERNANCE"
                  ),
                  p(
                    paste(
                      "Historical qualification precedes",
                      "prospective shadow validation."
                    )
                  )
                )
              )
            )
          )
        )
      ),


      # ======================================================
      # ARCHITECTURE
      # ======================================================

      tabItem(
        tabName = "architecture",
        section_header(
          "Platform architecture",
          paste(
            "Market-data ingestion through",
            "governed paper execution."
          )
        ),
        fluidRow(
          column(
            width = 12,
            div(
              class = "dashboard-panel",
              div(
                class = "architecture-flow",
                div(
                  class = "architecture-node node-cyan",
                  h4(
                    "Market data"
                  ),
                  p(
                    "AAPL · SPY · QQQ"
                  )
                ),
                div(
                  class = "architecture-arrow",
                  "→"
                ),
                div(
                  class = "architecture-node node-blue",
                  h4(
                    "PostgreSQL"
                  ),
                  p(
                    "Historical + operational state"
                  )
                ),
                div(
                  class = "architecture-arrow",
                  "→"
                ),
                div(
                  class = "architecture-node node-orange",
                  h4(
                    "Feature engine"
                  ),
                  p(
                    "V4.1 multi-market features"
                  )
                ),
                div(
                  class = "architecture-arrow",
                  "→"
                ),
                div(
                  class = "architecture-node node-purple",
                  h4(
                    "Model laboratory"
                  ),
                  p(
                    "Regime-aware candidates"
                  )
                )
              ),
              div(
                class = "architecture-flow second-row",
                div(
                  class = "architecture-node node-yellow",
                  h4(
                    "Walk-forward"
                  ),
                  p(
                    "Purged historical validation"
                  )
                ),
                div(
                  class = "architecture-arrow",
                  "→"
                ),
                div(
                  class = "architecture-node node-pink",
                  h4(
                    "Holdout"
                  ),
                  p(
                    "Untouched final evaluation"
                  )
                ),
                div(
                  class = "architecture-arrow",
                  "→"
                ),
                div(
                  class = "architecture-node node-green",
                  h4(
                    "Shadow"
                  ),
                  p(
                    "Prospective validation"
                  )
                ),
                div(
                  class = "architecture-arrow",
                  "→"
                ),
                div(
                  class = "architecture-node node-red",
                  h4(
                    "Paper execution"
                  ),
                  p(
                    "Champion-gated execution"
                  )
                )
              )
            )
          )
        ),
        fluidRow(
          column(
            width = 12,
            div(
              class = "dashboard-panel",
              div(
                class = "safety-banner",
                icon(
                  "shield"
                ),
                div(
                  h3(
                    "Model governance is enforced"
                  ),
                  p(
                    paste(
                      "A candidate is not promoted merely",
                      "because it ranks first.",
                      "Historical qualification and",
                      "prospective validation remain active."
                    )
                  )
                )
              )
            )
          )
        )
      )
    )
  )
)


# ============================================================
# SERVER
# ============================================================


server <- function(
  input,
  output,
  session
) {
  # Refresh artifact state every five seconds.

  refresh <- reactiveTimer(
    5000
  )


  latest <- reactive({
    refresh()

    read_latest_learning()
  })


  evaluations <- reactive({
    refresh()

    read_evaluations()
  })


  champion <- reactive({
    refresh()

    read_champion()
  })


  shadow <- reactive({
    refresh()

    read_shadow()
  })


  metrics <- reactive({
    metric_dataframe(
      evaluations()
    )
  })


  folds <- reactive({
    current <- latest()

    if (is.null(current)) {
      return(
        data.frame()
      )
    }

    winner <- safe_character(
      current$winning_model,
      ""
    )

    fold_dataframe(
      evaluations(),
      winner
    )
  })


  # ==========================================================
  # RESEARCH PROGRAM
  # ==========================================================


  v009 <- reactive({
    refresh()

    safe_read_json(v009_status_path)
  })


  shadow_research <- reactive({
    refresh()

    safe_read_json(shadow_status_path)
  })


  research_history <- reactive({
    refresh()

    read_research_history()
  })


  output$top_v009 <- renderText({
    status <- v009()

    if (is.null(status)) {
      return("NO DATA")
    }

    paste0(
      toupper(safe_character(status$designation, "unknown")),
      " ",
      status$completed_non_overlapping_periods %||% 0,
      "/",
      status$next_milestone_periods %||% 13
    )
  })


  output$v009_designation <- renderText({
    status <- v009()

    if (is.null(status)) {
      return("NO DATA")
    }

    toupper(safe_character(status$designation, "unknown"))
  })


  output$v009_periods <- renderText({
    status <- v009()

    if (is.null(status)) {
      return("N/A")
    }

    paste0(
      status$completed_non_overlapping_periods %||% 0,
      " / ",
      status$next_milestone_periods %||% 13
    )
  })


  output$shadow_health <- renderText({
    status <- shadow_research()

    if (is.null(status)) {
      return("NO DATA")
    }

    if (isTRUE(status$healthy)) "HEALTHY" else "CHECK"
  })


  output$research_freshness <- renderText({
    artifact_age(v009_status_path)
  })


  output$v009_milestones <- renderUI({
    status <- v009()

    if (is.null(status)) {
      return(
        p(
          class = "empty-note",
          "No V009 monitoring status found yet."
        )
      )
    }

    done <- number_or_zero(status$completed_non_overlapping_periods)

    tagList(
      milestone_bar("Provisional milestone", done, 13),
      milestone_bar("Second milestone", done, 26),
      milestone_bar("Official lock readiness", done, 52),
      div(
        class = "milestone-facts",
        div(
          span("Qualified market dates"),
          span(integer_text(status$qualified_market_dates))
        ),
        div(
          span("Symbols observed"),
          span(
            paste0(
              integer_text(status$minimum_observed_symbols),
              " - ",
              integer_text(status$maximum_observed_symbols),
              " (min ",
              integer_text(status$minimum_symbols_required),
              ")"
            )
          )
        ),
        div(
          span("Last qualified date"),
          span(substr(safe_character(status$last_qualified_date, "N/A"), 1, 10))
        )
      ),
      div(
        class = "flag-list",
        flag_row("Performance-blind", status$performance_blind),
        flag_row("Lock ready", status$official_lock_ready),
        flag_row("Lock executed", status$official_lock_executed),
        flag_row("V5.7 unlocked", status$v57_unlocked),
        flag_row("Champion eligible", status$champion_eligible),
        flag_row("Live trading allowed", status$live_trading_allowed)
      )
    )
  })


  output$shadow_table <- renderDT({
    frame <- shadow_dataframe(shadow_research())

    if (nrow(frame) == 0) {
      frame <- data.frame(
        status = "No shadow strategy status found."
      )
    }

    table <- DT::datatable(
      frame,
      rownames = FALSE,
      options = list(
        pageLength = 10,
        dom = "t",
        scrollX = TRUE
      ),
      class = "stripe hover compact"
    )

    if ("open_unrealized" %in% names(frame)) {
      table <- DT::formatPercentage(
        table,
        columns = "open_unrealized",
        digits = 2
      )
    }

    table
  })


  output$research_history_table <- renderDT({
    frame <- research_history()

    if (nrow(frame) == 0) {
      frame <- data.frame(
        status = "No V5.6 research reports found."
      )
    }

    table <- DT::datatable(
      frame,
      rownames = FALSE,
      options = list(
        pageLength = 10,
        dom = "t",
        scrollX = TRUE
      ),
      class = "stripe hover compact"
    )

    percent_columns <- intersect(
      c("net_return", "max_drawdown"),
      names(frame)
    )

    if (length(percent_columns) > 0) {
      table <- DT::formatPercentage(
        table,
        columns = percent_columns,
        digits = 2
      )
    }

    round_columns <- intersect(
      c("sharpe", "rank_ic"),
      names(frame)
    )

    if (length(round_columns) > 0) {
      table <- DT::formatRound(
        table,
        columns = round_columns,
        digits = 3
      )
    }

    table
  })


  # ==========================================================
  # STATUS STRIP
  # ==========================================================


  output$top_system_status <- renderText({
    if (is.null(latest())) {
      "WAITING"
    } else {
      "ONLINE"
    }
  })


  output$top_symbol <- renderText({
    current <- latest()

    if (is.null(current)) {
      return("N/A")
    }

    safe_character(
      current$symbol,
      "N/A"
    )
  })


  output$top_interval <- renderText({
    current <- latest()

    if (is.null(current)) {
      return("N/A")
    }

    safe_character(
      current$interval,
      "N/A"
    )
  })


  output$artifact_freshness <- renderText({
    artifact_age(
      latest_learning_path
    )
  })


  # ==========================================================
  # KPI CARDS
  # ==========================================================


  output$system_status <- renderText({
    if (is.null(latest())) {
      "WAITING"
    } else {
      "ONLINE"
    }
  })


  output$champion_status <- renderText({
    if (is.null(champion())) {
      "NONE"
    } else {
      "QUALIFIED"
    }
  })


  output$candidate_name <- renderText({
    current <- latest()

    if (is.null(current)) {
      return("NONE")
    }

    safe_character(
      current$winning_model,
      "UNKNOWN"
    )
  })


  output$holdout_return <- renderText({
    current <- latest()

    if (is.null(current)) {
      return("N/A")
    }

    percent_text(
      current$holdout_net_return %||% 0
    )
  })


  output$historical_status <- renderText({
    current <- latest()

    qualified <- (
      !is.null(current) &&
        isTRUE(
          current$historical_qualified
        )
    )

    if (qualified) {
      "PASSED"
    } else {
      "NOT PASSED"
    }
  })


  output$shadow_status <- renderText({
    current_shadow <- shadow()

    if (is.null(current_shadow)) {
      return(
        "NO CANDIDATE"
      )
    }

    toupper(
      safe_character(
        current_shadow$shadow_status,
        "OBSERVING"
      )
    )
  })


  output$execution_status <- renderText({
    if (is.null(champion())) {
      "BLOCKED"
    } else {
      "PAPER READY"
    }
  })


  # ==========================================================
  # GOVERNANCE PIPELINE
  # ==========================================================


  output$governance_pipeline <- renderUI({
    current <- latest()

    current_shadow <- shadow()

    champ <- champion()


    historical_pass <- (
      !is.null(current) &&
        isTRUE(
          current$historical_qualified
        )
    )


    shadow_exists <- !is.null(
      current_shadow
    )


    champion_exists <- !is.null(
      champ
    )


    tagList(
      div(
        class = "pipeline-stage pipeline-active",
        span(
          class = "pipeline-number",
          "01"
        ),
        div(
          h4(
            "Candidate research"
          ),
          p(
            "Walk-forward evaluation"
          )
        )
      ),
      div(
        class = if (historical_pass) {
          "pipeline-stage pipeline-pass"
        } else {
          "pipeline-stage pipeline-blocked"
        },
        span(
          class = "pipeline-number",
          "02"
        ),
        div(
          h4(
            "Historical gate"
          ),
          p(
            if (historical_pass) {
              "Qualification passed"
            } else {
              "Qualification not passed"
            }
          )
        )
      ),
      div(
        class = if (shadow_exists) {
          "pipeline-stage pipeline-active"
        } else {
          "pipeline-stage pipeline-muted"
        },
        span(
          class = "pipeline-number",
          "03"
        ),
        div(
          h4(
            "Shadow validation"
          ),
          p(
            if (shadow_exists) {
              "Prospective monitoring"
            } else {
              "Awaiting qualified candidate"
            }
          )
        )
      ),
      div(
        class = if (champion_exists) {
          "pipeline-stage pipeline-pass"
        } else {
          "pipeline-stage pipeline-muted"
        },
        span(
          class = "pipeline-number",
          "04"
        ),
        div(
          h4(
            "Champion"
          ),
          p(
            if (champion_exists) {
              "Governed model available"
            } else {
              "No promotion"
            }
          )
        )
      )
    )
  })


  # ==========================================================
  # MODEL RANKING
  # ==========================================================


  output$composite_plot <- renderPlotly({
    frame <- metrics()

    if (nrow(frame) == 0) {
      return(
        empty_plotly(
          "No model evaluation available."
        )
      )
    }


    frame <- frame |>
      arrange(
        composite_score
      )


    colors <- rep(
      MODEL_COLORS,
      length.out = nrow(frame)
    )


    plot <- plotly::plot_ly(
      data = frame,
      x = ~composite_score,
      y = ~ reorder(
        model,
        composite_score
      ),
      type = "bar",
      orientation = "h",
      marker = list(
        color = colors,
        opacity = 0.88,
        line = list(
          color = "#d1d5db",
          width = 0.4
        )
      ),
      text = ~ paste0(
        "<b>",
        model,
        "</b><br>",
        "Composite score: ",
        round(
          composite_score,
          4
        ),
        "<br>",
        "Net return: ",
        percent(
          net_return,
          accuracy = 0.01
        ),
        "<br>",
        "Balanced accuracy: ",
        percent(
          balanced_accuracy,
          accuracy = 0.01
        )
      ),
      hoverinfo = "text"
    )


    plotly_dark_layout(
      plot,
      x_title = "Composite score",
      y_title = ""
    )
  })


  # ==========================================================
  # EXECUTIVE RETURN
  # ==========================================================


  output$return_plot <- renderPlotly({
    frame <- metrics()

    if (nrow(frame) == 0) {
      return(
        empty_plotly(
          "No return metrics available."
        )
      )
    }


    frame <- frame |>
      arrange(
        net_return
      )


    colors <- ifelse(
      frame$net_return >= 0,
      COLOR_GREEN,
      COLOR_RED
    )


    plot <- plotly::plot_ly(
      data = frame,
      x = ~net_return,
      y = ~ reorder(
        model,
        net_return
      ),
      type = "bar",
      orientation = "h",
      marker = list(
        color = colors,
        opacity = 0.9
      ),
      text = ~ paste0(
        "<b>",
        model,
        "</b><br>",
        "Net return: ",
        percent(
          net_return,
          accuracy = 0.01
        ),
        "<br>",
        "Maximum drawdown: ",
        percent(
          maximum_drawdown,
          accuracy = 0.01
        ),
        "<br>",
        "Trades: ",
        round(
          trade_count
        )
      ),
      hoverinfo = "text"
    )


    plot <- plotly_dark_layout(
      plot,
      x_title = "Net return",
      y_title = ""
    )


    plot |>
      plotly::layout(
        xaxis = list(
          title = "Net return",
          tickformat = ".1%",
          gridcolor = COLOR_GRID,
          zeroline = TRUE,
          zerolinecolor = "#8b949e",
          zerolinewidth = 1.5
        )
      )
  })


  # ==========================================================
  # RISK / RETURN
  # ==========================================================


  output$risk_return_plot <- renderPlotly({
    frame <- metrics()

    if (nrow(frame) == 0) {
      return(
        empty_plotly(
          "No risk / return metrics available."
        )
      )
    }


    colors <- rep(
      MODEL_COLORS,
      length.out = nrow(frame)
    )


    plot <- plotly::plot_ly(
      data = frame,
      x = ~maximum_drawdown,
      y = ~net_return,
      type = "scatter",
      mode = "markers+text",
      text = ~model,
      textposition = "top center",
      textfont = list(
        color = "#d6d9de",
        size = 10
      ),
      marker = list(
        size = 15,
        color = colors,
        opacity = 0.92,
        line = list(
          color = "#f3f4f6",
          width = 0.7
        )
      ),
      hovertext = ~ paste0(
        "<b>",
        model,
        "</b><br>",
        "Net return: ",
        percent(
          net_return,
          accuracy = 0.01
        ),
        "<br>",
        "Maximum drawdown: ",
        percent(
          maximum_drawdown,
          accuracy = 0.01
        ),
        "<br>",
        "Composite score: ",
        round(
          composite_score,
          4
        )
      ),
      hoverinfo = "text"
    )


    plot <- plotly_dark_layout(
      plot,
      x_title = "Maximum drawdown",
      y_title = "Net return"
    )


    plot |>
      plotly::layout(
        xaxis = list(
          title = "Maximum drawdown",
          tickformat = ".1%",
          gridcolor = COLOR_GRID
        ),
        yaxis = list(
          title = "Net return",
          tickformat = ".1%",
          gridcolor = COLOR_GRID,
          zeroline = TRUE,
          zerolinecolor = "#8b949e"
        )
      )
  })


  # ==========================================================
  # CLASSIFICATION
  # ==========================================================


  output$classification_plot <- renderPlotly({
    frame <- metrics()

    if (nrow(frame) == 0) {
      return(
        empty_plotly(
          "No classification metrics available."
        )
      )
    }


    plot <- plotly::plot_ly(
      data = frame,
      x = ~model,
      y = ~balanced_accuracy,
      type = "bar",
      name = "Balanced accuracy",
      marker = list(
        color = COLOR_PURPLE,
        opacity = 0.9
      ),
      text = ~ percent(
        balanced_accuracy,
        accuracy = 0.01
      ),
      hovertemplate = paste(
        "<b>%{x}</b><br>",
        "Balanced accuracy: %{text}",
        "<extra></extra>"
      )
    )


    plot <- plot |>
      plotly::add_trace(
        y = ~macro_f1,
        name = "Macro F1",
        marker = list(
          color = COLOR_ORANGE,
          opacity = 0.9
        ),
        text = ~ percent(
          macro_f1,
          accuracy = 0.01
        ),
        hovertemplate = paste(
          "<b>%{x}</b><br>",
          "Macro F1: %{text}",
          "<extra></extra>"
        )
      )


    plot <- plotly_dark_layout(
      plot,
      x_title = "",
      y_title = "Classification score"
    )


    plot |>
      plotly::layout(
        barmode = "group",
        yaxis = list(
          title = "Classification score",
          tickformat = ".0%",
          gridcolor = COLOR_GRID,
          rangemode = "tozero"
        )
      )
  })


  # ==========================================================
  # FOLD CONSISTENCY
  # ==========================================================


  output$consistency_plot <- renderPlotly({
    frame <- metrics()

    if (nrow(frame) == 0) {
      return(
        empty_plotly(
          "No fold consistency metrics available."
        )
      )
    }


    frame <- frame |>
      arrange(
        positive_fold_fraction
      )


    plot <- plotly::plot_ly(
      data = frame,
      x = ~positive_fold_fraction,
      y = ~ reorder(
        model,
        positive_fold_fraction
      ),
      type = "bar",
      orientation = "h",
      marker = list(
        color = COLOR_YELLOW,
        opacity = 0.88,
        line = list(
          color = "#fde68a",
          width = 0.6
        )
      ),
      text = ~ percent(
        positive_fold_fraction,
        accuracy = 1
      ),
      hovertemplate = paste(
        "<b>%{y}</b><br>",
        "Positive folds: %{text}",
        "<extra></extra>"
      )
    )


    plot <- plotly_dark_layout(
      plot,
      x_title = "Positive fold fraction",
      y_title = ""
    )


    plot |>
      plotly::layout(
        xaxis = list(
          title = "Positive fold fraction",
          tickformat = ".0%",
          range = c(
            0,
            1
          ),
          gridcolor = COLOR_GRID
        )
      )
  })


  # ==========================================================
  # MODEL RETURN
  # ==========================================================


  output$model_return_plot <- renderPlotly({
    frame <- metrics()

    if (nrow(frame) == 0) {
      return(
        empty_plotly(
          "No economic metrics available."
        )
      )
    }


    frame <- frame |>
      arrange(
        net_return
      )


    colors <- ifelse(
      frame$net_return >= 0,
      COLOR_GREEN,
      COLOR_RED
    )


    plot <- plotly::plot_ly(
      data = frame,
      x = ~net_return,
      y = ~ reorder(
        model,
        net_return
      ),
      type = "bar",
      orientation = "h",
      marker = list(
        color = colors,
        opacity = 0.9
      ),
      text = ~ percent(
        net_return,
        accuracy = 0.01
      ),
      hovertemplate = paste(
        "<b>%{y}</b><br>",
        "Net return: %{text}",
        "<extra></extra>"
      )
    )


    plot <- plotly_dark_layout(
      plot,
      x_title = "Net return",
      y_title = ""
    )


    plot |>
      plotly::layout(
        xaxis = list(
          title = "Net return",
          tickformat = ".1%",
          gridcolor = COLOR_GRID,
          zeroline = TRUE,
          zerolinecolor = "#8b949e"
        )
      )
  })


  # ==========================================================
  # DRAWDOWN
  # ==========================================================


  output$drawdown_plot <- renderPlotly({
    frame <- metrics()

    if (nrow(frame) == 0) {
      return(
        empty_plotly(
          "No drawdown metrics available."
        )
      )
    }


    frame <- frame |>
      arrange(
        maximum_drawdown
      )


    plot <- plotly::plot_ly(
      data = frame,
      x = ~maximum_drawdown,
      y = ~ reorder(
        model,
        maximum_drawdown
      ),
      type = "bar",
      orientation = "h",
      marker = list(
        color = COLOR_ORANGE,
        opacity = 0.9
      ),
      text = ~ percent(
        maximum_drawdown,
        accuracy = 0.01
      ),
      hovertemplate = paste(
        "<b>%{y}</b><br>",
        "Maximum drawdown: %{text}",
        "<extra></extra>"
      )
    )


    plot <- plotly_dark_layout(
      plot,
      x_title = "Maximum drawdown",
      y_title = ""
    )


    plot |>
      plotly::layout(
        xaxis = list(
          title = "Maximum drawdown",
          tickformat = ".1%",
          gridcolor = COLOR_GRID
        )
      )
  })


  # ==========================================================
  # WALK-FORWARD RETURNS
  # ==========================================================


  output$fold_return_plot <- renderPlotly({
    frame <- folds()

    if (nrow(frame) == 0) {
      return(
        empty_plotly(
          "No winning-model fold data available."
        )
      )
    }


    frame$bar_color <- ifelse(
      frame$net_return >= 0,
      COLOR_GREEN,
      COLOR_RED
    )


    plot <- plotly::plot_ly(
      data = frame,
      x = ~ factor(
        fold
      ),
      y = ~net_return,
      type = "bar",
      marker = list(
        color = frame$bar_color,
        opacity = 0.9
      ),
      text = ~ percent(
        net_return,
        accuracy = 0.01
      ),
      hovertemplate = paste(
        "Fold %{x}<br>",
        "Net return: %{text}",
        "<extra></extra>"
      )
    )


    plot <- plotly_dark_layout(
      plot,
      x_title = "Walk-forward fold",
      y_title = "Net return"
    )


    plot |>
      plotly::layout(
        yaxis = list(
          title = "Net return",
          tickformat = ".1%",
          gridcolor = COLOR_GRID,
          zeroline = TRUE,
          zerolinecolor = "#8b949e",
          zerolinewidth = 1.5
        )
      )
  })


  # ==========================================================
  # WALK-FORWARD ACCURACY
  # ==========================================================


  output$fold_accuracy_plot <- renderPlotly({
    frame <- folds()

    if (nrow(frame) == 0) {
      return(
        empty_plotly(
          "No fold accuracy data available."
        )
      )
    }


    plot <- plotly::plot_ly(
      data = frame,
      x = ~fold,
      y = ~balanced_accuracy,
      type = "scatter",
      mode = "lines+markers",
      marker = list(
        size = 9,
        color = COLOR_CYAN,
        line = list(
          color = "#99f6e4",
          width = 1
        )
      ),
      line = list(
        width = 3,
        color = COLOR_CYAN
      ),
      text = ~ percent(
        balanced_accuracy,
        accuracy = 0.01
      ),
      hovertemplate = paste(
        "Fold %{x}<br>",
        "Balanced accuracy: %{text}",
        "<extra></extra>"
      )
    )


    plot <- plotly_dark_layout(
      plot,
      x_title = "Walk-forward fold",
      y_title = "Balanced accuracy"
    )


    plot |>
      plotly::layout(
        yaxis = list(
          title = "Balanced accuracy",
          tickformat = ".0%",
          gridcolor = COLOR_GRID
        )
      )
  })


  # ==========================================================
  # FOLD DRAWDOWN
  # ==========================================================


  output$fold_drawdown_plot <- renderPlotly({
    frame <- folds()

    if (nrow(frame) == 0) {
      return(
        empty_plotly(
          "No fold drawdown data available."
        )
      )
    }


    plot <- plotly::plot_ly(
      data = frame,
      x = ~ factor(
        fold
      ),
      y = ~maximum_drawdown,
      type = "bar",
      marker = list(
        color = COLOR_ORANGE,
        opacity = 0.88
      ),
      text = ~ percent(
        maximum_drawdown,
        accuracy = 0.01
      ),
      hovertemplate = paste(
        "Fold %{x}<br>",
        "Maximum drawdown: %{text}",
        "<extra></extra>"
      )
    )


    plot <- plotly_dark_layout(
      plot,
      x_title = "Walk-forward fold",
      y_title = "Maximum drawdown"
    )


    plot |>
      plotly::layout(
        yaxis = list(
          title = "Maximum drawdown",
          tickformat = ".1%",
          gridcolor = COLOR_GRID
        )
      )
  })


  # ==========================================================
  # FOLD ACCURACY VS RETURN
  # ==========================================================


  output$fold_scatter_plot <- renderPlotly({
    frame <- folds()

    if (nrow(frame) == 0) {
      return(
        empty_plotly(
          "No fold relationship data available."
        )
      )
    }


    colors <- ifelse(
      frame$net_return >= 0,
      COLOR_GREEN,
      COLOR_RED
    )


    plot <- plotly::plot_ly(
      data = frame,
      x = ~balanced_accuracy,
      y = ~net_return,
      type = "scatter",
      mode = "markers+text",
      text = ~ paste0(
        "Fold ",
        fold
      ),
      textposition = "top center",
      marker = list(
        size = 14,
        color = colors,
        opacity = 0.9,
        line = list(
          color = "#ffffff",
          width = 0.6
        )
      ),
      hovertext = ~ paste0(
        "<b>Fold ",
        fold,
        "</b><br>",
        "Balanced accuracy: ",
        percent(
          balanced_accuracy,
          accuracy = 0.01
        ),
        "<br>",
        "Net return: ",
        percent(
          net_return,
          accuracy = 0.01
        ),
        "<br>",
        "Drawdown: ",
        percent(
          maximum_drawdown,
          accuracy = 0.01
        )
      ),
      hoverinfo = "text"
    )


    plot <- plotly_dark_layout(
      plot,
      x_title = "Balanced accuracy",
      y_title = "Net return"
    )


    plot |>
      plotly::layout(
        xaxis = list(
          title = "Balanced accuracy",
          tickformat = ".0%",
          gridcolor = COLOR_GRID
        ),
        yaxis = list(
          title = "Net return",
          tickformat = ".1%",
          gridcolor = COLOR_GRID,
          zeroline = TRUE,
          zerolinecolor = "#8b949e"
        )
      )
  })


  # ==========================================================
  # MODEL TABLE
  # ==========================================================


  output$model_table <- renderDT({
    frame <- metrics()


    if (nrow(frame) == 0) {
      frame <- data.frame(
        status = "No evaluation artifact available."
      )
    }


    display <- frame


    if (
      "balanced_accuracy" %in%
        names(display)
    ) {
      display <- display |>
        mutate(
          balanced_accuracy = percent(
            balanced_accuracy,
            accuracy = 0.01
          ),
          macro_f1 = percent(
            macro_f1,
            accuracy = 0.01
          ),
          net_return = percent(
            net_return,
            accuracy = 0.01
          ),
          maximum_drawdown = percent(
            maximum_drawdown,
            accuracy = 0.01
          ),
          positive_fold_fraction = percent(
            positive_fold_fraction,
            accuracy = 0.01
          ),
          composite_score = round(
            composite_score,
            4
          ),
          trade_count = round(
            trade_count
          )
        )
    }


    DT::datatable(
      display,
      rownames = FALSE,
      filter = "top",
      options = list(
        pageLength = 10,
        scrollX = TRUE,
        autoWidth = TRUE
      ),
      class = "stripe hover compact"
    )
  })


  # ==========================================================
  # RESEARCH TABLE
  # ==========================================================


  output$research_table <- renderDT({
    frame <- metrics()


    if (nrow(frame) == 0) {
      frame <- data.frame(
        status = "No research metrics available."
      )
    }


    table <- DT::datatable(
      frame,
      rownames = FALSE,
      filter = "top",
      options = list(
        pageLength = 15,
        scrollX = TRUE,
        autoWidth = TRUE
      ),
      class = "stripe hover compact"
    )


    numeric_columns <- intersect(
      c(
        "balanced_accuracy",
        "macro_f1",
        "net_return",
        "maximum_drawdown",
        "positive_fold_fraction",
        "composite_score"
      ),
      names(frame)
    )


    if (length(numeric_columns) > 0) {
      table <- DT::formatRound(
        table,
        columns = numeric_columns,
        digits = 4
      )
    }


    table
  })


  # ==========================================================
  # LATEST CYCLE TABLE
  # ==========================================================


  output$latest_table <- renderDT({
    current <- latest()


    if (is.null(current)) {
      frame <- data.frame(
        Metric = "Status",
        Value = "No learning-cycle artifact available."
      )
    } else {
      frame <- data.frame(
        Metric = c(
          "Symbol",
          "Interval",
          "Winning model",
          "Rows used",
          "Research rows",
          "Holdout rows",
          "Walk-forward net return",
          "Holdout net return",
          "Holdout balanced accuracy",
          "Historical qualification",
          "Artifact freshness"
        ),
        Value = c(
          safe_character(
            current$symbol
          ),
          safe_character(
            current$interval
          ),
          safe_character(
            current$winning_model
          ),
          integer_text(
            current$rows_used %||% 0
          ),
          integer_text(
            current$research_rows %||% 0
          ),
          integer_text(
            current$holdout_rows %||% 0
          ),
          percent_text(
            current$walk_forward_net_return %||% 0
          ),
          percent_text(
            current$holdout_net_return %||% 0
          ),
          percent_text(
            current$holdout_balanced_accuracy %||% 0
          ),
          if (
            isTRUE(
              current$historical_qualified
            )
          ) {
            "PASSED"
          } else {
            "NOT PASSED"
          },
          artifact_age(
            latest_learning_path
          )
        ),
        stringsAsFactors = FALSE
      )
    }


    DT::datatable(
      frame,
      rownames = FALSE,
      options = list(
        dom = "t",
        ordering = FALSE,
        pageLength = 20
      ),
      class = "stripe hover compact"
    )
  })


  # ==========================================================
  # GOVERNANCE DETAIL
  # ==========================================================


  output$governance_detail <- renderUI({
    current <- latest()

    current_shadow <- shadow()

    champ <- champion()


    historical_pass <- (
      !is.null(current) &&
        isTRUE(
          current$historical_qualified
        )
    )


    historical_reason <- if (
      is.null(current)
    ) {
      "No learning-cycle artifact is available."
    } else {
      safe_character(
        current$historical_reason,
        if (historical_pass) {
          paste(
            "Candidate satisfied",
            "historical qualification."
          )
        } else {
          paste(
            "Candidate has not satisfied",
            "historical qualification."
          )
        }
      )
    }


    shadow_text <- if (
      is.null(current_shadow)
    ) {
      paste(
        "No candidate is currently in",
        "prospective shadow validation."
      )
    } else {
      paste(
        "Shadow state:",
        toupper(
          safe_character(
            current_shadow$shadow_status,
            "OBSERVING"
          )
        )
      )
    }


    champion_text <- if (
      is.null(champ)
    ) {
      paste(
        "No qualified champion exists.",
        "Paper execution remains governed",
        "and blocked."
      )
    } else {
      paste(
        "A qualified champion exists.",
        "Execution remains paper-only."
      )
    }


    tagList(
      div(
        class = "governance-detail-grid",
        div(
          class = if (historical_pass) {
            paste(
              "governance-detail-card",
              "state-pass"
            )
          } else {
            paste(
              "governance-detail-card",
              "state-block"
            )
          },
          h4(
            "Historical qualification"
          ),
          h3(
            if (historical_pass) {
              "PASSED"
            } else {
              "NOT PASSED"
            }
          ),
          p(
            historical_reason
          )
        ),
        div(
          class = "governance-detail-card",
          h4(
            "Prospective validation"
          ),
          h3(
            if (
              is.null(
                current_shadow
              )
            ) {
              "WAITING"
            } else {
              "ACTIVE"
            }
          ),
          p(
            shadow_text
          )
        ),
        div(
          class = if (
            is.null(
              champ
            )
          ) {
            paste(
              "governance-detail-card",
              "state-block"
            )
          } else {
            paste(
              "governance-detail-card",
              "state-pass"
            )
          },
          h4(
            "Champion"
          ),
          h3(
            if (
              is.null(
                champ
              )
            ) {
              "NONE"
            } else {
              "QUALIFIED"
            }
          ),
          p(
            champion_text
          )
        )
      ),
      div(
        class = "paper-only-banner",
        icon(
          "lock"
        ),
        span(
          paste(
            "Execution mode: PAPER / SHADOW.",
            "Live-money enablement is disabled."
          )
        )
      )
    )
  })
}


# ============================================================
# START APPLICATION
# ============================================================


shinyApp(
  ui = ui,
  server = server
)
