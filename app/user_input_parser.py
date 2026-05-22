import re
import pandas as pd
import numpy as np
from app.schedule_extractor import _seconds_to_time_str

def parse_user_times(text: str) -> list[int] | None:
    """
    Realiza o parse e a validação do texto de horários colado pelo usuário.
    Espera um horário por linha no formato HH:MM:SS.
    Retorna uma lista de segundos desde a meia-noite correspondente a cada horário,
    tratando a transição de meia-noite (adicionando 24 horas/86400s quando o horário diminui).
    Caso algum horário seja inválido, retorna None.
    """
    if not text or not text.strip():
        return None
        
    # Divide o texto em linhas, remove espaços e descarta linhas vazias
    lines = [line.strip() for line in text.split('\n')]
    lines = [line for line in lines if line != ""]
    
    if not lines:
        return None
        
    # Regex para validar o formato HH:MM:SS. Aceita horas de 0 a 29 para acomodar horários estendidos
    regex = re.compile(r"^([0-2]?[0-9]):[0-5][0-9]:[0-5][0-9]$")
    
    seconds_list = []
    for idx, line in enumerate(lines):
        if not regex.match(line):
            return None
            
        try:
            parts = line.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            
            sec = hours * 3600 + minutes * 60 + seconds
            seconds_list.append(sec)
        except (ValueError, IndexError):
            return None
            
    # Tratamento de rollover (transição de meia-noite)
    # Se um horário subsequente for menor que o anterior, adicionamos 24h (86400 segundos)
    # O loop faz isso sequencialmente de forma acumulada
    for i in range(1, len(seconds_list)):
        while seconds_list[i] < seconds_list[i - 1]:
            seconds_list[i] += 86400
            
    return seconds_list

def build_user_schedule_df(seconds: list[int]) -> pd.DataFrame:
    """
    Cria um DataFrame contendo as partidas propostas do usuário de forma legível.
    Retorna colunas: Partida (número sequencial), Horário (HH:MM:SS), hora (inteiro), Intervalo (minutos).
    """
    if not seconds:
        return pd.DataFrame(columns=['Partida', 'Horário', 'hora', 'Intervalo'])
        
    df = pd.DataFrame({
        'departure_seconds': seconds
    })
    
    # Adiciona metadados
    df['Partida'] = df.index + 1
    df['Horário'] = df['departure_seconds'].apply(_seconds_to_time_str)
    df['hora'] = df['departure_seconds'] // 3600
    
    # Calcula intervalo em minutos
    df['Intervalo'] = df['departure_seconds'].diff() / 60.0
    
    return df[['Partida', 'Horário', 'hora', 'Intervalo']]

def build_frequencies_from_user(
    seconds: list[int],
    route_short_name: str,
    headsign: str
) -> pd.DataFrame:
    """
    Agrupa horários de partida propostos em linhas de frequências consecutivas e idênticas.
    Replica a lógica complexa de agrupamento da função user_schedule_processed() do R.
    Retorna colunas: trip_id, trip_headsign, trip_short_name, start_time, end_time, headway_secs.
    """
    cols = ['trip_id', 'trip_headsign', 'trip_short_name', 'start_time', 'end_time', 'headway_secs']
    n = len(seconds)
    if n == 0:
        return pd.DataFrame(columns=cols)
        
    # Se houver apenas 1 partida, não há headway propriamente dito. Supomos headway de 0.
    if n == 1:
        return pd.DataFrame([{
            'trip_id': '',
            'trip_headsign': headsign,
            'trip_short_name': route_short_name,
            'start_time': _seconds_to_time_str(seconds[0]),
            'end_time': _seconds_to_time_str(seconds[0]),
            'headway_secs': 0
        }], columns=cols)
        
    # Calcula headway_secs para cada partida
    # headway_secs da partida i é o tempo até a partida i+1
    headways = []
    for i in range(n - 1):
        headways.append(seconds[i+1] - seconds[i])
        
    # A última partida repete o headway da anterior (comportamento do R via lag(headway_secs))
    headways.append(headways[-1])
    
    # Agrupa intervalos consecutivos com o mesmo headway
    intervals = []
    curr_start = seconds[0]
    curr_headway = headways[0]
    curr_end = seconds[0] + curr_headway
    
    for i in range(1, n):
        if headways[i] == curr_headway:
            # Continua no mesmo bloco de headway
            curr_end = seconds[i] + headways[i]
        else:
            # Fecha o bloco atual e inicia um novo
            intervals.append({
                'start_time': curr_start,
                'end_time': curr_end,
                'headway_secs': curr_headway
            })
            curr_start = seconds[i]
            curr_headway = headways[i]
            curr_end = seconds[i] + curr_headway
            
    # Adiciona o último bloco pendente
    intervals.append({
        'start_time': curr_start,
        'end_time': curr_end,
        'headway_secs': curr_headway
    })
    
    # Cria o DataFrame e formata os tempos
    res_rows = []
    for item in intervals:
        res_rows.append({
            'trip_id': '',
            'trip_headsign': headsign,
            'trip_short_name': route_short_name,
            'start_time': _seconds_to_time_str(item['start_time']),
            'end_time': _seconds_to_time_str(item['end_time']),
            'headway_secs': int(item['headway_secs'])
        })
        
    return pd.DataFrame(res_rows, columns=cols)
