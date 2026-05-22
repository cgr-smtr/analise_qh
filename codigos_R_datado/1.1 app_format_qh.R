options(shiny.maxRequestSize = 40*1024^2)

library(shiny)
library(kableExtra)
library(knitr)
library(stringr)
library(data.table)

ui <- fluidPage(
  titlePanel("Análise da Operação de Linhas de Ônibus"),
  sidebarLayout(
    sidebarPanel(
      width = 2,
      fileInput("gtfs_zip", "Carregar arquivo GTFS (ZIP)", accept = c(".zip")),
      selectInput("route", "Selecione uma linha:", choices = NULL),
      selectInput("direction_id", "Selecione o sentido:", choices = NULL),
      selectInput("service", "Selecione um calendário:", choices = NULL),
      selectInput("trip_headsign", "Selecione o destino:", choices = NULL),
      downloadButton("downloadData", "Baixar QH em CSV")
    ),
    mainPanel(
      h3("trip_headsign"),
      verbatimTextOutput("unique_destinations"),
      fluidRow(
        column(3,
               h3("Colar a Programação Prevista (um horário por linha):"),
               actionButton("clear", "Limpar"), 
               textAreaInput("partidas", 
                             NULL,
                             rows = 30, placeholder = "Exemplo:\n03:40:00\n04:00:00\n04:20:00\n...")
        ),
        column(3,
               h2('Tabela do GTFS'),
               tableOutput("schedule_table")),
        column(3,
               h2('Tabela Proposta'),
               textOutput("error_message"),
               tableOutput("numeracao_horarios")),
        column(3,
               h2('Comparação'),
               tableOutput("comparison_table"))
      ),
      fluidRow(
        column(5,
               h3("Partidas por Faixa Horária"),
               tableOutput("summary_table")
        )
      )
    )
  )
)

library(shiny)
library(tidytransit)
library(dplyr)
library(tidyr)
library(DT)
library(purrr)

