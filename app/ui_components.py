import pandas as pd
import numpy as np
from app.config import get_time_color, TIME_TO_HOUR, TIME_COLORS
from app.schedule_extractor import _seconds_to_time_str

def _styled_cell(text: str, bg_color: str = None, color: str = "#000000", bold: bool = False) -> str:
    """Gera uma célula HTML (div) com cor de fundo e estilo."""
    style_parts = []
    if bg_color:
        style_parts.append(f"background-color: {bg_color}")
        # Determina contraste simples (se a cor de fundo for muito escura, usa texto branco)
        # As cores do projeto são todas tons pastéis claros, então texto escuro funciona perfeitamente.
    if color:
        style_parts.append(f"color: {color}")
    if bold:
        style_parts.append("font-weight: bold")
    
    style_parts.append("padding: 6px 12px")
    style_parts.append("border-radius: 4px")
    style_parts.append("text-align: center")
    style_parts.append("font-family: monospace")
    
    style_str = "; ".join(style_parts)
    return f'<div style="{style_str}">{text}</div>'

def _clean_html(html_str: str) -> str:
    """Remove espaços em branco no início e fim de cada linha para evitar
    que o markdown do Streamlit interprete como bloco de código."""
    return "\n".join(line.strip() for line in html_str.splitlines())

def _get_table_styles() -> str:
    """Retorna o bloco de estilo CSS para as tabelas adaptáveis ao tema (claro/escuro)."""
    return """
    <style>
      .custom-table {
        width: 100%;
        border-collapse: collapse;
        border: 1px solid rgba(128, 128, 128, 0.2);
        font-size: 14px;
        color: var(--text-color);
        margin-bottom: 10px;
      }
      .custom-table th {
        background-color: rgba(128, 128, 128, 0.15);
        border-bottom: 2px solid rgba(128, 128, 128, 0.3);
        padding: 10px;
        text-align: center;
        font-weight: 600;
        color: var(--text-color) !important;
      }
      .custom-table td {
        padding: 8px;
        text-align: center;
        border-bottom: 1px solid rgba(128, 128, 128, 0.15);
        color: var(--text-color);
      }
      .custom-table tbody tr:hover {
        background-color: rgba(128, 128, 128, 0.05);
      }
      .custom-table-comp {
        font-size: 13px;
      }
      .custom-table-comp td {
        padding: 6px;
      }
      .total-row {
        background-color: rgba(128, 128, 128, 0.25) !important;
        font-weight: bold;
        border-top: 2px solid rgba(128, 128, 128, 0.4);
      }
    </style>
    """

def render_schedule_table(df: pd.DataFrame) -> str:
    """
    Gera o HTML para a tabela de horários (do GTFS ou Proposta).
    Campos esperados: Partida, Horário, hora, Intervalo.
    """
    if df.empty:
        return "<p style='text-align: center; color: #888;'>Nenhum horário disponível.</p>"
        
    html = _get_table_styles() + """
    <table class="custom-table">
      <thead>
        <tr>
          <th>Partida</th>
          <th>Horário</th>
          <th>Intervalo (min)</th>
        </tr>
      </thead>
      <tbody>
    """
    
    for _, row in df.iterrows():
        partida = int(row['Partida'])
        horario = row['Horário']
        hora = int(row['hora'])
        intervalo = row['Intervalo']
        
        bg_color = get_time_color(hora)
        styled_time = _styled_cell(horario, bg_color=bg_color, bold=True)
        
        if pd.isna(intervalo):
            styled_interval = "-"
        else:
            styled_interval = f"{intervalo:.1f}"
            
        html += f"""
        <tr>
          <td style="font-family: monospace;">{partida}</td>
          <td>{styled_time}</td>
          <td style="font-family: monospace;">{styled_interval}</td>
        </tr>
        """
        
    html += "</tbody></table>"
    return _clean_html(html)

