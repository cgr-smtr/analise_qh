import pytest
import pandas as pd
from app.ui_components import (
    render_schedule_table,
    render_comparison_table,
    render_summary_table
)

def test_render_schedule_table_cleaning():
    df = pd.DataFrame([
        {"Partida": 1, "Horário": "04:00:00", "hora": 4, "Intervalo": 20.0}
    ])
    html = render_schedule_table(df)
    
    # Verifica que nenhuma linha do HTML retornado começa com 4 ou mais espaços
    for line in html.splitlines():
        assert not line.startswith("    "), f"A linha '{line}' contém indentação excessiva que pode quebrar no Streamlit."
        
def test_render_comparison_table_cleaning():
    df = pd.DataFrame([
        {
            "time_gtfs": 14400,
            "time_user": 14400,
            "interval_gtfs": 20.0,
            "interval_user": 20.0,
            "comparison": "="
        }
    ])
    html = render_comparison_table(df)
    
    # Verifica que nenhuma linha do HTML retornado começa com 4 ou mais espaços
    for line in html.splitlines():
        assert not line.startswith("    "), f"A linha '{line}' contém indentação excessiva que pode quebrar no Streamlit."

def test_render_summary_table_cleaning():
    df = pd.DataFrame([
        {"Faixa": "04:00", "Partidas GTFS": 2, "Partidas Propostas": 2}
    ])
    html = render_summary_table(df)
    
    # Verifica que nenhuma linha do HTML retornado começa com 4 ou mais espaços
    for line in html.splitlines():
        assert not line.startswith("    "), f"A linha '{line}' contém indentação excessiva que pode quebrar no Streamlit."