server <- function(input, output, session) {
  
  observeEvent(input$clear, {
    updateTextAreaInput(session, "partidas", value = "")
  })
  
  gtfs_data <- reactiveVal(NULL)
  
  observeEvent(input$gtfs_zip, {
    req(input$gtfs_zip)
    gtfs <- read_gtfs(input$gtfs_zip$datapath)
    gtfs_data(gtfs)
    
    route_choices <- gtfs$routes %>%
      select(route_id, route_short_name) %>%
      arrange(route_short_name) %>% 
      mutate(route_choice = paste(route_short_name, route_id, sep = " - ")) %>%
      pull(route_choice)
    
    updateSelectInput(session, "route", choices = route_choices)
  })
  
  observeEvent(input$route, {
    req(gtfs_data())
    gtfs <- gtfs_data()
    selected_route_id <- str_extract(input$route, "(?<= - ).*")
    trips <- gtfs$trips %>% filter(route_id == selected_route_id)
    updateSelectInput(session, "direction_id", choices = unique(trips$direction_id))
  })
  
  observe({
    req(input$direction_id, gtfs_data())
    gtfs <- gtfs_data()
    selected_route_id <- str_extract(input$route, "(?<= - ).*")
    trips <- gtfs$trips %>%
      filter(route_id == selected_route_id, direction_id == input$direction_id)
    updateSelectInput(session, "service", choices = unique(trips$service_id))
  })
  
  observe({
    req(input$route, input$direction_id, gtfs_data())
    gtfs <- gtfs_data()
    selected_route_id <- str_extract(input$route, "(?<= - ).*")
    headsigns <- gtfs$trips %>%
      filter(route_id == selected_route_id, direction_id == input$direction_id) %>%
      pull(trip_headsign)
    opcoes <- unique(headsigns[!is.na(headsigns) & headsigns != ""])
    updateSelectInput(session, "trip_headsign",
                      choices = opcoes,
                      selected = opcoes[1])
  })
  
  get_time_color <- function(hora) {
    case_when(
      hora >= 0  & hora < 1  ~ "#B3E5FC",
      hora >= 1  & hora < 2  ~ "#80DEEA",
      hora >= 2  & hora < 3  ~ "#80CBC4",
      hora >= 3  & hora < 4  ~ "#A5D6A7",
      hora >= 4  & hora < 5  ~ "#C8E6C9",
      hora >= 5  & hora < 6  ~ "#E6EE9C",
      hora >= 6  & hora < 9  ~ "#FFF59D",
      hora >= 9  & hora < 12 ~ "#FFE082",
      hora >= 12 & hora < 15 ~ "#FFCC80",
      hora >= 15 & hora < 18 ~ "#FFAB91",
      hora >= 18 & hora < 21 ~ "#F48FB1",
      hora >= 21 & hora < 22 ~ "#CE93D8",
      hora >= 22 & hora < 23 ~ "#B39DDB",
      hora >= 23 & hora < 24 ~ "#9FA8DA",
      hora >= 24 & hora < 25 ~ "#E0E0E0",
      hora >= 25 & hora < 26 ~ "#CFD8DC",
      hora >= 26 & hora < 27 ~ "#D7CCC8",
      hora >= 27 & hora < 28 ~ "#DCEDC8",
      hora >= 28 & hora < 29 ~ "#FFF9C4",
      hora >= 29 & hora < 30 ~ "#FFECB3"
    )
  }
  
  # Função auxiliar para gerar schedule a partir do GTFS
  get_gtfs_schedule <- function(gtfs, trips) {
    if ("frequencies" %in% names(gtfs)) {
      frequencies <- gtfs$frequencies %>%
        filter(trip_id %in% trips$trip_id) %>%
        arrange(start_time) %>%
        mutate(
          start_time = as.character(start_time),
          end_time = as.character(end_time),
          start_seconds = as.numeric(lubridate::hms(start_time)),
          end_seconds = as.numeric(lubridate::hms(end_time))
        ) %>%
        filter(is.finite(start_seconds) & is.finite(end_seconds) & start_seconds < end_seconds)
      
      schedule <- frequencies %>%
        rowwise() %>%
        do(data.frame(departure_times = seq(.$start_seconds, .$end_seconds - .$headway_secs, by = .$headway_secs))) %>%
        ungroup() %>%
        distinct(.data$departure_times) %>%
        arrange(.data$departure_times) %>%
        mutate(
          departure_time = sprintf("%02d:%02d:%02d",
                                   .data$departure_times %/% 3600,
                                   (.data$departure_times %% 3600) %/% 60,
                                   .data$departure_times %% 60)
        ) %>%
        select(departure_time)
      
      return(schedule)
    }
    return(NULL)
  }
  
  output$schedule_table <- renderTable({
    req(gtfs_data(), input$route, input$direction_id, input$service, input$trip_headsign)
    gtfs <- gtfs_data()
    selected_route_id <- str_extract(input$route, "(?<= - ).*")
    
    trips <- gtfs$trips %>%
      filter(route_id == selected_route_id,
             direction_id == input$direction_id,
             service_id == input$service) %>%
      filter(trip_headsign == input$trip_headsign)
    
    schedule <- get_gtfs_schedule(gtfs, trips)
    req(!is.null(schedule))
    
    schedule <- schedule %>%
      arrange(departure_time) %>%
      mutate(
        numero = row_number(),
        departure_seconds = as.numeric(lubridate::hms(departure_time)),
        hora = as.numeric(str_extract(as.character(departure_time), "^[0-9]{2}")),
        intervalo = ifelse(numero == 1, NA, (departure_seconds - lag(departure_seconds)) / 60)
      ) %>%
      select(Partida = numero, Horário = departure_time, hora, Intervalo = intervalo)
    
    schedule %>%
      mutate(
        Horário = paste0('<div style="background-color:', get_time_color(hora), ';">', Horário, '</div>')
      ) %>%
      select(Partida, Horário, Intervalo)
    
  }, sanitize.text.function = function(x) x,
  html.table.attributes = "style='width:100%'",
  bordered = TRUE)
  
  horarios_programados <- reactive({
    req(input$partidas)
    horarios <- unlist(strsplit(input$partidas, "\n"))
    horarios <- trimws(horarios)
    horarios <- horarios[horarios != ""]
    
    valid <- all(grepl("^([0-2]?[0-9]):[0-5][0-9]:[0-5][0-9]$", horarios))
    if (!valid) return(NULL)
    
    horarios_seg <- sapply(horarios, function(h) {
      partes <- as.numeric(strsplit(h, ":")[[1]])
      partes[1] * 3600 + partes[2] * 60 + partes[3]
    })
    
    for (i in 2:length(horarios_seg)) {
      if (horarios_seg[i] < horarios_seg[i - 1]) {
        horarios_seg[i] <- horarios_seg[i] + 86400
      }
    }
    
    as.POSIXct(horarios_seg, origin = "1970-01-01", tz = "America/Sao_Paulo")
  })
  
  output$error_message <- renderText({
    if (is.null(horarios_programados())) {
      "Erro: Um ou mais horários foram inseridos no formato incorreto. Use o formato HH:MM:SS."
    } else {
      ""
    }
  })
  
  output$unique_destinations <- renderPrint({
    req(gtfs_data())
    gtfs <- gtfs_data()
    selected_route_id <- str_extract(input$route, "(?<= - ).*")
    trips <- gtfs$trips %>%
      filter(route_id == selected_route_id, direction_id == input$direction_id) %>%
      filter(trip_headsign == input$trip_headsign)
    cat(unique(trips$trip_headsign), sep = "\n")
  })
  
  output$numeracao_horarios <- renderTable({
    req(horarios_programados())
    horarios <- horarios_programados()
    
    intervalos <- c(NA, as.numeric(difftime(horarios[-1], horarios[-length(horarios)], units = "mins")))
    intervalos <- ifelse(is.na(intervalos), "-", round(intervalos, 2))
    
    secs <- as.numeric(horarios)
    hora <- floor(secs / 3600)
    
    data.frame(
      Partida = seq_along(horarios),
      Horário = paste0(
        '<div style="background-color:', get_time_color(hora), ';">',
        sprintf("%02d:%02d:%02d", secs %/% 3600L, (secs %% 3600) %/% 60, secs %% 60),
        '</div>'
      ),
      Intervalo = intervalos
    )
  },
  bordered = TRUE,
  align = 'c',
  digits = 0,
  sanitize.text.function = function(x) x,
  html.table.attributes = "style='width:100%; border-collapse: collapse;'")
  
  user_schedule_processed <- reactive({
    req(input$partidas, input$route, input$direction_id)
    horarios_programados <- str_split(input$partidas, "\\n") %>% unlist() %>% str_trim()
    
    horarios_segundos <- sapply(horarios_programados, function(h) {
      as.numeric(lubridate::hms(h))
    })
    
    h <- as.data.table(horarios_segundos) %>%
      mutate(horarios_segundos = if_else(horarios_segundos < lag(horarios_segundos) & row_number() != 1,
                                         horarios_segundos + 86400, horarios_segundos))
    
    for(j in 1:nrow(h)){
      h <- h %>%
        mutate(horarios_segundos = if_else(horarios_segundos < lag(horarios_segundos) & row_number() != 1,
                                           horarios_segundos + 86400, horarios_segundos))
    }
    
    h <- h %>%
      mutate(headway_secs = lead(horarios_segundos) - horarios_segundos,
             headway_secs = if_else(row_number() == n(), lag(headway_secs), headway_secs)) %>%
      rename(start_time = horarios_segundos) %>%
      mutate(end_time = start_time + headway_secs) %>%
      select(start_time, end_time, headway_secs)
    
    while (length(unique(h$teste)) != 1){
      h <- h %>%
        mutate(end_time = if_else(lead(headway_secs) == headway_secs & !is.na(lead(headway_secs)), lead(end_time), end_time)) %>%
        filter(end_time != lag(end_time) | is.na(lag(end_time))) %>%
        mutate(teste = headway_secs == lead(headway_secs)) %>%
        mutate(teste = if_else(is.na(teste), FALSE, teste))
    }
    
    headsign <- input$trip_headsign
    
    h <- h %>%
      select(-c(teste)) %>%
      mutate(end_time = if_else(end_time < start_time, end_time + 86400, end_time)) %>%
      mutate(start_time = lubridate::seconds_to_period(start_time),
             end_time = lubridate::seconds_to_period(end_time)) %>%
      mutate(start_time = hms::hms(start_time),
             end_time = hms::hms(end_time)) %>%
      mutate(
        trip_short_name = sub("\\s*-\\s*.*$", "", input$route),
        trip_headsign = headsign,
        trip_id = ''
      ) %>%
      filter(trip_headsign == input$trip_headsign) %>%
      select(trip_id, trip_headsign, trip_short_name, start_time, end_time, headway_secs)
    
    return(h)
  })
  
  output$comparison_table <- renderTable({
    req(input$partidas, gtfs_data(), input$route, input$direction_id,
        input$service, input$trip_headsign, horarios_programados())
    
    round_to_minute <- function(x) round(as.numeric(x) / 60) * 60
    
    find_nearest_time <- function(x, y) {
      y[which.min(abs(difftime(x, y, units = "mins")))]
    }
    
    gtfs <- gtfs_data()
    selected_route_id <- str_extract(input$route, "(?<= - ).*")
    
    trips <- gtfs$trips %>%
      filter(route_id == selected_route_id,
             direction_id == input$direction_id,
             service_id == input$service) %>%
      filter(trip_headsign == input$trip_headsign)
    
    schedule <- get_gtfs_schedule(gtfs, trips)
    req(!is.null(schedule))
    
    # Manter tudo em segundos numéricos — mesma escala para GTFS e usuário
    gtfs_schedule <- schedule %>%
      arrange(departure_time) %>%
      mutate(
        departure_seconds = as.numeric(lubridate::hms(departure_time)),
        intervalo = (departure_seconds - lag(departure_seconds)) / 60
      )
    
    user_schedule <- horarios_programados()
    if (is.null(user_schedule) || length(user_schedule) == 0) {
      return(data.frame(Mensagem = "Nenhum horário fornecido pelo usuário."))
    }
    
    # Ambos com origin = "1970-01-01" — mesma escala!
    gtfs_df <- data.frame(
      time_gtfs = as.POSIXct(round_to_minute(gtfs_schedule$departure_seconds), origin = "1970-01-01", tz = "America/Sao_Paulo"),
      interval_gtfs = gtfs_schedule$intervalo
    )
    
    user_df <- data.frame(
      time_user = as.POSIXct(round_to_minute(as.numeric(user_schedule)), origin = "1970-01-01", tz = "America/Sao_Paulo"),
      interval_user = c(NA, as.numeric(difftime(user_schedule[-1], user_schedule[-length(user_schedule)], units = "mins")))
    )
    
    user_df$nearest_gtfs_time <- sapply(user_df$time_user, find_nearest_time, y = gtfs_df$time_gtfs)
    user_df$nearest_gtfs_time <- as.POSIXct(user_df$nearest_gtfs_time, origin = "1970-01-01", tz = "America/Sao_Paulo")
    
    combined_df <- left_join(gtfs_df, user_df, by = c("time_gtfs" = "nearest_gtfs_time"))
    
    unmatched_user <- user_df %>%
      filter(!time_user %in% combined_df$time_user) %>%
      mutate(time_gtfs = time_user)
    
    combined_df <- bind_rows(combined_df, unmatched_user) %>% arrange(time_gtfs)
    
    if (nrow(gtfs_df) <= nrow(user_df)) {
      combined_df <- combined_df %>%
        mutate(diff = abs(difftime(time_gtfs, time_user))) %>%
        arrange(time_gtfs) %>%
        group_by(time_gtfs) %>%
        mutate(
          manter = diff == min(diff) & !duplicated(diff),
          time_gtfs = if_else(manter | is.na(diff), time_gtfs, as.POSIXct(NA, tz = attr(time_gtfs, "tzone")))
        ) %>%
        ungroup()
    } else {
      combined_df <- combined_df %>%
        mutate(diff = abs(difftime(time_gtfs, time_user))) %>%
        group_by(time_user) %>%
        mutate(
          manter_user = diff == min(diff) & !duplicated(diff),
          time_user = if_else(manter_user | is.na(diff), time_user, as.POSIXct(NA, tz = attr(time_user, "tzone")))
        ) %>%
        ungroup() %>%
        group_by(time_gtfs) %>%
        mutate(
          manter_gtfs = diff == min(diff) & !duplicated(diff),
          time_gtfs = if_else(manter_gtfs | is.na(diff), time_gtfs, as.POSIXct(NA, tz = attr(time_gtfs, "tzone")))
        ) %>%
        ungroup()
    }
    
    combined_df$comparison <- ifelse(
      is.na(combined_df$interval_gtfs) | is.na(combined_df$interval_user), "-",
      ifelse(combined_df$interval_user > combined_df$interval_gtfs, "↑",
             ifelse(combined_df$interval_user < combined_df$interval_gtfs, "↓", "=")))
    
    # Ambos agora têm origin="1970-01-01", então floor(as.numeric()/3600) funciona para os dois
    gtfs_secs  <- as.numeric(combined_df$time_gtfs)
    gtfs_hours <- floor(gtfs_secs / 3600)
    user_secs  <- as.numeric(combined_df$time_user)
    user_hours <- floor(user_secs / 3600)
    
    result <- data.frame(
      `Horário GTFS` = ifelse(
        is.na(combined_df$time_gtfs), "-",
        paste0('<div style="background-color:', get_time_color(gtfs_hours), ';">',
               sprintf("%02d:%02d:%02d", gtfs_secs %/% 3600L, (gtfs_secs %% 3600) %/% 60, gtfs_secs %% 60),
               '</div>')
      ),
      `Horário Usuário` = ifelse(
        is.na(combined_df$time_user), "-",
        paste0('<div style="background-color:', get_time_color(user_hours), ';">',
               sprintf("%02d:%02d:%02d", user_secs %/% 3600L, (user_secs %% 3600) %/% 60, user_secs %% 60),
               '</div>')
      ),
      `Intervalo GTFS` = ifelse(is.na(combined_df$interval_gtfs) | is.na(combined_df$time_gtfs), "-", round(combined_df$interval_gtfs, 1)),
      `Intervalo Usuário` = ifelse(is.na(combined_df$interval_user), "-", round(combined_df$interval_user, 1)),
      Comparação = ifelse(is.na(combined_df$interval_gtfs) | is.na(combined_df$time_gtfs) | is.na(combined_df$interval_user) | is.na(combined_df$time_user), "-", combined_df$comparison)
    )
    result
  },
  bordered = TRUE,
  align = 'c',
  digits = 1,
  sanitize.text.function = function(x) x,
  html.table.attributes = "style='width:100%; border-collapse: collapse;'")
  
  output$summary_table <- renderTable({
    req(gtfs_data(), input$route, input$direction_id,
        input$service, input$trip_headsign, horarios_programados())
    
    gtfs <- gtfs_data()
    selected_route_id <- str_extract(input$route, "(?<= - ).*")
    
    trips <- gtfs$trips %>%
      filter(route_id == selected_route_id,
             direction_id == input$direction_id,
             service_id == input$service) %>%
      filter(trip_headsign == input$trip_headsign)
    
    schedule <- get_gtfs_schedule(gtfs, trips)
    req(!is.null(schedule))
    
    schedule <- schedule %>%
      mutate(
        departure_times = as.numeric(lubridate::hms(departure_time)),
        hora = departure_times %/% 3600
      )
    
    gtfs_times <- schedule$hora
    user_times <- floor(as.numeric(horarios_programados()) / 3600)
    
    time_periods <- c("00:00-00:59","01:00-01:59","02:00-02:59","03:00-03:59",
                      "04:00-04:59","05:00-05:59","06:00-08:59","09:00-11:59",
                      "12:00-14:59","15:00-17:59","18:00-20:59","21:00-21:59",
                      "22:00-22:59","23:00-23:59","24:00-24:59","25:00-25:59",
                      "26:00-26:59","27:00-27:59","28:00-28:59","29:00-29:59")
    
    breaks <- c(0, 1, 2, 3, 4, 5, 6, 9, 12, 15, 18, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30)
    
    gtfs_counts <- table(cut(gtfs_times, breaks = breaks, labels = time_periods, include.lowest = TRUE, right = FALSE))
    user_counts <- table(cut(user_times, breaks = breaks, labels = time_periods, include.lowest = TRUE, right = FALSE))
    
    time_to_hour <- setNames(c(0,1,2,3,4,5,6,9,12,15,18,21,22,23,24,25,26,27,28,29), time_periods)
    
    summary_df <- data.frame(
      Faixa = sapply(time_to_hour, function(h) {
        sprintf('<div style="background-color:%s;">%s</div>',
                get_time_color(h),
                names(time_to_hour)[match(h, time_to_hour)])
      }),
      `Partidas GTFS` = as.vector(gtfs_counts),
      `Partidas Propostas` = as.vector(user_counts)
    )
    
    total_row <- data.frame(
      Faixa = "Total",
      `Partidas GTFS` = sum(gtfs_counts),
      `Partidas Propostas` = sum(user_counts)
    )
    
    rbind(summary_df, total_row)
  },
  bordered = TRUE,
  sanitize.text.function = function(x) x,
  html.table.attributes = "style='width:100%; border-collapse: collapse;'")
  
  output$downloadData <- downloadHandler(
    filename = function() {
      headsign <- if(input$trip_headsign != "all") input$trip_headsign else "todos_destinos"
      paste0("horarios_", sub("\\s*-\\s*.*$", "", input$route), "_", headsign, "_", input$service, ".csv")
    },
    content = function(file) {
      write.csv(user_schedule_processed(), file, row.names = FALSE, quote = FALSE)
    }
  )
}

shinyApp(ui = ui, server = server)