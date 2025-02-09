library(readr)
library(dplyr)
library(magrittr)
library(ggplot2)
library(tidyr)
library(trend)

data_path <- commandArgs(trailingOnly = TRUE)[1]
game_dirs <- list.dirs(data_path, full.names = TRUE)

custom_colors <- c("#04ff00", "#000099")

for (dir_index in seq(2, length(game_dirs))) {
  current_game_dir <- game_dirs[dir_index]
  current_game_file <- paste(current_game_dir, "/games.csv", sep = "")
  if (file.exists(current_game_file)) {
    game <- read.csv(current_game_file,
                     fileEncoding = "UTF-8", check.names = FALSE)
    game <- game[-1, ]
    columns <- colnames(game)
    total_players <- (length(columns) - 3) / 2 # 2 columns for each player signifying the bankroll and the tendency index

    entity_counts <- game %>%
      count(.data[["winner"]])

    entity_counts <- entity_counts %>%
      mutate(win_ratio = n / sum(.data[["n"]]),
             winner = winner)

    metrics <- data.frame(
      player = character(),
      # ti = numeric(),
      win_ratio = numeric(),
      stringsAsFactors = FALSE
    )
    for (i in seq(2, 2 + total_players - 1)) {
      player <- columns[i]
      # ti <- game %>%
      #   pull(.data[[columns[i + total_players]]]) %>%
      #   last()
      player_name <- sub("\\(.*", "", player)
      win_ratio <- entity_counts %>%
        filter(grepl(player_name, .data[["winner"]])) %>%
        distinct(winner, .keep_all = TRUE) %>%
        pull(.data[["win_ratio"]])

      metrics <- rbind(metrics, data.frame(player = player, win_ratio = win_ratio))
    }
    output_csv_file <- file.path(current_game_dir, "metrics.csv")
    write.csv(metrics, file = output_csv_file, row.names = FALSE)
    message(paste("Metrics saved to:", output_csv_file))

    ending_round <- game %>%
      count(.data[["ending_round"]])
    output_csv_file <- file.path(current_game_dir, "ending_round.csv")
    write.csv(ending_round, file = output_csv_file, row.names = FALSE)
    message(paste("Ending round data saved to:", output_csv_file))

    game_long <- game %>%
      pivot_longer(cols = columns[2:(2 + total_players - 1)],
             names_to = "Player",
             values_to = "Score") %>%
      mutate(Score = log10(Score)) # logarithmic scaling of the bankrolls

    player_colors <- setNames(custom_colors[seq_len(length(unique(game_long$Player)))],
                              unique(game_long$Player))

    plot <- ggplot(data = game_long,
                   aes(x = hand_no, y = Score, colour = Player)) +
      geom_line() +
      scale_color_manual(values = player_colors) +
      labs(
        x = "Hand Number", y = "Score",
        title = paste("Comparison:",
                      paste(metrics$player,
                            collapse = " vs ")),
        subtitle = paste(paste("Win Ratio:",
                               paste(metrics$win_ratio, collapse = ", ")),
                         sep = "\n")
      ) +
      theme(legend.position = "bottom")
    output_file <- file.path(current_game_dir, "bankroll_line.svg")
    svg(output_file, width = 10, height = 6)
    print(plot)
    dev.off()  # Close the svg device
    message(paste("Bankroll plot saved to:", output_file))

    plot <- ggplot(data = ending_round,
                    aes(x = ending_round, y = n)) +
      geom_bar(stat = "identity") +
      labs(
        x = "Ending Round", y = "Count",
        title = "Ending Round Distribution"
      )
    output_file <- file.path(current_game_dir, "ending_round_hist.svg")
    svg(output_file, width = 10, height = 6)
    print(plot)
    dev.off()  # Close the svg device
    message(paste("Ending round histogram saved to:", output_file))

    size <- 1000
    convergence_metrics <- data.frame(
      index = numeric(),
      player = character(),
      win_ratio_cumm = numeric(),
      win_ratio = numeric(),
      profitability_per_hand_cumm = numeric(),
      profitability_per_hand = numeric(),
      stringsAsFactors = FALSE
    )
    sliced_game <- game %>%
      slice(seq_len(min(size, nrow(game))))
    sliced_game <- game %>%
      slice(seq_len(min(size, nrow(game))))
    for (j in seq(size, nrow(game) - size, size)) {
      sliced_game_cumm <- game %>%
        slice(seq_len(min(j + size, nrow(game))))
      sliced_game <- game %>%
        slice((j + 1): min(j + size, nrow(game)))
      entity_counts_cumm <- sliced_game_cumm %>%
        count(.data[["winner"]])
      entity_counts_cumm <- entity_counts_cumm %>%
        mutate(win_ratio = n / sum(.data[["n"]]),
               winner = winner)
      entity_counts <- sliced_game %>%
        count(.data[["winner"]])
      entity_counts <- entity_counts %>%
        mutate(win_ratio = n / sum(.data[["n"]]),
               winner = winner)
      for (i in seq(2, 2 + total_players - 1)) {
        player <- columns[i]
        player_name <- sub("\\(.*", "", player)
        profitability_per_hand_cumm <- (sliced_game_cumm %>%
          pull(.data[[player]]) %>%
          last() - sliced_game_cumm %>%
          pull(.data[[player]]) %>%
          first()) / nrow(sliced_game_cumm)
        profitability_per_hand <- (sliced_game %>%
          pull(.data[[player]]) %>%
          last() - sliced_game %>%
          pull(.data[[player]]) %>%
          first()) / nrow(sliced_game)
        if (nrow(sliced_game) < size) {
          next
        }
        convergence_metrics <- rbind(convergence_metrics, data.frame(
          index = j,
          player = player,
          win_ratio_cumm = entity_counts_cumm %>%
            filter(grepl(player_name, .data[["winner"]])) %>%
            pull(.data[["win_ratio"]]),
          profitability_per_hand_cumm = profitability_per_hand_cumm,
          win_ratio = entity_counts %>%
            filter(grepl(player_name, .data[["winner"]])) %>%
            pull(.data[["win_ratio"]]),
          profitability_per_hand = profitability_per_hand
        ))
      }
    }
    players <- convergence_metrics$player %>%
      unique()
    size_limit <- 100
    step <- nrow(game) / size_limit
    truncated_game <- game[seq(1, nrow(game), by = step), ]
    truncated_game_long <- truncated_game %>%
      pivot_longer(cols = columns[2:(2 + total_players - 1)],
                   names_to = "Player",
                   values_to = "Score") %>%
      group_by(Player) %>%
      #mutate(Score = EMA(Score, n = 100)) %>%
      ungroup()

    player_bankroll <- truncated_game_long %>%
      filter(Player == !!players[1]) %>%
      pull(Score)
    running_average <- cumsum(player_bankroll) / seq_along(player_bankroll)

    results <- mk.test(running_average)

    player_bankroll_diff <- truncated_game_long %>%
      group_by(hand_no) %>%
      transmute(score_diff = Score[Player == !!players[1]] - Score[Player == !!players[2]]) %>%
      unique()

    mean_diff <- mean(player_bankroll_diff$score_diff)
    sd_diff <- sd(player_bankroll_diff$score_diff)
    cohens_d <- mean_diff / sd_diff

    spearman <- cor(running_average, seq_along(running_average), method = "spearman")
    matchup <- gsub(".*\\((.*)\\).*", "\\1", players)

    analysis_metrics <- data.frame(
      match = paste(matchup, collapse = " "),
      p = results$p.value,
      S = results$estimates[1],
      rho = spearman,
      d = cohens_d
    )
    output_csv_file <- file.path(current_game_dir, "test_results.csv")
    write.csv(analysis_metrics, file = output_csv_file, row.names = FALSE)
    message(paste("Test results saved to:", output_csv_file))
    # output_csv_file <- file.path(current_game_dir, "convergence_metrics.csv")
    # write.csv(convergence_metrics, file = output_csv_file, row.names = FALSE)
    # message(paste("Convergence metrics saved to:", output_csv_file))
    message("---------------------------------------------------------")
  } else {
    print(paste(current_game_file, "not found"))
  }
}