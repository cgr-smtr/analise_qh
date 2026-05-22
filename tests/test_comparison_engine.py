import pytest
import pandas as pd
import numpy as np
from app.comparison_engine import (
    _round_to_minute,
    _find_nearest,
    compare_schedules,
    build_summary_by_period
)

def test_helper_functions():
    assert _round_to_minute(60) == 60
    assert _round_to_minute(89) == 60
    assert _round_to_minute(90) == 120
    assert _round_to_minute(119) == 120
    
    assert _find_nearest(100, [10, 50, 110, 200]) == 110
    assert _find_nearest(30, [10, 50, 110]) == 10  # Empate, 30-10 = 20, 50-30 = 20. Min pega a primeira ocorrência do min.

def test_compare_schedules_identical():
    # Duas partidas idênticas: 06:00:00 e 06:15:00
    gtfs_schedule = pd.DataFrame({
        'Partida': [1, 2],
        'Horário': ['06:00:00', '06:15:00'],
        'hora': [6, 6],
        'Intervalo': [np.nan, 15.0]
    })
    user_seconds = [6*3600, 6*3600 + 15*60]
    
    res = compare_schedules(gtfs_schedule, user_seconds)
    assert len(res) == 2
    
    # Linha 1: 06:00
    assert res.iloc[0]['time_gtfs'] == 6*3600
    assert res.iloc[0]['time_user'] == 6*3600
    assert np.isnan(res.iloc[0]['interval_gtfs'])
    assert np.isnan(res.iloc[0]['interval_user'])
    assert res.iloc[0]['comparison'] == "-"
    
    # Linha 2: 06:15
    assert res.iloc[1]['time_gtfs'] == 6*3600 + 15*60
    assert res.iloc[1]['time_user'] == 6*3600 + 15*60
    assert res.iloc[1]['interval_gtfs'] == 15.0
    assert res.iloc[1]['interval_user'] == 15.0
    assert res.iloc[1]['comparison'] == "="

def test_compare_schedules_user_more():
    # GTFS: 06:00
    # Usuário: 06:00, 06:10
    gtfs_schedule = pd.DataFrame({
        'Partida': [1],
        'Horário': ['06:00:00'],
        'hora': [6],
        'Intervalo': [np.nan]
    })
    user_seconds = [6*3600, 6*3600 + 10*60]
    
    res = compare_schedules(gtfs_schedule, user_seconds)
    assert len(res) == 2
    
    # Ordenado por order_key (time_gtfs ou time_user)
    # Linha 1: 06:00 vs 06:00
    assert res.iloc[0]['time_gtfs'] == 6*3600
    assert res.iloc[0]['time_user'] == 6*3600
    
    # Linha 2: Sem par GTFS vs 06:10
    assert np.isnan(res.iloc[1]['time_gtfs'])
    assert res.iloc[1]['time_user'] == 6*3600 + 10*60
    assert res.iloc[1]['comparison'] == "-"

def test_compare_schedules_gtfs_more():
    # GTFS: 06:00, 06:15
    # Usuário: 06:00
    gtfs_schedule = pd.DataFrame({
        'Partida': [1, 2],
        'Horário': ['06:00:00', '06:15:00'],
        'hora': [6, 6],
        'Intervalo': [np.nan, 15.0]
    })
    user_seconds = [6*3600]
    
    res = compare_schedules(gtfs_schedule, user_seconds)
    assert len(res) == 2
    
    # Linha 1: 06:00 vs 06:00
    assert res.iloc[0]['time_gtfs'] == 6*3600
    assert res.iloc[0]['time_user'] == 6*3600
    
    # Linha 2: 06:15 vs Sem par Usuário
    assert res.iloc[1]['time_gtfs'] == 6*3600 + 15*60
    assert np.isnan(res.iloc[1]['time_user'])
    assert res.iloc[1]['comparison'] == "-"

def test_build_summary_by_period():
    # Partidas GTFS: 00:30 (faixa 0), 06:15 (faixa 6), 08:30 (faixa 6)
    # Partidas Usuário: 06:20 (faixa 6), 29:30 (faixa 29)
    gtfs_seconds = [1800, 6*3600 + 15*60, 8*3600 + 30*60]
    user_seconds = [6*3600 + 20*60, 29*3600 + 30*60]
    
    summary = build_summary_by_period(gtfs_seconds, user_seconds)
    
    # Total deve ser a última linha
    assert summary.iloc[-1]['Faixa'] == "Total"
    assert summary.iloc[-1]['Partidas GTFS'] == 3
    assert summary.iloc[-1]['Partidas Propostas'] == 2
    
    # Verifica faixas específicas
    row_0 = summary[summary['Faixa'] == "00:00-00:59"]
    assert row_0['Partidas GTFS'].values[0] == 1
    assert row_0['Partidas Propostas'].values[0] == 0
    
    row_6 = summary[summary['Faixa'] == "06:00-08:59"]
    assert row_6['Partidas GTFS'].values[0] == 2
    assert row_6['Partidas Propostas'].values[0] == 1
    
    row_29 = summary[summary['Faixa'] == "29:00-29:59"]
    assert row_29['Partidas GTFS'].values[0] == 0
    assert row_29['Partidas Propostas'].values[0] == 1
