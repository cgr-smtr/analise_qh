import pandas as pd
import numpy as np
import gtfs_kit as gk
from app.config import GTFSMode

def _time_str_to_seconds(time_str: str) -> int:
    """
    Converte uma string no formato HH:MM:SS para segundos.
    Suporta horas superiores a 24 (como 25:30:00).
    """
    if not isinstance(time_str, str) or not time_str:
        return 0
    try:
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2]) if len(parts) > 2 else 0
        return hours * 3600 + minutes * 60 + seconds
    except (ValueError, IndexError):
        return 0

def _seconds_to_time_str(seconds: int) -> str:
    """
    Converte segundos de volta para o formato de string HH:MM:SS.
    Preserva valores de hora superiores a 24.
    """
    if pd.isna(seconds) or seconds < 0:
        return "00:00:00"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def _extract_from_frequencies(feed: gk.Feed, trip_ids: list[str]) -> pd.DataFrame:
    """
    Gera horários individuais de partida com base em frequencies.txt.
    Replica a lógica da função get_gtfs_schedule() em R.
    """
    if feed.frequencies is not None and not feed.frequencies.empty:
        # Filtra frequências pelos trip_ids
        freq_df = feed.frequencies[feed.frequencies['trip_id'].isin(trip_ids)].copy()
        if freq_df.empty:
            return pd.DataFrame(columns=['departure_time'])
            
        # Converte horários de início e fim para string
        freq_df['start_time'] = freq_df['start_time'].astype(str)
        freq_df['end_time'] = freq_df['end_time'].astype(str)
        
        # Converte para segundos
        freq_df['start_seconds'] = freq_df['start_time'].apply(_time_str_to_seconds)
        freq_df['end_seconds'] = freq_df['end_time'].apply(_time_str_to_seconds)
        freq_df['headway_secs'] = freq_df['headway_secs'].astype(int)
        
        # Filtra valores válidos e com sentido lógico
        freq_df = freq_df[
            (freq_df['start_seconds'] >= 0) & 
            (freq_df['end_seconds'] > freq_df['start_seconds']) & 
            (freq_df['headway_secs'] > 0)
        ]
        
        if freq_df.empty:
            return pd.DataFrame(columns=['departure_time'])
            
        departure_times_all = []
        
        # Ordena por start_seconds
        freq_df = freq_df.sort_values(by='start_seconds')
        
        for _, row in freq_df.iterrows():
            start = int(row['start_seconds'])
            end = int(row['end_seconds'])
            step = int(row['headway_secs'])
            
            # Conforme o R: seq(start_seconds, end_seconds - headway_secs, by = headway_secs)
            # Em python, range(start, end, step) vai de start até o maior valor < end de step em step.
            # No R, vai de start até end - step inclusive.
            # Ex: start=3600, end=7200, step=1200.
            # No R: seq(3600, 7200-1200, 1200) -> 3600, 4800, 6000.
            # No Python: range(3600, 7200, 1200) -> 3600, 4800, 6000.
            # Logo, range(start, end, step) gera exatamente as mesmas partidas.
            times = list(range(start, end, step))
            departure_times_all.extend(times)
            
        # Remove duplicados e ordena
        departure_times_all = sorted(list(set(departure_times_all)))
        
        # Converte de volta para string HH:MM:SS
        time_strings = [_seconds_to_time_str(t) for t in departure_times_all]
        
        return pd.DataFrame({'departure_time': time_strings})
        
    return pd.DataFrame(columns=['departure_time'])

def _extract_from_timetable(feed: gk.Feed, trip_ids: list[str]) -> pd.DataFrame:
    """
    Extrai os horários de partida para modo Timetable usando o primeiro stop
    (menor stop_sequence) de cada trip_id selecionado em stop_times.txt.
    """
    if feed.stop_times is not None and not feed.stop_times.empty:
        # Filtra stop_times pelos trip_ids
        st_df = feed.stop_times[feed.stop_times['trip_id'].isin(trip_ids)].copy()
        if st_df.empty:
            return pd.DataFrame(columns=['departure_time'])
            
        # Garante que stop_sequence é numérico
        st_df['stop_sequence'] = st_df['stop_sequence'].astype(int)
        
        # Para cada trip, pega o registro correspondente ao menor stop_sequence
        idx = st_df.groupby('trip_id')['stop_sequence'].idxmin()
        first_stops = st_df.loc[idx]
        
        # Pega as departure_times dessas partidas
        departure_times = first_stops['departure_time'].dropna().astype(str).tolist()
        
        # Converte para segundos para ordenar e limpar
        seconds = [_time_str_to_seconds(t) for t in departure_times]
        
        # Remove duplicados e ordena
        seconds_sorted = sorted(list(set(seconds)))
        
        # Reconverte para string
        time_strings = [_seconds_to_time_str(s) for s in seconds_sorted]
        
        return pd.DataFrame({'departure_time': time_strings})
        
    return pd.DataFrame(columns=['departure_time'])

def extract_schedule(feed: gk.Feed, trip_ids: list[str], mode: GTFSMode) -> pd.DataFrame:
    """
    Função principal que extrai o quadro de partidas com base no modo selecionado.
    Garante a mesma interface de retorno (DataFrame com coluna 'departure_time' HH:MM:SS).
    """
    if not trip_ids:
        return pd.DataFrame(columns=['departure_time'])
        
    if mode == GTFSMode.FREQUENCIES:
        return _extract_from_frequencies(feed, trip_ids)
    elif mode == GTFSMode.TIMETABLE:
        return _extract_from_timetable(feed, trip_ids)
    else:
        raise ValueError(f"Modo de operação inválido: {mode}")

def add_schedule_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona colunas de metadados: numero (1-indexed), hora (inteiro) e intervalo (minutos).
    Modifica o DataFrame ou retorna uma cópia com os dados preenchidos.
    """
    if df.empty or 'departure_time' not in df.columns:
        return pd.DataFrame(columns=['Partida', 'Horário', 'hora', 'Intervalo'])
        
    res_df = df.copy()
    
    # Ordena para garantir cálculos sequenciais corretos
    res_df['departure_seconds'] = res_df['departure_time'].apply(_time_str_to_seconds)
    res_df = res_df.sort_values(by='departure_seconds').reset_index(drop=True)
    
    # Número da partida (1-indexed)
    res_df['Partida'] = res_df.index + 1
    
    # Hora extraída dos primeiros dois dígitos da string (ex: "03" -> 3, "25" -> 25)
    res_df['hora'] = res_df['departure_time'].str.slice(0, 2).astype(int)
    
    # Calcula intervalo em minutos
    res_df['Intervalo'] = res_df['departure_seconds'].diff() / 60.0
    
    # Para a primeira partida, o intervalo é NaN (como no R)
    
    # Organiza e renomeia colunas para a saída
    res_df = res_df.rename(columns={'departure_time': 'Horário'})
    return res_df[['Partida', 'Horário', 'hora', 'Intervalo']]
