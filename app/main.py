import sys
import pathlib

# Adiciona o diretório raiz do projeto ao sys.path para garantir o funcionamento das importações no Streamlit Cloud
root_dir = str(pathlib.Path(__file__).parent.parent.resolve())
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import streamlit as st
import tempfile
import os
import pandas as pd
from app.config import GTFSMode, ExportFormat
from app.gtfs_loader import (
    load_gtfs,
    detect_feed_mode,
    get_route_choices,
    get_available_directions,
    get_available_services,
    get_available_headsigns,
    get_filtered_trips
)
from app.schedule_extractor import extract_schedule, add_schedule_metadata
from app.user_input_parser import parse_user_times, build_user_schedule_df
from app.comparison_engine import compare_schedules, build_summary_by_period
from app.export_handler import (
    get_export_format,
    build_export_filename,
    export_gtfs_as_csv,
    export_gtfs_as_txt,
    export_user_as_csv,
    export_user_as_txt
)
from app.ui_components import (
    render_schedule_table,
    render_comparison_table,
    render_summary_table
)

# Aumenta limite de tamanho de arquivos como nas configurações do Shiny R
# O Streamlit lida com isso em arquivos de configuração (.streamlit/config.toml)
# Mas definimos layouts largos por padrão
st.set_page_config(
    page_title="Análise da Operação de Linhas de Ônibus",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializa sessão para gerenciar o input de horários do usuário
if 'partidas_input' not in st.session_state:
    st.session_state.partidas_input = ""

def clear_input():
    st.session_state.partidas_input = ""

@st.cache_data
def get_cached_feed(uploaded_file_bytes):
    """
    Salva temporariamente o arquivo carregado e lê o GTFS usando cache.
    Isso evita re-processar o ZIP a cada interação na tela do Streamlit.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(uploaded_file_bytes)
        tmp_path = tmp.name
        
    try:
        feed = load_gtfs(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
            
    return feed

# Título Principal do Painel
st.title("📊 Análise da Operação de Linhas de Ônibus")

# Sidebar de Configuração
st.sidebar.header("⚙️ Configurações do GTFS")

uploaded_file = st.sidebar.file_uploader("Carregar arquivo GTFS (ZIP)", type=["zip"])

if uploaded_file is not None:
    # Carrega dados do feed
    feed = get_cached_feed(uploaded_file.getvalue())
    
    # 1. Detecção automática de modo e seletor na sidebar
    modes_available = detect_feed_mode(feed)
    
    if not modes_available:
        st.sidebar.error("Erro: O GTFS não contém tabelas de horários válidas (frequencies.txt ou stop_times.txt).")
        st.stop()
        
    mode = None
    if GTFSMode.FREQUENCIES in modes_available and GTFSMode.TIMETABLE in modes_available:
        mode = st.sidebar.radio(
            "Selecione o tipo de dado do GTFS:",
            options=[GTFSMode.FREQUENCIES, GTFSMode.TIMETABLE],
            format_func=lambda m: "🔄 Frequências" if m == GTFSMode.FREQUENCIES else "📋 Quadro Horário (Timetable)",
            index=0
        )
    elif GTFSMode.FREQUENCIES in modes_available:
        st.sidebar.info("💡 Modo de Frequências detectado automaticamente.")
        mode = GTFSMode.FREQUENCIES
    else:
        st.sidebar.info("💡 Modo de Quadro Horário (Timetable) detectado automaticamente.")
        mode = GTFSMode.TIMETABLE

    # 2. Carregamento dos filtros em cascata
    route_choices = get_route_choices(feed)
    if not route_choices:
        st.error("Nenhuma rota encontrada no GTFS.")
        st.stop()
        
    route_labels = [r['label'] for r in route_choices]
    selected_route_label = st.sidebar.selectbox("Selecione uma linha:", options=route_labels)
    
    # Obtém dados da rota selecionada
    selected_route = next(r for r in route_choices if r['label'] == selected_route_label)
    route_id = selected_route['route_id']
    route_short_name = selected_route['route_short_name']
    
    # Sentido
    directions = get_available_directions(feed, route_id)
    selected_dir = st.sidebar.selectbox("Selecione o sentido:", options=directions)
    
    # Calendário
    services = get_available_services(feed, route_id, selected_dir)
    selected_service = st.sidebar.selectbox("Selecione um calendário:", options=services)
    
    # Destino (trip_headsign)
    headsigns = get_available_headsigns(feed, route_id, selected_dir)
    if not headsigns:
        st.error("Nenhum destino (trip_headsign) disponível para os filtros selecionados.")
        st.stop()
    selected_headsign = st.sidebar.selectbox("Selecione o destino:", options=headsigns)
    
    # 3. Processamento do GTFS
    trips_df = get_filtered_trips(feed, route_id, selected_dir, selected_service, selected_headsign)
    trip_ids = trips_df['trip_id'].tolist() if not trips_df.empty else []
    
    gtfs_schedule_raw = extract_schedule(feed, trip_ids, mode)
    
    # 4. Interface Principal: Exibição do Destino
    st.subheader(f"Trip Headsign: {selected_headsign}")
    
    # Colunas Principais de Dados
    col1, col2, col3, col4 = st.columns(4)
    
    # Coluna 1: Entrada do Usuário
    col1.subheader("Programação Prevista")
    col1.write("Colar um horário por linha (formato HH:MM:SS):")
    
    # Caixa de texto vinculada ao session_state para permitir limpar
    partidas_text = col1.text_area(
        label="Horários",
        label_visibility="collapsed",
        value=st.session_state.partidas_input,
        key="partidas_text_area",
        placeholder="Exemplo:\n03:40:00\n04:00:00\n04:20:00\n...",
        height=500
    )
    # Sincroniza o session state
    st.session_state.partidas_input = partidas_text
    
    col1.button("Limpar", on_click=clear_input, use_container_width=True)
    
    # Coluna 2: Tabela GTFS
    col2.subheader("Tabela do GTFS")
    if not gtfs_schedule_raw.empty:
        gtfs_schedule_df = add_schedule_metadata(gtfs_schedule_raw)
        col2.markdown(render_schedule_table(gtfs_schedule_df), unsafe_allow_html=True)
    else:
        col2.warning("Nenhum horário encontrado para os filtros aplicados.")
        gtfs_schedule_df = pd.DataFrame()
        
    # Processa Entrada do Usuário
    user_seconds = None
    user_schedule_df = pd.DataFrame()
    
    if st.session_state.partidas_input.strip() != "":
        user_seconds = parse_user_times(st.session_state.partidas_input)
        
        if user_seconds is None:
            # Exibe erro na Coluna 3 se o parse falhar (como no R)
            col3.subheader("Tabela Proposta")
            col3.error("Erro: Um ou mais horários foram inseridos no formato incorreto. Use o formato HH:MM:SS.")
        else:
            # Entrada é válida
            user_schedule_df = build_user_schedule_df(user_seconds)
            col3.subheader("Tabela Proposta")
            col3.markdown(render_schedule_table(user_schedule_df), unsafe_allow_html=True)
    else:
        col3.subheader("Tabela Proposta")
        col3.info("Aguardando inserção de horários.")
        
    # Coluna 4: Comparação
    col4.subheader("Comparação")
    if not gtfs_schedule_raw.empty and user_seconds is not None:
        comparison_df = compare_schedules(gtfs_schedule_df, user_seconds)
        col4.markdown(render_comparison_table(comparison_df), unsafe_allow_html=True)
    else:
        col4.info("Insira horários propostos para comparar.")
        
    # Seção inferior com o resumo por faixa horária
    st.divider()
    res_col1, res_col2 = st.columns([5, 7])
    
    res_col1.subheader("Partidas por Faixa Horária")
    if not gtfs_schedule_raw.empty and user_seconds is not None:
        # Extrai os segundos do GTFS ordenados
        gtfs_secs = gtfs_schedule_df['Horário'].apply(lambda x: sum(int(p) * mult for p, mult in zip(x.split(':'), [3600, 60, 1]))).tolist()
        summary_df = build_summary_by_period(gtfs_secs, user_seconds)
        res_col1.markdown(render_summary_table(summary_df), unsafe_allow_html=True)
    else:
        res_col1.info("Insira horários propostos para ver o resumo por faixa horária.")
        
    # 5. Configuração da seção de exportações na Sidebar
    st.sidebar.divider()
    st.sidebar.subheader("📥 Exportar Resultados")
    
    fmt = get_export_format(mode)
    
    # Download 1: Exportar GTFS
    if not gtfs_schedule_raw.empty:
        if fmt == ExportFormat.CSV:
            gtfs_export_data = export_gtfs_as_csv(gtfs_schedule_df, route_short_name, selected_headsign)
            label = "Baixar do GTFS (CSV)"
        else:
            gtfs_export_data = export_gtfs_as_txt(gtfs_schedule_df)
            label = "Baixar do GTFS (TXT)"
            
        filename_gtfs = build_export_filename("horarios", route_short_name, selected_headsign, selected_service, fmt)
        st.sidebar.download_button(
            label=label,
            data=gtfs_export_data,
            file_name=filename_gtfs,
            mime="text/csv" if fmt == ExportFormat.CSV else "text/plain",
            use_container_width=True
        )
        
    # Download 2: Exportar Proposta
    if user_seconds is not None:
        if fmt == ExportFormat.CSV:
            # Para frequências, exporta o formato agrupado
            user_export_data = export_user_as_csv(user_seconds, route_short_name, selected_headsign)
            label = "Baixar Proposta (CSV)"
        else:
            # Para timetable, exporta lista simples de partidas em TXT
            user_export_data = export_user_as_txt(user_seconds)
            label = "Baixar Proposta (TXT)"
            
        filename_user = build_export_filename("horarios", route_short_name, selected_headsign, selected_service, fmt)
        st.sidebar.download_button(
            label=label,
            data=user_export_data,
            file_name=filename_user,
            mime="text/csv" if fmt == ExportFormat.CSV else "text/plain",
            use_container_width=True
        )

else:
    # Estado inicial do app
    st.info("Para começar, carregue o arquivo GTFS (ZIP) na barra lateral esquerda.")
    
    # Demonstração visual de layout inativo
    col1, col2, col3, col4 = st.columns(4)
    col1.subheader("Programação Prevista")
    col1.text_area("Horários", label_visibility="collapsed", disabled=True, height=200)
    col2.subheader("Tabela do GTFS")
    col2.info("Aguardando arquivo GTFS.")
    col3.subheader("Tabela Proposta")
    col3.info("Aguardando arquivo GTFS.")
    col4.subheader("Comparação")
    col4.info("Aguardando arquivo GTFS.")
