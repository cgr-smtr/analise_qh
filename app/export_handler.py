import re
import pandas as pd
import io
from app.config import GTFSMode, ExportFormat
from app.schedule_extractor import _time_str_to_seconds, _seconds_to_time_str
from app.user_input_parser import build_frequencies_from_user

def get_export_format(mode: GTFSMode) -> ExportFormat:
    """Determina o formato de exportação baseado no modo do GTFS."""
    if mode == GTFSMode.FREQUENCIES:
        return ExportFormat.CSV
    return ExportFormat.TXT

def sanitize_filename(name: str) -> str:
    """Remove caracteres inválidos para nomes de arquivos no Windows e substitui espaços por underscores."""
    if not name:
        return "indefinido"
    # Remove caracteres inválidos: \ / : * ? " < > |
    sanitized = re.sub(r'[\\/*?:"<>|]', '', name)
    # Substitui espaços e hifens múltiplos por um único underscore
    sanitized = re.sub(r'[\s\-]+', '_', sanitized)
    # Remove underscores no início e fim
    return sanitized.strip('_')

def build_export_filename(
    prefix: str,
    route: str,
    headsign: str,
    service: str,
    fmt: ExportFormat
) -> str:
    """Gera um nome de arquivo higienizado para exportação."""
    route_clean = sanitize_filename(route)
    headsign_clean = sanitize_filename(headsign)
    service_clean = sanitize_filename(service)
    
    ext = fmt.value
    return f"{prefix}_{route_clean}_{headsign_clean}_{service_clean}.{ext}"

def export_gtfs_as_csv(schedule_df: pd.DataFrame, route_name: str, headsign: str) -> str:
    """
    Exporta o schedule do GTFS em formato CSV de frequências.
    Reconstrói as faixas de frequências a partir do schedule individual.
    """
    if schedule_df.empty or 'Horário' not in schedule_df.columns:
        return ""
        
    # Extrai os tempos individuais em segundos
    seconds = schedule_df['Horário'].apply(_time_str_to_seconds).tolist()
    seconds = sorted(list(set(seconds)))
    
    # Reconstrói as frequências
    freq_df = build_frequencies_from_user(seconds, route_name, headsign)
    
    # Gera a string CSV
    output = io.StringIO()
    freq_df.to_csv(output, index=False, lineterminator='\n')
    return output.getvalue()

def export_gtfs_as_txt(schedule_df: pd.DataFrame) -> str:
    """
    Exporta o schedule do GTFS como uma lista de partidas simples.
    Gera um arquivo de texto com um horário por linha (HH:MM:SS), sem cabeçalho.
    """
    if schedule_df.empty or 'Horário' not in schedule_df.columns:
        return ""
        
    times = schedule_df['Horário'].tolist()
    return "\n".join(times) + "\n"

def export_user_as_csv(user_seconds: list[int], route_short_name: str, headsign: str) -> str:
    """
    Exporta a proposta do usuário em formato CSV de frequências.
    Reconstrói as faixas de frequências a partir das partidas individuais.
    """
    if not user_seconds:
        return ""
        
    # Ordena e remove duplicados (da mesma forma que o GTFS)
    seconds = sorted(list(set(user_seconds)))
    
    # Reconstrói as frequências
    freq_df = build_frequencies_from_user(seconds, route_short_name, headsign)
    
    # Gera a string CSV
    output = io.StringIO()
    freq_df.to_csv(output, index=False, lineterminator='\n')
    return output.getvalue()

def export_user_as_txt(user_seconds: list[int]) -> str:
    """
    Exporta a proposta do usuário em formato de texto simples.
    Gera um arquivo de texto com um horário por linha (HH:MM:SS), sem cabeçalho.
    """
    if not user_seconds:
        return ""
        
    # Converte os segundos para strings ordenadas
    sorted_seconds = sorted(user_seconds)
    times = [_seconds_to_time_str(s) for s in sorted_seconds]
    return "\n".join(times) + "\n"
