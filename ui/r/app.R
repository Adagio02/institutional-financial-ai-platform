library(shiny)
library(shinydashboard)
library(jsonlite)
library(ggplot2)
library(dplyr)
library(DT)
library(scales)
library(lubridate)
library(tidyr)


`%||%` <- function(x, default) {
  if (
    is.null(x) ||
    length(x) == 0 ||
    identical(x, "")
  ) {
    return(default)
  }

  x
}


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


safe_read_json <- function(path) {
  if (!file.exists(path)) {
    return(NULL)
  }

  tryCatch(
    fromJSON(
      path,
      simplifyVector = FALSE
    ),
    error = function(error) {
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

  info <- file.info(files)

  files[
    which.max(
      info$mtime
    )
  ]
}


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

  safe_read_json(
    path
  )
}


read_champion <- function() {
  v41 <- safe_read_json(
    v41_champion_path
  )

  if (!is.null(v41)) {
    return(v41)
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


number_or_zero <- function(value) {
  value <- value %||% 0

  result <- suppressWarnings(
    as.numeric(value)
  )

  if (
    length(result) == 0 ||
    is.na(result)
  ) {
    return(0)
  }

  result
}


percent_text <- function(value) {
  value <- number_or_zero(
    value
  )

  percent(
    value,
    accuracy = 0.01
  )
}


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
        model = (
          model$model_name %||% "unknown"
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

  bind_rows(
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
    if (
      identical(
        model$model_name,
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

  bind_rows(
    rows
  )
}


ui <- dashboardPage(
  skin = "black",

  dashboardHeader(
    title = "FinAI V4.2"
  ),

  dashboardSidebar(
    sidebarMenu(
      menuItem(
        "Executive",
        tabName = "executive",
        icon = icon("dashboard")
      ),

      menuItem(
        "Models",
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
    )
  ),

  dashboardBody(
    tags$head(
      tags$link(
        rel = "stylesheet",
        type = "text/css",
        href = "custom.css"
      )
    ),

    tabItems(
      tabItem(
        tabName = "executive",

        fluidRow(
          valueBoxOutput(
            "system_box",
            width = 3
          ),

          valueBoxOutput(
            "champion_box",
            width = 3
          ),

          valueBoxOutput(
            "candidate_box",
            width = 3
          ),

          valueBoxOutput(
            "holdout_box",
            width = 3
          )
        ),

        fluidRow(
          shinydashboard::box(
            title = "Model composite score",
            width = 6,
            status = "primary",
            solidHeader = TRUE,

            plotOutput(
              "composite_plot",
              height = 320
            )
          ),

          shinydashboard::box(
            title = "Walk-forward net return",
            width = 6,
            status = "primary",
            solidHeader = TRUE,

            plotOutput(
              "return_plot",
              height = 320
            )
          )
        ),

        fluidRow(
          shinydashboard::box(
            title = "Latest learning cycle",
            width = 12,
            status = "info",
            solidHeader = TRUE,

            tableOutput(
              "latest_table"
            )
          )
        )
      ),

      tabItem(
        tabName = "models",

        fluidRow(
          shinydashboard::box(
            title = "Classification quality",
            width = 6,
            status = "primary",
            solidHeader = TRUE,

            plotOutput(
              "classification_plot",
              height = 350
            )
          ),

          shinydashboard::box(
            title = "Risk vs return",
            width = 6,
            status = "warning",
            solidHeader = TRUE,

            plotOutput(
              "risk_return_plot",
              height = 350
            )
          )
        ),

        fluidRow(
          shinydashboard::box(
            title = "Model comparison",
            width = 12,
            status = "primary",
            solidHeader = TRUE,

            DTOutput(
              "model_table"
            )
          )
        )
      ),

      tabItem(
        tabName = "validation",

        fluidRow(
          valueBoxOutput(
            "historical_box",
            width = 4
          ),

          valueBoxOutput(
            "shadow_box",
            width = 4
          ),

          valueBoxOutput(
            "execution_box",
            width = 4
          )
        ),

        fluidRow(
          shinydashboard::box(
            title = "Winning-model fold returns",
            width = 6,
            status = "primary",
            solidHeader = TRUE,

            plotOutput(
              "fold_return_plot",
              height = 350
            )
          ),

          shinydashboard::box(
            title = "Fold balanced accuracy",
            width = 6,
            status = "info",
            solidHeader = TRUE,

            plotOutput(
              "fold_accuracy_plot",
              height = 350
            )
          )
        ),

        fluidRow(
          shinydashboard::box(
            title = "Governance state",
            width = 12,
            status = "warning",
            solidHeader = TRUE,

            verbatimTextOutput(
              "governance_text"
            )
          )
        )
      ),

      tabItem(
        tabName = "research",

        fluidRow(
          shinydashboard::box(
            title = "Research metrics",
            width = 12,
            status = "primary",
            solidHeader = TRUE,

            DTOutput(
              "research_table"
            )
          )
        )
      ),

      tabItem(
        tabName = "architecture",

        fluidRow(
          shinydashboard::box(
            title = "FinAI architecture",
            width = 12,
            status = "primary",
            solidHeader = TRUE,

            tags$div(
              class = "architecture",

              tags$pre(
"
REAL MARKET DATA
      |
      v
AAPL + SPY + QQQ
      |
      v
DATABASE
      |
      v
V4.1 FEATURE ENGINEERING
      |
      v
REGIME-AWARE ML
      |
      v
PURGED WALK-FORWARD
      |
      v
UNTOUCHED HOLDOUT
      |
   +--+--+
   |     |
 FAIL   PASS
   |     |
REJECT  v
      SHADOW
        |
        v
PROSPECTIVE VALIDATION
        |
     +--+--+
     |     |
   FAIL   PASS
     |     |
 OBSERVE  v
       CHAMPION
           |
           v
       PAPER MODE
"
              )
            )
          )
        )
      )
    )
  )
)


server <- function(
  input,
  output,
  session
) {
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

    fold_dataframe(
      evaluations(),
      current$winning_model %||% ""
    )
  })


  output$system_box <- renderValueBox({
    current <- latest()

    healthy <- !is.null(
      current
    )

    valueBox(
      value = if (healthy) {
        "ONLINE"
      } else {
        "WAITING"
      },

      subtitle = "Research artifact feed",

      icon = icon(
        "server"
      ),

      color = if (healthy) {
        "green"
      } else {
        "yellow"
      }
    )
  })


  output$champion_box <- renderValueBox({
    champ <- champion()

    exists <- !is.null(
      champ
    )

    valueBox(
      value = if (exists) {
        "YES"
      } else {
        "NONE"
      },

      subtitle = "Qualified champion",

      icon = icon(
        "trophy"
      ),

      color = if (exists) {
        "green"
      } else {
        "yellow"
      }
    )
  })


  output$candidate_box <- renderValueBox({
    current <- latest()

    value <- if (
      is.null(current)
    ) {
      "NONE"
    } else {
      current$winning_model %||% "unknown"
    }

    valueBox(
      value = value,
      subtitle = "Latest candidate",
      icon = icon("bar-chart"),
      color = "aqua"
    )
  })


  output$holdout_box <- renderValueBox({
    current <- latest()

    value <- if (
      is.null(current)
    ) {
      "N/A"
    } else {
      percent_text(
        current$holdout_net_return %||% 0
      )
    }

    valueBox(
      value = value,
      subtitle = "Holdout net return",
      icon = icon("line-chart"),
      color = "purple"
    )
  })


  output$historical_box <- renderValueBox({
    current <- latest()

    qualified <- (
      !is.null(current) &&
      isTRUE(
        current$historical_qualified
      )
    )

    valueBox(
      value = if (qualified) {
        "PASS"
      } else {
        "NOT PASSED"
      },

      subtitle = "Historical qualification",

      icon = icon(
        "check-circle"
      ),

      color = if (qualified) {
        "green"
      } else {
        "yellow"
      }
    )
  })


  output$shadow_box <- renderValueBox({
    current_shadow <- shadow()

    state <- if (
      is.null(current_shadow)
    ) {
      "NONE"
    } else {
      toupper(
        current_shadow$shadow_status %||% "OBSERVING"
      )
    }

    valueBox(
      value = state,
      subtitle = "Prospective validation",
      icon = icon("eye"),
      color = "aqua"
    )
  })


  output$execution_box <- renderValueBox({
    champ <- champion()

    valueBox(
      value = if (
        is.null(champ)
      ) {
        "BLOCKED"
      } else {
        "PAPER READY"
      },

      subtitle = "Execution governance",

      icon = icon(
        "lock"
      ),

      color = if (
        is.null(champ)
      ) {
        "red"
      } else {
        "green"
      }
    )
  })


  output$composite_plot <- renderPlot({
    frame <- metrics()

    shiny::validate(
      shiny::need(
        nrow(frame) > 0,
        "No model evaluation exists yet."
      )
    )

    ggplot(
      frame,
      aes(
        x = reorder(
          model,
          composite_score
        ),
        y = composite_score
      )
    ) +
      geom_col() +
      coord_flip() +
      labs(
        x = NULL,
        y = "Composite score"
      ) +
      theme_minimal(
        base_size = 13
      )
  })


  output$return_plot <- renderPlot({
    frame <- metrics()

    shiny::validate(
      shiny::need(
        nrow(frame) > 0,
        "No return data exists yet."
      )
    )

    ggplot(
      frame,
      aes(
        x = reorder(
          model,
          net_return
        ),
        y = net_return
      )
    ) +
      geom_col() +
      coord_flip() +
      scale_y_continuous(
        labels = percent
      ) +
      labs(
        x = NULL,
        y = "Net return"
      ) +
      theme_minimal(
        base_size = 13
      )
  })


  output$classification_plot <- renderPlot({
    frame <- metrics()

    shiny::validate(
      shiny::need(
        nrow(frame) > 0,
        "No classification metrics yet."
      )
    )

    plotting <- frame |>
      select(
        model,
        balanced_accuracy,
        macro_f1
      ) |>
      pivot_longer(
        cols = c(
          balanced_accuracy,
          macro_f1
        ),
        names_to = "metric",
        values_to = "value"
      )

    ggplot(
      plotting,
      aes(
        x = model,
        y = value,
        fill = metric
      )
    ) +
      geom_col(
        position = "dodge"
      ) +
      scale_y_continuous(
        labels = percent
      ) +
      coord_flip() +
      labs(
        x = NULL,
        y = "Score",
        fill = NULL
      ) +
      theme_minimal(
        base_size = 13
      )
  })


  output$risk_return_plot <- renderPlot({
    frame <- metrics()

    shiny::validate(
      shiny::need(
        nrow(frame) > 0,
        "No risk data exists yet."
      )
    )

    ggplot(
      frame,
      aes(
        x = maximum_drawdown,
        y = net_return,
        label = model
      )
    ) +
      geom_point(
        size = 4
      ) +
      geom_text(
        nudge_y = 0.01,
        check_overlap = TRUE
      ) +
      scale_x_continuous(
        labels = percent
      ) +
      scale_y_continuous(
        labels = percent
      ) +
      labs(
        x = "Maximum drawdown",
        y = "Net return"
      ) +
      theme_minimal(
        base_size = 13
      )
  })


  output$fold_return_plot <- renderPlot({
    frame <- folds()

    shiny::validate(
      shiny::need(
        nrow(frame) > 0,
        "No winning-model fold data yet."
      )
    )

    ggplot(
      frame,
      aes(
        x = factor(
          fold
        ),
        y = net_return
      )
    ) +
      geom_col() +
      scale_y_continuous(
        labels = percent
      ) +
      labs(
        x = "Walk-forward fold",
        y = "Net return"
      ) +
      theme_minimal(
        base_size = 13
      )
  })


  output$fold_accuracy_plot <- renderPlot({
    frame <- folds()

    shiny::validate(
      shiny::need(
        nrow(frame) > 0,
        "No fold accuracy exists yet."
      )
    )

    ggplot(
      frame,
      aes(
        x = fold,
        y = balanced_accuracy
      )
    ) +
      geom_line(
        linewidth = 1
      ) +
      geom_point(
        size = 3
      ) +
      scale_y_continuous(
        labels = percent
      ) +
      labs(
        x = "Walk-forward fold",
        y = "Balanced accuracy"
      ) +
      theme_minimal(
        base_size = 13
      )
  })


  output$model_table <- renderDT({
    frame <- metrics()

    datatable(
      frame,
      rownames = FALSE,

      options = list(
        pageLength = 10,
        scrollX = TRUE
      )
    )
  })


  output$research_table <- renderDT({
    frame <- metrics()

    datatable(
      frame,
      rownames = FALSE,

      options = list(
        pageLength = 10,
        scrollX = TRUE
      )
    )
  })


  output$latest_table <- renderTable({
    current <- latest()

    if (is.null(current)) {
      return(
        data.frame(
          status = "No learning cycle yet"
        )
      )
    }

    data.frame(
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
        "Historical qualification"
      ),

      Value = c(
        current$symbol %||% "N/A",

        current$interval %||% "N/A",

        current$winning_model %||% "N/A",

        current$rows_used %||% "N/A",

        current$research_rows %||% "N/A",

        current$holdout_rows %||% "N/A",

        percent_text(
          current$walk_forward_net_return %||% 0
        ),

        percent_text(
          current$holdout_net_return %||% 0
        ),

        percent_text(
          current$holdout_balanced_accuracy %||% 0
        ),

        current$historical_qualified %||% FALSE
      )
    )
  })


  output$governance_text <- renderText({
    current <- latest()
    current_shadow <- shadow()
    champ <- champion()

    historical <- if (
      !is.null(current) &&
      isTRUE(
        current$historical_qualified
      )
    ) {
      "PASSED"
    } else {
      "NOT PASSED"
    }

    shadow_state <- if (
      is.null(current_shadow)
    ) {
      "NO SHADOW CANDIDATE"
    } else {
      toupper(
        current_shadow$shadow_status %||% "OBSERVING"
      )
    }

    champion_state <- if (
      is.null(champ)
    ) {
      "NONE"
    } else {
      "AVAILABLE"
    }

    paste0(
      "Historical qualification: ",
      historical,
      "\n",
      "Shadow state: ",
      shadow_state,
      "\n",
      "Champion: ",
      champion_state,
      "\n",
      "Execution mode: PAPER / GOVERNED",
      "\n",
      "Live-money enablement: DISABLED"
    )
  })
}


shinyApp(
  ui = ui,
  server = server
)