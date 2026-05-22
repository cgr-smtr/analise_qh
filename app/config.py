from enum import Enum

class GTFSMode(Enum):
    FREQUENCIES = "frequencies"
    TIMETABLE = "timetable"

class ExportFormat(Enum):
    CSV = "csv"
    TXT = "txt"

# Cores associadas às faixas horárias (Replica a lógica get_time_color() do R)
TIME_COLORS = {
    0: "#B3E5FC",
    1: "#80DEEA",
    2: "#80CBC4",
    3: "#A5D6A7",
    4: "#C8E6C9",
    5: "#E6EE9C",
    6: "#FFF59D",   # Cobriria 6, 7, 8
    7: "#FFF59D",
    8: "#FFF59D",
    9: "#FFE082",   # Cobriria 9, 10, 11
    10: "#FFE082",
    11: "#FFE082",
    12: "#FFCC80",  # Cobriria 12, 13, 14
    13: "#FFCC80",
    14: "#FFCC80",
    15: "#FFAB91",  # Cobriria 15, 16, 17
    16: "#FFAB91",
    17: "#FFAB91",
    18: "#F48FB1",  # Cobriria 18, 19, 20
    19: "#F48FB1",
    20: "#F48FB1",
    21: "#CE93D8",
    22: "#B39DDB",
    23: "#9FA8DA",
    24: "#E0E0E0",
    25: "#CFD8DC",
    26: "#D7CCC8",
    27: "#DCEDC8",
    28: "#FFF9C4",
    29: "#FFECB3"
}

def get_time_color(hour: int) -> str:
    """Retorna a cor em formato hexadecimal associada a uma hora."""
    # Garante que a hora está dentro do mapeamento (0 a 29)
    h_mapped = int(hour) % 30
    return TIME_COLORS.get(h_mapped, "#FFFFFF")

# Configuração de faixas horárias para o resumo
TIME_PERIODS = [
    "00:00-00:59", "01:00-01:59", "02:00-02:59", "03:00-03:59",
    "04:00-04:59", "05:00-05:59", "06:00-08:59", "09:00-11:59",
    "12:00-14:59", "15:00-17:59", "18:00-20:59", "21:00-21:59",
    "22:00-22:59", "23:00-23:59", "24:00-24:59", "25:00-25:59",
    "26:00-26:59", "27:00-27:59", "28:00-28:59", "29:00-29:59"
]

BREAKS = [0, 1, 2, 3, 4, 5, 6, 9, 12, 15, 18, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]

# Mapeamento para saber qual hora base usar para pintar cada faixa no resumo
TIME_TO_HOUR = {
    "00:00-00:59": 0, "01:00-01:59": 1, "02:00-02:59": 2, "03:00-03:59": 3,
    "04:00-04:59": 4, "05:00-05:59": 5, "06:00-08:59": 6, "09:00-11:59": 9,
    "12:00-14:59": 12, "15:00-17:59": 15, "18:00-20:59": 18, "21:00-21:59": 21,
    "22:00-22:59": 22, "23:00-23:59": 23, "24:00-24:59": 24, "25:00-25:59": 25,
    "26:00-26:59": 26, "27:00-27:59": 27, "28:00-28:59": 28, "29:00-29:59": 29
}
