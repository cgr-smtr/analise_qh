import pytest
import pandas as pd
from app.config import GTFSMode, ExportFormat
from app.export_handler import (
    get_export_format,
    sanitize_filename,
    build_export_filename,
    export_gtfs_as_csv,
    export_gtfs_as_txt,
    export_user_as_csv,
    export_user_as_txt
)
from app.user_input_parser import parse_user_times

def test_export_format_determination():
    assert get_export_format(GTFSMode.FREQUENCIES) == ExportFormat.CSV
    assert get_export_format(GTFSMode.TIMETABLE) == ExportFormat.TXT

def test_sanitize_filename():
    assert sanitize_filename("123 - VAZIO") == "123_VAZIO"
    assert sanitize_filename("Terminal: Alvorada / Galeão") == "Terminal_Alvorada_Galeão"
    assert sanitize_filename("linha*teste?outra") == "linhatesteoutra"
    assert sanitize_filename("") == "indefinido"

def test_build_export_filename():
    fn_csv = build_export_filename("horarios", "123 - VAZIO", "Term. Alvorada", "SABADO", ExportFormat.CSV)
    assert fn_csv == "horarios_123_VAZIO_Term._Alvorada_SABADO.csv"
    
    fn_txt = build_export_filename("horarios", "456", "Centro", "DIA UTIL", ExportFormat.TXT)
    assert fn_txt == "horarios_456_Centro_DIA_UTIL.txt"

def test_export_gtfs_as_txt():
    # DataFrame do GTFS schedule
    schedule_df = pd.DataFrame({
        'Partida': [1, 2, 3],
        'Horário': ['06:00:00', '06:15:00', '07:00:00'],
        'hora': [6, 6, 7],
        'Intervalo': [None, 15.0, 45.0]
    })
    
    txt_content = export_gtfs_as_txt(schedule_df)
    assert txt_content == "06:00:00\n06:15:00\n07:00:00\n"

def test_export_gtfs_as_csv():
    # Duas faixas com headway de 10 min de 06:00 a 06:20
    # E de 20 min de 06:20 a 07:00
    # Partidas: 06:00, 06:10, 06:20, 06:40, 07:00
    schedule_df = pd.DataFrame({
        'Partida': [1, 2, 3, 4, 5],
        'Horário': ['06:00:00', '06:10:00', '06:20:00', '06:40:00', '07:00:00'],
        'hora': [6, 6, 6, 6, 7],
        'Intervalo': [None, 10.0, 10.0, 20.0, 20.0]
    })
    
    csv_content = export_gtfs_as_csv(schedule_df, "123", "Terminal")
    # A primeira linha deve ser o cabeçalho
    lines = csv_content.strip().split('\n')
    assert lines[0] == "trip_id,trip_headsign,trip_short_name,start_time,end_time,headway_secs"
    
    # Faixa 1: 06:00:00 a 06:20:00 com headway 600
    # Faixa 2: 06:20:00 a 07:20:00 com headway 1200
    assert lines[1] == ",Terminal,123,06:00:00,06:20:00,600"
    assert lines[2] == ",Terminal,123,06:20:00,07:20:00,1200"

def test_export_user_as_txt_roundtrip():
    # Segundos do usuário
    user_seconds = [6*3600, 6*3600 + 15*60, 7*3600]
    
    # Exporta para TXT
    txt_content = export_user_as_txt(user_seconds)
    assert txt_content == "06:00:00\n06:15:00\n07:00:00\n"
    
    # Simula colagem de volta (importação / parse)
    imported_seconds = parse_user_times(txt_content)
    
    # Devem ser iguais
    assert imported_seconds == user_seconds

def test_export_user_as_csv():
    # Segundos do usuário correspondentes a 06:00, 06:10, 06:20, 06:40, 07:00
    # Com duplicatas e desordenado para testar ordenação e remoção de duplicados
    user_seconds = [22800, 21600, 22200, 24000, 22200, 25200]
    
    csv_content = export_user_as_csv(user_seconds, "123", "Terminal")
    lines = csv_content.strip().split('\n')
    assert lines[0] == "trip_id,trip_headsign,trip_short_name,start_time,end_time,headway_secs"
    
    # Faixa 1: 06:00:00 a 06:20:00 com headway 600
    # Faixa 2: 06:20:00 a 07:20:00 com headway 1200
    assert lines[1] == ",Terminal,123,06:00:00,06:20:00,600"
    assert lines[2] == ",Terminal,123,06:20:00,07:20:00,1200"