def render_comparison_table(df: pd.DataFrame) -> str:
    """
    Gera o HTML para a tabela de comparação.
    Campos esperados: time_gtfs, time_user, interval_gtfs, interval_user, comparison.
    """
    if df.empty:
        return "<p style='text-align: center; color: #888;'>Nenhuma comparação disponível.</p>"
        
    html = _get_table_styles() + """
    <table class="custom-table custom-table-comp">
      <thead>
        <tr>
          <th>Horário GTFS</th>
          <th>Horário Usuário</th>
          <th>Int. GTFS (min)</th>
          <th>Int. Usuário (min)</th>
          <th>Comparação</th>
        </tr>
      </thead>
      <tbody>
    """
    
    for _, row in df.iterrows():
        t_gtfs = row['time_gtfs']
        t_user = row['time_user']
        i_gtfs = row['interval_gtfs']
        i_user = row['interval_user']
        comp = row['comparison']
        
        # Formata Horário GTFS
        if pd.isna(t_gtfs):
            styled_gtfs_time = "-"
        else:
            time_str = _seconds_to_time_str(int(t_gtfs))
            hora = int(t_gtfs) // 3600
            styled_gtfs_time = _styled_cell(time_str, bg_color=get_time_color(hora), bold=True)
            
        # Formata Horário Usuário
        if pd.isna(t_user):
            styled_user_time = "-"
        else:
            time_str = _seconds_to_time_str(int(t_user))
            hora = int(t_user) // 3600
            styled_user_time = _styled_cell(time_str, bg_color=get_time_color(hora), bold=True)
            
        # Formata Intervalo GTFS
        val_i_gtfs = "-" if pd.isna(i_gtfs) or pd.isna(t_gtfs) else f"{i_gtfs:.1f}"
        
        # Formata Intervalo Usuário
        val_i_user = "-" if pd.isna(i_user) or pd.isna(t_user) else f"{i_user:.1f}"
        
        # Estilização da seta de comparação
        if comp == "↑":
            # Azul escuro ou Vermelho para aumento
            styled_comp = _styled_cell("↑ Aumentou", bg_color="#FFEBEE", color="#C62828", bold=True)
        elif comp == "↓":
            # Verde ou Laranja para diminuição
            styled_comp = _styled_cell("↓ Diminuiu", bg_color="#E8F5E9", color="#2E7D32", bold=True)
        elif comp == "=":
            # Cinza
            styled_comp = _styled_cell("= Igual", bg_color="#ECEFF1", color="#37474F", bold=True)
        else:
            styled_comp = _styled_cell("-", bg_color=None, color="#888888")
            
        html += f"""
        <tr>
          <td>{styled_gtfs_time}</td>
          <td>{styled_user_time}</td>
          <td style="font-family: monospace;">{val_i_gtfs}</td>
          <td style="font-family: monospace;">{val_i_user}</td>
          <td>{styled_comp}</td>
        </tr>
        """
        
    html += "</tbody></table>"
    return _clean_html(html)

def render_summary_table(df: pd.DataFrame) -> str:
    """
    Gera o HTML para a tabela resumo de partidas por faixa horária.
    Campos esperados: Faixa, Partidas GTFS, Partidas Propostas.
    """
    if df.empty:
        return "<p style='text-align: center; color: #888;'>Nenhum resumo disponível.</p>"
        
    html = _get_table_styles() + """
    <table class="custom-table">
      <thead>
        <tr>
          <th>Faixa Horária</th>
          <th>Partidas GTFS</th>
          <th>Partidas Propostas</th>
        </tr>
      </thead>
      <tbody>
    """
    
    for _, row in df.iterrows():
        faixa = row['Faixa']
        p_gtfs = int(row['Partidas GTFS'])
        p_user = int(row['Partidas Propostas'])
        
        is_total = (faixa == "Total")
        
        if is_total:
            styled_faixa = f"<b>{faixa}</b>"
            tr_class = 'class="total-row"'
            style_gtfs = f"<b>{p_gtfs}</b>"
            style_user = f"<b>{p_user}</b>"
        else:
            # Pega a cor correspondente à hora da faixa
            target_hour = TIME_TO_HOUR.get(faixa, 0)
            bg_color = get_time_color(target_hour)
            styled_faixa = _styled_cell(faixa, bg_color=bg_color, bold=True)
            tr_class = ""
            style_gtfs = str(p_gtfs)
            style_user = str(p_user)
            
        html += f"""
        <tr {tr_class}>
          <td>{styled_faixa}</td>
          <td style="font-family: monospace;">{style_gtfs}</td>
          <td style="font-family: monospace;">{style_user}</td>
        </tr>
        """
        
    html += "</tbody></table>"
    return _clean_html(html)
