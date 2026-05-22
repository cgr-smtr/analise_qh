import pytest
import pandas as pd
import numpy as np
from app.user_input_parser import (
    parse_user_times,
    build_user_schedule_df,
    build_frequencies_from_user
)

def test_parse_user_times_valid():
    # Caso básico: horários bem formatados e em ordem crescente
    text = "06:00:00\n06:10:00\n06:20:00"
    res = parse_user_times(text)
    assert res == [6*3600, 6*3600 + 10*60, 6*3600 + 20*60]
    
    # Teste de rollover (transição de meia-noite)
    # 23:50:00, 00:10:00 -> O segundo deve receber +86400s
    text_rollover = "23:50:00\n00:10:00"
    res_rollover = parse_user_times(text_rollover)
    assert res_rollover == [23*3600 + 50*60, (0*3600 + 10*60) + 86400]
    
    # Teste de rollover duplo (cruza meia-noite duas vezes)
    # 23:00:00, 00:00:00, 23:00:00 (que seria do dia seguinte, logo +86400, e o outro do outro dia, logo +2*86400)
    text_rollover_2 = "23:00:00\n00:00:00\n23:00:00"
    # 1º: 23*3600 = 82800
    # 2º: 0 -> menor que anterior -> +86400
    # 3º: 23*3600 = 82800 -> menor que anterior (86400) -> +86400 = 169200
    res_rollover_2 = parse_user_times(text_rollover_2)
    assert res_rollover_2 == [82800, 86400, 169200]

def test_parse_user_times_invalid():
    # Entradas vazias ou nulas
    assert parse_user_times("") is None
    assert parse_user_times(None) is None
    assert parse_user_times("   \n  \n") is None
    
    # Entradas mal formatadas
    assert parse_user_times("06:00") is None          # Sem segundos
    assert parse_user_times("06:00:00\ninvalido") is None # Linha inválida
    assert parse_user_times("26:00:00") is not None   # Válido pois aceitamos horas de 0 a 29
    assert parse_user_times("30:00:00") is None       # Inválido
    assert parse_user_times("06:60:00") is None       # Minutos inválidos
    assert parse_user_times("06:00:60") is None       # Segundos inválidos

def test_build_user_schedule_df():
    # Entrada com 3 partidas (06:00:00, 06:15:00, 07:00:00)
    seconds = [6*3600, 6*3600 + 15*60, 7*3600]
    df = build_user_schedule_df(seconds)
    
    assert len(df) == 3
    assert list(df['Partida']) == [1, 2, 3]
    assert list(df['Horário']) == ["06:00:00", "06:15:00", "07:00:00"]
    assert list(df['hora']) == [6, 6, 7]
    
    # Intervalos:
    # 1º -> NaN
    # 2º -> 15 min
    # 3º -> 45 min
    assert np.isnan(df['Intervalo'].iloc[0])
    assert df['Intervalo'].iloc[1] == 15.0
    assert df['Intervalo'].iloc[2] == 45.0

def test_build_frequencies_from_user():
    # Cenário de frequências agrupadas
    # Partidas: 06:00, 06:10, 06:20, 06:30, 06:50, 07:10
    # Headways esperados:
    # 06:00 -> 06:10 (600s)
    # 06:10 -> 06:20 (600s)
    # 06:20 -> 06:30 (600s) -> agrupado como 06:00 a 06:30 com headway 600s
    # 06:30 -> 06:50 (1200s)
    # 06:50 -> 07:10 (1200s)
    # 07:10 -> repete o penúltimo (1200s) -> agrupado como 06:30 a 07:30 com headway 1200s
    seconds = [
        6*3600,
        6*3600 + 10*60,
        6*3600 + 20*60,
        6*3600 + 30*60,
        6*3600 + 50*60,
        7*3600 + 10*60
    ]
    
    df_freq = build_frequencies_from_user(seconds, "123", "Terminal Alvorada")
    
    assert len(df_freq) == 2
    
    # Linha 1
    assert df_freq.iloc[0]['trip_short_name'] == "123"
    assert df_freq.iloc[0]['trip_headsign'] == "Terminal Alvorada"
    assert df_freq.iloc[0]['start_time'] == "06:00:00"
    assert df_freq.iloc[0]['end_time'] == "06:30:00"
    assert df_freq.iloc[0]['headway_secs'] == 600
    
    # Linha 2
    assert df_freq.iloc[1]['trip_short_name'] == "123"
    assert df_freq.iloc[1]['trip_headsign'] == "Terminal Alvorada"
    assert df_freq.iloc[1]['start_time'] == "06:30:00"
    assert df_freq.iloc[1]['end_time'] == "07:30:00"
    assert df_freq.iloc[1]['headway_secs'] == 1200
