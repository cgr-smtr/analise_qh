import gtfs_kit as gk
import pandas as pd
from app.config import GTFSMode

def load_gtfs(file_path: str) -> gk.Feed:
    """Carrega o arquivo GTFS (zip) usando a biblioteca gtfs-kit."""
    # O gtfs-kit requer a especificação da unidade de distância. Usamos 'km' por padrão.
    feed = gk.read_feed(file_path, dist_units='km')
    return feed

def detect_feed_mode(feed: gk.Feed) -> set[GTFSMode]:
    """
    Detecta quais modos estão disponíveis no feed (Frequencies e/ou Timetable).
    Retorna um set com os modos identificados.
    """
    modes = set()
    
    # Se existe tabela frequencies e tem registros, suporta FREQUENCIES
    if feed.frequencies is not None and not feed.frequencies.empty:
        modes.add(GTFSMode.FREQUENCIES)
        
    # Se existe tabela stop_times e tem registros, suporta TIMETABLE
    if feed.stop_times is not None and not feed.stop_times.empty:
        modes.add(GTFSMode.TIMETABLE)
        
    return modes

def get_route_choices(feed: gk.Feed) -> list[dict]:
    """
    Retorna a lista de rotas ordenadas por route_short_name.
    Cada item é um dicionário com route_id, route_short_name e label formatado:
    'route_short_name - route_id'
    """
    if feed.routes is None or feed.routes.empty:
        return []
        
    routes_df = feed.routes.copy()
    
    # Preenche valores nulos para evitar problemas na ordenação ou formatação
    routes_df['route_short_name'] = routes_df['route_short_name'].fillna('').astype(str)
    routes_df['route_id'] = routes_df['route_id'].astype(str)
    
    # Ordena por nome curto da rota
    routes_df = routes_df.sort_values(by='route_short_name')
    
    choices = []
    for _, row in routes_df.iterrows():
        route_id = row['route_id']
        short_name = row['route_short_name']
        label = f"{short_name} - {route_id}" if short_name else route_id
        choices.append({
            'route_id': route_id,
            'route_short_name': short_name,
            'label': label
        })
    return choices

def get_available_directions(feed: gk.Feed, route_id: str) -> list[str]:
    """
    Retorna os sentidos (direction_id) únicos disponíveis para a rota selecionada.
    """
    if feed.trips is None or feed.trips.empty:
        return []
        
    trips_df = feed.trips[feed.trips['route_id'] == route_id]
    
    if trips_df.empty:
        return []
        
    # direction_id pode ser numérico ou string, convertemos para str
    directions = trips_df['direction_id'].dropna().unique()
    # Converte para string e ordena
    return sorted([str(int(d)) if isinstance(d, (int, float)) and not pd.isna(d) else str(d) for d in directions])

def get_available_services(feed: gk.Feed, route_id: str, direction_id: str) -> list[str]:
    """
    Retorna os calendários (service_id) únicos disponíveis para a rota e sentido.
    """
    if feed.trips is None or feed.trips.empty:
        return []
        
    # Filtra trips por rota e sentido
    # Atenção: direction_id no GTFS pode ser lido como int ou str pelo pandas. Tratamos ambos.
    trips_df = feed.trips.copy()
    trips_df['direction_str'] = trips_df['direction_id'].dropna().astype(float).astype(int).astype(str)
    
    # Faz o filtro tratando a direção como string
    target_dir = str(int(float(direction_id))) if direction_id.replace('.','',1).isdigit() else direction_id
    filtered = trips_df[
        (trips_df['route_id'] == route_id) & 
        (trips_df['direction_str'] == target_dir)
    ]
    
    if filtered.empty:
        # Tenta comparação direta se falhar a conversão numérica
        filtered = trips_df[
            (trips_df['route_id'] == route_id) & 
            (trips_df['direction_id'].astype(str) == direction_id)
        ]
        
    services = filtered['service_id'].dropna().unique()
    return sorted(list(services))

def get_available_headsigns(feed: gk.Feed, route_id: str, direction_id: str) -> list[str]:
    """
    Retorna os destinos (trip_headsign) únicos e válidos (não nulos/vazios)
    para a rota e sentido selecionados.
    """
    if feed.trips is None or feed.trips.empty:
        return []
        
    trips_df = feed.trips.copy()
    trips_df['direction_str'] = trips_df['direction_id'].dropna().astype(float).astype(int).astype(str)
    
    target_dir = str(int(float(direction_id))) if direction_id.replace('.','',1).isdigit() else direction_id
    filtered = trips_df[
        (trips_df['route_id'] == route_id) & 
        (trips_df['direction_str'] == target_dir)
    ]
    
    if filtered.empty:
        filtered = trips_df[
            (trips_df['route_id'] == route_id) & 
            (trips_df['direction_id'].astype(str) == direction_id)
        ]
        
    if 'trip_headsign' not in filtered.columns:
        return []
        
    headsigns = filtered['trip_headsign'].dropna().unique()
    valid_headsigns = [h.strip() for h in headsigns if isinstance(h, str) and h.strip() != ""]
    return sorted(list(set(valid_headsigns)))

def get_filtered_trips(feed: gk.Feed, route_id: str, direction_id: str, service_id: str, headsign: str) -> pd.DataFrame:
    """
    Filtra trips por rota, sentido, serviço e destino (headsign).
    Retorna o DataFrame filtrado.
    """
    if feed.trips is None or feed.trips.empty:
        return pd.DataFrame()
        
    trips_df = feed.trips.copy()
    trips_df['direction_str'] = trips_df['direction_id'].dropna().astype(float).astype(int).astype(str)
    
    target_dir = str(int(float(direction_id))) if direction_id.replace('.','',1).isdigit() else direction_id
    
    mask = (
        (trips_df['route_id'] == route_id) & 
        (trips_df['service_id'] == service_id) &
        (trips_df['trip_headsign'].astype(str).str.strip() == headsign.strip())
    )
    
    filtered = trips_df[mask]
    
    # Aplica o filtro de direction_id adicionalmente
    filtered_dir = filtered[filtered['direction_str'] == target_dir]
    if filtered_dir.empty:
        filtered_dir = filtered[filtered['direction_id'].astype(str) == direction_id]
        
    return filtered_dir
