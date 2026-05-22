import pytest
import pandas as pd
import numpy as np
from app.config import GTFSMode
from app.schedule_extractor import (
    _time_str_to_seconds,
    _seconds_to_time_str,
    extract_schedule,
    add_schedule_metadata
)

class MockFeed:
    def __init__(self, frequencies=None, stop_times=None):
        self.frequencies = frequencies
        self.stop_times = stop_times

def test_time_conversions():
    # Teste de strings normais
    assert _time_str_to_seconds("01:00:00") == 3600
    assert _time_str_to_seconds("00:30:00") == 1800
    assert _time_str_to_seconds("00:00:15") == 15
    
    # Teste de strings superiores a 24h
    assert _time_str_to_seconds("25:30:00") == 25 * 3600 + 30 * 60
    
    # Testes reversos
    assert _seconds_to_time_str(3600) == "01:00:00"
    assert _seconds_to_time_str(1800) == "00:30:00"
    assert _seconds_to_time_str(25 * 3600 + 30 * 60) == "25:30:00"
    
    # Teste de entradas inválidas
    assert _time_str_to_seconds("") == 0
    assert _time_str_to_seconds(None) == 0
    assert _seconds_to_time_str(-1) == "00:00:00"

def test_extract_frequencies_basic():
    # Define DataFrame de frequências mockado
    frequencies_data = pd.DataFrame({
        'trip_id': ['trip1', 'trip2'],
        'start_time': ['06:00:00', '08:00:00'],
        'end_time': ['07:00:00', '09:00:00'],
        'headway_secs': [600, 1200]  # 10 min e 20 min
    })
    feed = MockFeed(frequencies=frequencies_data)
    
    # Extrai horário para trip1
    # De 06:00 a 07:00 com headway 600s (10 min) -> 06:00, 06:10, 06:20, 06:30, 06:40, 06:50 (6 partidas)
    res = extract_schedule(feed, ['trip1'], GTFSMode.FREQUENCIES)
    assert len(res) == 6
    assert list(res['departure_time']) == [
        '06:00:00', '06:10:00', '06:20:00', '06:30:00', '06:40:00', '06:50:00'
    ]

def test_extract_frequencies_deduplication():
    # Frequências com janelas que se sobrepõem gerando mesmos horários
    frequencies_data = pd.DataFrame({
        'trip_id': ['trip1', 'trip1'],
        'start_time': ['06:00:00', '06:20:00'],
        'end_time': ['07:00:00', '07:20:00'],
        'headway_secs': [1200, 1200]  # 20 min
    })
    # trip1 no intervalo 1: 06:00, 06:20, 06:40
    # trip1 no intervalo 2: 06:20, 06:40, 07:00
    # Combinados sem duplicados: 06:00, 06:20, 06:40, 07:00
    feed = MockFeed(frequencies=frequencies_data)
    
    res = extract_schedule(feed, ['trip1'], GTFSMode.FREQUENCIES)
    assert len(res) == 4
    assert list(res['departure_time']) == ['06:00:00', '06:20:00', '06:40:00', '07:00:00']

def test_extract_timetable_basic():
    # Define DataFrame de stop_times mockado
    stop_times_data = pd.DataFrame({
        'trip_id': ['trip1', 'trip1', 'trip2', 'trip2', 'trip3'],
        'arrival_time': ['06:00:00', '06:15:00', '07:00:00', '07:30:00', '05:30:00'],
        'departure_time': ['06:00:00', '06:15:00', '07:02:00', '07:30:00', '05:30:00'],
        'stop_id': ['stopA', 'stopB', 'stopA', 'stopB', 'stopA'],
        'stop_sequence': [1, 2, 1, 2, 1]
    })
    feed = MockFeed(stop_times=stop_times_data)
    
    # Extrai horários do 1º stop das trips ['trip1', 'trip2']
    # trip1: stop_sequence=1 -> departure_time = 06:00:00
    # trip2: stop_sequence=1 -> departure_time = 07:02:00
    res = extract_schedule(feed, ['trip1', 'trip2'], GTFSMode.TIMETABLE)
    assert len(res) == 2
    assert list(res['departure_time']) == ['06:00:00', '07:02:00']
    
    # Se extrair todas as trips
    res_all = extract_schedule(feed, ['trip1', 'trip2', 'trip3'], GTFSMode.TIMETABLE)
    # Devem ser ordenados: 05:30:00 (trip3), 06:00:00 (trip1), 07:02:00 (trip2)
    assert list(res_all['departure_time']) == ['05:30:00', '06:00:00', '07:02:00']

def test_add_schedule_metadata():
    df = pd.DataFrame({'departure_time': ['06:00:00', '06:15:00', '07:00:00']})
    res = add_schedule_metadata(df)
    
    assert list(res['Partida']) == [1, 2, 3]
    assert list(res['Horário']) == ['06:00:00', '06:15:00', '07:00:00']
    assert list(res['hora']) == [6, 6, 7]
    
    # Intervalos:
    # 06:00:00 -> primeiro -> NaN
    # 06:15:00 - 06:00:00 -> 15 min
    # 07:00:00 - 06:15:00 -> 45 min
    assert np.isnan(res['Intervalo'].iloc[0])
    assert res['Intervalo'].iloc[1] == 15.0
    assert res['Intervalo'].iloc[2] == 45.0
