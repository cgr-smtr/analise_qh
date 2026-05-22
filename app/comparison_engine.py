import pandas as pd
import numpy as np
from app.config import TIME_PERIODS, BREAKS

def _round_to_minute(seconds: float) -> int:
    """Arredonda segundos para o minuto mais próximo (equivalente à lógica do R)."""
    if pd.isna(seconds):
        return int(np.nan)
    return int(round(seconds / 60.0) * 60)

def _find_nearest(val: int, candidates: list[int]) -> int:
    """Encontra o valor mais próximo em uma lista de candidatos em segundos."""
    if not candidates:
        return int(np.nan)
    # Acha o candidato que minimiza a diferença absoluta
    return min(candidates, key=lambda c: abs(val - c))

def compare_schedules(gtfs_schedule_df: pd.DataFrame, user_seconds: list[int]) -> pd.DataFrame:
    """
    Compara o quadro de horários GTFS com a lista de segundos do usuário.
    Replica a complexa lógica de matching 1:1 e comparação de intervalos do R.
    
    Retorna um DataFrame com as colunas:
    - time_gtfs: Segundos correspondentes à partida do GTFS (ou None se sem par)
    - time_user: Segundos correspondentes à partida do Usuário (ou None se sem par)
    - interval_gtfs: Intervalo em minutos para a partida anterior no GTFS (ou None)
    - interval_user: Intervalo em minutos para a partida anterior do Usuário (ou None)
    - comparison: String representando o resultado da comparação (↑, ↓, =, -)
    """
    # 1. Preparação do GTFS
    # Garante ordenação e calcula o intervalo
    gtfs = gtfs_schedule_df.copy()
    if gtfs.empty:
        # Se GTFS está vazio, retorna tabela vazia ou indicando nenhum horário
        return pd.DataFrame(columns=['time_gtfs', 'time_user', 'interval_gtfs', 'interval_user', 'comparison'])
        
    gtfs['departure_seconds'] = gtfs['Horário'].apply(lambda x: sum(int(p) * mult for p, mult in zip(x.split(':'), [3600, 60, 1])))
    gtfs = gtfs.sort_values(by='departure_seconds').reset_index(drop=True)
    
    # Cria o DataFrame gtfs_df arredondado para o minuto mais próximo
    gtfs_df = pd.DataFrame({
        'time_gtfs': gtfs['departure_seconds'].apply(_round_to_minute),
        'interval_gtfs': gtfs['Intervalo']
    })
    
    # 2. Preparação do Usuário
    if not user_seconds:
        return pd.DataFrame(columns=['time_gtfs', 'time_user', 'interval_gtfs', 'interval_user', 'comparison'])
        
    user_sorted = sorted(user_seconds)
    user_intervals = [np.nan] + [float(user_sorted[i] - user_sorted[i-1]) / 60.0 for i in range(1, len(user_sorted))]
    
    user_df = pd.DataFrame({
        'time_user': [_round_to_minute(s) for s in user_sorted],
        'interval_user': user_intervals
    })
    
    # 3. Pareamento por vizinhança (nearest matching)
    # Para cada partida do usuário, encontra a partida do GTFS mais próxima
    candidates = gtfs_df['time_gtfs'].tolist()
    user_df['nearest_gtfs_time'] = user_df['time_user'].apply(lambda t: _find_nearest(t, candidates))
    
    # 4. Join: gtfs_df com user_df pelo nearest_gtfs_time
    # Em R: left_join(gtfs_df, user_df, by = c("time_gtfs" = "nearest_gtfs_time"))
    combined_df = pd.merge(
        gtfs_df,
        user_df,
        left_on='time_gtfs',
        right_on='nearest_gtfs_time',
        how='left'
    )
    
    # 5. Adiciona os registros do usuário que não deram match em nenhum registro do GTFS
    # Em R:
    # unmatched_user <- user_df %>% filter(!time_user %in% combined_df$time_user) %>% mutate(time_gtfs = time_user)
    matched_user_times = combined_df['time_user'].dropna().unique()
    unmatched_user = user_df[~user_df['time_user'].isin(matched_user_times)].copy()
    
    if not unmatched_user.empty:
        unmatched_user['time_gtfs'] = unmatched_user['time_user']
        # Concatena com combined_df
        combined_df = pd.concat([combined_df, unmatched_user], ignore_index=True)
        
    # Ordena por time_gtfs (e por time_user em caso de empate)
    combined_df = combined_df.sort_values(by=['time_gtfs', 'time_user']).reset_index(drop=True)
    
    # 6. Lógica de deduplicação e manter pareamento 1:1 único (Diferenciação baseada no tamanho das tabelas)
    if len(gtfs_df) <= len(user_df):
        # Em R:
        # combined_df <- combined_df %>%
        #   mutate(diff = abs(difftime(time_gtfs, time_user))) %>%
        #   arrange(time_gtfs) %>%
        #   group_by(time_gtfs) %>%
        #   mutate(
        #     manter = diff == min(diff) & !duplicated(diff),
        #     time_gtfs = if_else(manter | is.na(diff), time_gtfs, as.POSIXct(NA))
        #   ) %>% ungroup()
        combined_df['diff'] = (combined_df['time_gtfs'] - combined_df['time_user']).abs()
        combined_df = combined_df.sort_values(by='time_gtfs')
        
        # Cria a máscara para manter apenas a menor diferença por time_gtfs
        manter_list = []
        for g_time, group in combined_df.groupby('time_gtfs', dropna=False):
            if pd.isna(g_time):
                # Se time_gtfs é nulo, mantém todos
                for idx in group.index:
                    manter_list.append((idx, True))
                continue
                
            min_diff = group['diff'].min()
            first_min = False
            for idx, row in group.iterrows():
                if pd.isna(row['diff']):
                    manter_list.append((idx, True))
                elif row['diff'] == min_diff and not first_min:
                    manter_list.append((idx, True))
                    first_min = True  # Garante que duplicados do mesmo min_diff sejam descartados (!duplicated)
                else:
                    manter_list.append((idx, False))
                    
        manter_dict = dict(manter_list)
        combined_df['manter'] = combined_df.index.map(manter_dict)
        
        # Zera time_gtfs para os registros que não devem ser mantidos
        combined_df.loc[~combined_df['manter'], 'time_gtfs'] = np.nan
        combined_df.loc[~combined_df['manter'], 'interval_gtfs'] = np.nan
        
    else:
        # Em R:
        # combined_df <- combined_df %>%
        #   mutate(diff = abs(difftime(time_gtfs, time_user))) %>%
        #   group_by(time_user) %>%
        #   mutate(
        #     manter_user = diff == min(diff) & !duplicated(diff),
        #     time_user = if_else(manter_user | is.na(diff), time_user, as.POSIXct(NA))
        #   ) %>% ungroup() %>%
        #   group_by(time_gtfs) %>%
        #   mutate(
        #     manter_gtfs = diff == min(diff) & !duplicated(diff),
        #     time_gtfs = if_else(manter_gtfs | is.na(diff), time_gtfs, as.POSIXct(NA))
        #   ) %>% ungroup()
        combined_df['diff'] = (combined_df['time_gtfs'] - combined_df['time_user']).abs()
        
        # Filtro pelo lado do Usuário
        manter_user_list = []
        for u_time, group in combined_df.groupby('time_user', dropna=False):
            if pd.isna(u_time):
                for idx in group.index:
                    manter_user_list.append((idx, True))
                continue
            min_diff = group['diff'].min()
            first_min = False
            for idx, row in group.iterrows():
                if pd.isna(row['diff']):
                    manter_user_list.append((idx, True))
                elif row['diff'] == min_diff and not first_min:
                    manter_user_list.append((idx, True))
                    first_min = True
                else:
                    manter_user_list.append((idx, False))
        manter_user_dict = dict(manter_user_list)
        combined_df['manter_user'] = combined_df.index.map(manter_user_dict)
        
        combined_df.loc[~combined_df['manter_user'], 'time_user'] = np.nan
        combined_df.loc[~combined_df['manter_user'], 'interval_user'] = np.nan
        # Recalcula diff após zerar
        combined_df['diff'] = (combined_df['time_gtfs'] - combined_df['time_user']).abs()
        
        # Filtro pelo lado do GTFS
        manter_gtfs_list = []
        for g_time, group in combined_df.groupby('time_gtfs', dropna=False):
            if pd.isna(g_time):
                for idx in group.index:
                    manter_gtfs_list.append((idx, True))
                continue
            min_diff = group['diff'].min()
            first_min = False
            for idx, row in group.iterrows():
                if pd.isna(row['diff']):
                    manter_gtfs_list.append((idx, True))
                elif row['diff'] == min_diff and not first_min:
                    manter_gtfs_list.append((idx, True))
                    first_min = True
                else:
                    manter_gtfs_list.append((idx, False))
        manter_gtfs_dict = dict(manter_gtfs_list)
        combined_df['manter_gtfs'] = combined_df.index.map(manter_gtfs_dict)
        
        combined_df.loc[~combined_df['manter_gtfs'], 'time_gtfs'] = np.nan
        combined_df.loc[~combined_df['manter_gtfs'], 'interval_gtfs'] = np.nan

    # 7. Regra final de comparação dos intervalos
    def get_comparison_arrow(row):
        g_time = row['time_gtfs']
        u_time = row['time_user']
        g_int = row['interval_gtfs']
        u_int = row['interval_user']
        
        if pd.isna(g_time) or pd.isna(u_time) or pd.isna(g_int) or pd.isna(u_int):
            return "-"
            
        if u_int > g_int:
            return "↑"
        elif u_int < g_int:
            return "↓"
        else:
            return "="
            
    combined_df['comparison'] = combined_df.apply(get_comparison_arrow, axis=1)
    
    # Limpa colunas auxiliares e ordena
    # No R, ordena pela coluna time_gtfs final
    # Se time_gtfs for NA, ele se baseia em time_user
    combined_df['order_key'] = combined_df['time_gtfs'].fillna(combined_df['time_user'])
    combined_df = combined_df.sort_values(by='order_key').reset_index(drop=True)
    
    return combined_df[['time_gtfs', 'time_user', 'interval_gtfs', 'interval_user', 'comparison']]

def build_summary_by_period(gtfs_seconds: list[int], user_seconds: list[int]) -> pd.DataFrame:
    """
    Gera a tabela resumo de contagem de partidas por faixas horárias.
    Replica a lógica da função output$summary_table do R.
    """
    # Converte segundos para horas decimais
    gtfs_hours = [float(s) / 3600.0 for s in gtfs_seconds]
    user_hours = [float(s) / 3600.0 for s in user_seconds]
    
    # Cria faixas horárias (labels)
    # O R usa cut() com limites 'breaks' fechados à esquerda (right=FALSE, include.lowest=TRUE)
    # Breaks: [0, 1, 2, 3, 4, 5, 6, 9, 12, 15, 18, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
    # Labels: TIME_PERIODS
    
    def count_by_bins(hours: list[float]) -> list[int]:
        counts = [0] * len(TIME_PERIODS)
        for h in hours:
            for idx in range(len(BREAKS) - 1):
                lower = BREAKS[idx]
                upper = BREAKS[idx+1]
                # Para o último intervalo, inclui o limite superior.
                # Para os outros, é fechado à esquerda e aberto à direita.
                is_in = False
                if idx == len(BREAKS) - 2:
                    is_in = (lower <= h <= upper)
                else:
                    is_in = (lower <= h < upper)
                    
                if is_in:
                    counts[idx] += 1
                    break
        return counts
        
    gtfs_counts = count_by_bins(gtfs_hours)
    user_counts = count_by_bins(user_hours)
    
    # Cria DataFrame com as contagens
    summary_df = pd.DataFrame({
        'Faixa': TIME_PERIODS,
        'Partidas GTFS': gtfs_counts,
        'Partidas Propostas': user_counts
    })
    
    # Cria a linha do total
    total_row = pd.DataFrame([{
        'Faixa': 'Total',
        'Partidas GTFS': sum(gtfs_counts),
        'Partidas Propostas': sum(user_counts)
    }])
    
    return pd.concat([summary_df, total_row], ignore_index=True)
