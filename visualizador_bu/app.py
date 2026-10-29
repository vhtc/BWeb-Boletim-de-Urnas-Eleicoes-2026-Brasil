import hashlib
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="Boletim de Urna", page_icon="BU", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');

    :root {
        --ink: #172a25;
        --muted: #64746d;
        --paper: #f3f6f1;
        --surface: #ffffff;
        --line: #dce5dc;
        --green: #147d5a;
        --mint: #d9eee2;
        --coral: #d96f58;
        --gold: #d9a83e;
    }
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: var(--ink); }
    [data-testid="stAppViewContainer"] { background: var(--paper); }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] { background: #e8efe8; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.4rem; }
    [data-testid="stMainBlockContainer"] { padding: 2rem 2.4rem 3rem; max-width: 1600px; }
    h1, h2, h3 { font-family: 'Manrope', sans-serif !important; color: var(--ink) !important; }
    .dashboard-header {
        display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;
        padding: 1rem 0 1.5rem; border-bottom: 1px solid var(--line); margin-bottom: 1.35rem;
    }
    .dashboard-header h1 { font-size: 2.25rem; line-height: 1.1; margin: .2rem 0 .45rem; }
    .dashboard-header p { color: var(--muted); margin: 0; }
    .eyebrow { color: var(--green) !important; font-size: .72rem; font-weight: 700; letter-spacing: .08em; }
    .local-badge {
        display: inline-flex; align-items: center; gap: .5rem; background: var(--mint); color: #15583f;
        border: 1px solid #b7dbc6; border-radius: 999px; padding: .45rem .75rem; font-size: .75rem;
        font-weight: 700; white-space: nowrap; margin-top: .35rem;
    }
    .local-badge span { width: .48rem; height: .48rem; background: var(--green); border-radius: 50%; }
    [data-testid="stMetric"] {
        background: var(--surface); border: 1px solid var(--line); border-top: 3px solid var(--green);
        border-radius: 8px; padding: 1rem 1.1rem; min-height: 112px;
    }
    [data-testid="stMetricLabel"] { color: var(--muted); font-weight: 600; }
    [data-testid="stMetricValue"] { font-family: 'Manrope', sans-serif; color: var(--ink); }
    [data-testid="stMetricDelta"] { font-size: .78rem; }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { font-weight: 600; color: var(--ink); }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
    div[data-testid="stPlotlyChart"] { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: .45rem; }
    @media (max-width: 760px) {
        [data-testid="stMainBlockContainer"] { padding: 1.15rem 1rem 2rem; }
        .dashboard-header { flex-direction: column; }
        .dashboard-header h1 { font-size: 1.8rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "Boletim_Urna_CSV"
SOURCE = "read_csv(?, delim=';', header=true, all_varchar=true, union_by_name=true, encoding='latin-1')"
PREVIEW_LIMIT = 500
REGION_STATES = {
    "Norte": ("AC", "AP", "AM", "PA", "RO", "RR", "TO"),
    "Nordeste": ("AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"),
    "Centro-Oeste": ("DF", "GO", "MT", "MS"),
    "Sudeste": ("ES", "MG", "RJ", "SP"),
    "Sul": ("PR", "RS", "SC"),
}
CLOSURE_HOUR_IN_BRASILIA = """
EXTRACT(HOUR FROM TRY_CAST(DT_ENCERRAMENTO AS TIMESTAMP) + CASE
    WHEN TRIM(SG_UF) = 'ZZ' THEN INTERVAL '0 hours'
        WHEN TRIM(SG_UF) = 'AC'
            OR (TRIM(SG_UF) = 'AM' AND TRIM(NM_MUNICIPIO) IN (
                    'AMATURÁ', 'ATALAIA DO NORTE', 'BENJAMIN CONSTANT', 'EIRUNEPÉ',
                    'ENVIRA', 'GUAJARÁ', 'IPIXUNA', 'ITAMARATI', 'JUTAÍ',
                    'SÃO PAULO DE OLIVENÇA', 'TABATINGA'
            )) THEN INTERVAL '2 hours'
        WHEN TRIM(SG_UF) IN ('RO', 'RR', 'MT', 'MS') OR TRIM(SG_UF) = 'AM'
            THEN INTERVAL '1 hour'
        WHEN TRIM(SG_UF) = 'PE' AND TRIM(NM_MUNICIPIO) = 'FERNANDO DE NORONHA'
            THEN INTERVAL '-1 hour'
        ELSE INTERVAL '0 hours'
END)
"""


@st.cache_data(show_spinner=False)
def run_query(
    files: tuple[str, ...],
    signature: tuple[tuple[str, int, int], ...],
    sql: str,
    params: tuple = (),
) -> pd.DataFrame:
    with duckdb.connect() as connection:
        return connection.execute(sql, [list(files), *params]).fetchdf()


def state_code(filename: str) -> str | None:
    match = re.search(r"(?:^|_)([A-Z]{2})(?:_|$)", Path(filename).stem.upper())
    return match.group(1) if match else None


def find_data_sources(directory: str) -> tuple[dict[str, list[tuple]], tuple[str, ...]]:
    path = Path(directory).expanduser()
    if not path.is_dir():
        return {}, ()

    sources: dict[str, list[tuple]] = {}
    for file in path.glob("*.csv"):
        state = state_code(file.name)
        if state:
            sources.setdefault(state, []).append(("csv", str(file.resolve()), ""))

    archives_without_csv = []
    for archive_path in sorted(path.glob("*.zip")):
        try:
            with zipfile.ZipFile(archive_path) as archive:
                csv_entries = [
                    entry for entry in archive.infolist()
                    if not entry.is_dir() and entry.filename.lower().endswith(".csv")
                ]
                if not csv_entries:
                    archives_without_csv.append(archive_path.name)
                    continue

                state = state_code(archive_path.name)
                if not state:
                    archives_without_csv.append(archive_path.name)
                    continue
                for entry in csv_entries:
                    sources.setdefault(state, []).append(
                        ("zip", str(archive_path.resolve()), entry.filename)
                    )
        except (OSError, zipfile.BadZipFile):
            archives_without_csv.append(archive_path.name)

    for state, entries in sources.items():
        direct_csvs = [entry for entry in entries if entry[0] == "csv"]
        if direct_csvs:
            sources[state] = direct_csvs

    return sources, tuple(archives_without_csv)


def load_state_files(sources: dict[str, list[tuple]], state: str) -> tuple[str, ...]:
    files = []
    cache_dir = Path(tempfile.gettempdir()) / "visualizador_bu_csv_cache"
    for kind, source_path, entry_name in sources.get(state, []):
        if kind == "csv":
            files.append(source_path)
            continue

        archive_path = Path(source_path)
        archive_stat = archive_path.stat()
        cache_key = hashlib.sha256(
            (
                f"{archive_path}:{archive_stat.st_size}:"
                f"{archive_stat.st_mtime_ns}:{entry_name}"
            ).encode("utf-8")
        ).hexdigest()
        cached_file = cache_dir / f"{cache_key}.csv"
        if not cached_file.exists():
            cache_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive_path) as archive:
                with archive.open(entry_name) as source, cached_file.open("wb") as target:
                    shutil.copyfileobj(source, target)
        files.append(str(cached_file.resolve()))
    return tuple(sorted(set(files)))


def file_signature(files: tuple[str, ...]) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        (file, Path(file).stat().st_size, Path(file).stat().st_mtime_ns)
        for file in files
    )


def where_clause(
    filters: tuple[tuple[str, str], ...],
    closure_hour: int | None = None,
    biometric_sections_only: bool = False,
) -> tuple[str, tuple]:
    clauses = [f"TRIM({column}) = ?" for column, _ in filters]
    params = [value for _, value in filters]
    if closure_hour is not None:
        clauses.append(f"{CLOSURE_HOUR_IN_BRASILIA} = ?")
        params.append(closure_hour)
    if biometric_sections_only:
        clauses.append("TRY_CAST(QT_ELEI_BIOM_SEM_HABILITACAO AS BIGINT) > 0")
    return ("WHERE " + " AND ".join(clauses), tuple(params)) if clauses else ("", ())


def choices(
    files: tuple[str, ...],
    signature: tuple[tuple[str, int, int], ...],
    column: str,
    filters: tuple[tuple[str, str], ...] = (),
) -> list[str]:
    where, params = where_clause(filters)
    extra_condition = f"AND TRIM({column}) <> ''" if where else f"WHERE TRIM({column}) <> ''"
    result = run_query(
        files,
        signature,
        f"SELECT DISTINCT TRIM({column}) AS value FROM {SOURCE} {where} "
        f"{extra_condition} ORDER BY value",
        params,
    )
    return [str(value) for value in result["value"].dropna().tolist() if str(value)]


def filter_select(
    label: str,
    values: list[str],
    key: str,
    default: str | None = None,
) -> str | None:
    options = ["Todos", *values]
    index = options.index(default) if default in options else 0
    selected = st.sidebar.selectbox(label, options, index=index, key=key)
    return None if selected == "Todos" else selected


def make_filters(
    state: str | None,
    city: str | None,
    cargo: str | None = None,
    candidate: str | None = None,
    zone: str = "",
    section: str = "",
) -> tuple[tuple[str, str], ...]:
    filters = []
    for column, value in (
        ("SG_UF", state),
        ("NM_MUNICIPIO", city),
        ("DS_CARGO_PERGUNTA", cargo),
        ("NM_VOTAVEL", candidate),
        ("NR_ZONA", zone.strip()),
        ("NR_SECAO", section.strip()),
    ):
        if value:
            filters.append((column, value))
    return tuple(filters)


st.markdown(
        """
        <div class="dashboard-header">
            <div>
                <p class="eyebrow">PAINEL DE DADOS ELEITORAIS</p>
                <h1>Boletim de Urna</h1>
                <p>Explore participação, votos e registros por localidade.</p>
            </div>
            <div class="local-badge"><span></span> PROCESSAMENTO LOCAL</div>
        </div>
        """,
        unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Dados")
    data_directory = st.text_input("Pasta com arquivos CSV", str(DEFAULT_DATA_DIR))
    st.caption("Coloque os CSVs dos estados nessa pasta. Os arquivos são lidos sob demanda.")

data_sources, archives_without_csv = find_data_sources(data_directory)
if not data_sources:
    st.warning("Não encontrei CSVs soltos nem arquivos ZIP com CSV nessa pasta.")
    st.stop()

states = sorted(data_sources)
region_options = [
    "Todas",
    *(region for region, region_states in REGION_STATES.items()
      if any(state_code in states for state_code in region_states)),
]
if "ZZ" in states:
    region_options.append("Exterior/Especial")
selected_region = st.sidebar.selectbox(
    "Região", region_options, key="region_v1"
)
if selected_region == "Todas":
    available_states = states
elif selected_region == "Exterior/Especial":
    available_states = [state_code for state_code in states if state_code == "ZZ"]
else:
    available_states = [
        state_code for state_code in REGION_STATES[selected_region]
        if state_code in states
    ]
state_options = ["Todos", *available_states]
selected_state = st.sidebar.selectbox(
    "Estado", state_options, index=0, key="state_v5"
)
state = None if selected_state == "Todos" else selected_state
selected_states = available_states if state is None else [state]
files = tuple(sorted({
    file
    for selected in selected_states
    for file in load_state_files(data_sources, selected)
}))
signature = file_signature(files)
st.caption(
    f"{selected_region} / {selected_state}: {len(files)} CSV(s) disponível(is), incluindo os encontrados em ZIPs. "
    f"A prévia da tabela é limitada a {PREVIEW_LIMIT} linhas. "
    "Os arquivos selecionados são preparados em cache temporário; ZIPs originais não são alterados."
)
if archives_without_csv:
    st.warning(
        "Estes ZIPs não contêm CSV ou não puderam ser lidos: "
        + ", ".join(archives_without_csv)
    )

city_options = choices(files, signature, "NM_MUNICIPIO", make_filters(state, None))
city = filter_select("Município", city_options, "city")
closure_period = st.sidebar.selectbox(
    "Horário de encerramento",
    ["Todos", "Normal (17h de Brasília)", "19h de Brasília"],
    key="closure_period_v1",
)
closure_hour = {
    "Normal (17h de Brasília)": 17,
    "19h de Brasília": 19,
}.get(closure_period)
cargo_filters = make_filters(state, city)
cargo_options = choices(files, signature, "DS_CARGO_PERGUNTA", cargo_filters)
cargo = filter_select("Cargo", cargo_options, "cargo_v2", "Presidente")
candidate_filters = make_filters(state, city, cargo)
candidate_options = choices(files, signature, "NM_VOTAVEL", candidate_filters)
candidate = filter_select("Candidato / opção", candidate_options, "candidate")

zone = st.sidebar.text_input("Zona (opcional)")
section = st.sidebar.text_input("Seção (opcional)")
biometric_section_filter = st.sidebar.selectbox(
    "Contagem de eleitores",
    [
        "Todos os eleitores aptos",
        "Todos os eleitores com falha de biometria",
    ],
    key="biometric_section_filter_v1",
)
biometric_sections_only = biometric_section_filter != "Todos os eleitores aptos"
location_filters = make_filters(state, city, cargo, zone=zone, section=section)
location_where, location_params = where_clause(
    location_filters, closure_hour, biometric_sections_only
)

section_summary = run_query(
    files,
    signature,
    f"""
    WITH section_totals AS (
        SELECT SG_UF, NM_MUNICIPIO, NR_ZONA, NR_SECAO,
               MAX(TRY_CAST(QT_APTOS AS BIGINT)) AS aptos,
               MAX(TRY_CAST(QT_COMPARECIMENTO AS BIGINT)) AS comparecimento,
             MAX(TRY_CAST(QT_ABSTENCOES AS BIGINT)) AS abstencoes,
             MAX(TRY_CAST(QT_ELEI_BIOM_SEM_HABILITACAO AS BIGINT)) AS biometria_sem_habilitacao
        FROM {SOURCE} {location_where}
        GROUP BY SG_UF, NM_MUNICIPIO, NR_ZONA, NR_SECAO
    )
    SELECT COUNT(*) AS secoes,
           COALESCE(SUM(aptos), 0) AS aptos,
           COALESCE(SUM(comparecimento), 0) AS comparecimento,
            COALESCE(SUM(abstencoes), 0) AS abstencoes,
            COALESCE(SUM(biometria_sem_habilitacao), 0) AS biometria_sem_habilitacao
    FROM section_totals
    """,
    location_params,
)
metrics = section_summary.iloc[0]
voter_count = (
    metrics["biometria_sem_habilitacao"] if biometric_sections_only else metrics["aptos"]
)
voter_count_label = (
    "Eleitores sem habilitação biométrica" if biometric_sections_only else "Eleitores aptos"
)
metric_columns = st.columns(4)
metric_columns[0].metric("Seções", f"{int(metrics['secoes']):,}".replace(",", "."))
metric_columns[1].metric(voter_count_label, f"{int(voter_count):,}".replace(",", "."))
attendance = int(metrics["comparecimento"])
absences = int(metrics["abstencoes"])
attendance_rate = attendance / (attendance + absences) * 100 if attendance + absences else 0
metric_columns[2].metric(
    "Comparecimento",
    f"{attendance:,}".replace(",", "."),
    f"{attendance_rate:.1f}% do total".replace(".", ","),
)
metric_columns[3].metric("Abstenções", f"{int(metrics['abstencoes']):,}".replace(",", "."))
st.caption(
    "A habilitação biométrica é contabilizada por seção. O cargo selecionado restringe os registros; "
    "por isso, o total pode ser igual entre cargos."
)

vote_filters = make_filters(state, city, cargo, candidate, zone, section)
vote_where, vote_params = where_clause(
    vote_filters, closure_hour, biometric_sections_only
)
votes = run_query(
    files,
    signature,
    f"""
    SELECT TRIM(NM_VOTAVEL) AS candidato,
           SUM(TRY_CAST(QT_VOTOS AS BIGINT)) AS votos
    FROM {SOURCE} {vote_where}
    GROUP BY TRIM(NM_VOTAVEL)
    ORDER BY votos DESC, candidato
    """,
    vote_params,
)

chart_left, chart_right = st.columns([1.5, 1], gap="large")
with chart_left:
    st.subheader("Votos por candidato ou opção")
    if biometric_sections_only:
        st.caption(
            "Exibindo votos de todos os eleitores nas seções selecionadas. "
            "O CSV não permite identificar os votos individuais dos eleitores sem biometria."
        )
    if votes.empty:
        st.info("Nenhum resultado para os filtros selecionados.")
    else:
        chart_votes = votes.head(12).sort_values("votos", ascending=True)
        vote_figure = px.bar(
            chart_votes,
            x="votos",
            y="candidato",
            orientation="h",
            color="votos",
            color_continuous_scale=["#b8ddc8", "#147d5a"],
            labels={"votos": "Votos", "candidato": "Candidato / opção"},
            text_auto=".2s",
        )
        vote_figure.update_layout(
            height=max(330, 42 * len(chart_votes) + 100),
            margin=dict(l=8, r=18, t=18, b=24),
            font=dict(family="DM Sans, sans-serif", color="#172a25"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
            xaxis=dict(showgrid=True, gridcolor="#e8eee8", zeroline=False, title=None),
            yaxis=dict(showgrid=False, title=None),
        )
        vote_figure.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{y}<br>%{x:,} votos<extra></extra>")
        st.plotly_chart(vote_figure, use_container_width=True, config={"displayModeBar": False})
        if len(votes) > len(chart_votes):
            st.caption(f"Gráfico com as 12 opções mais votadas; tabela completa abaixo ({len(votes)} opções).")

with chart_right:
    st.subheader("Participação eleitoral")
    if attendance + absences:
        participation_figure = go.Figure(
            go.Pie(
                labels=["Comparecimento", "Abstenções"],
                values=[attendance, absences],
                hole=0.76,
                sort=False,
                marker=dict(colors=["#147d5a", "#e6b84f"], line=dict(color="#ffffff", width=3)),
                textinfo="none",
                hovertemplate="%{label}<br>%{value:,} eleitores (%{percent})<extra></extra>",
            )
        )
        participation_figure.update_layout(
            height=390,
            margin=dict(l=12, r=12, t=18, b=18),
            showlegend=True,
            legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"),
            font=dict(family="DM Sans, sans-serif", color="#172a25"),
            paper_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(text=f"{attendance_rate:.1f}%".replace(".", ","), x=0.5, y=0.52, showarrow=False, font=dict(size=27, family="Manrope", color="#172a25"))],
        )
        st.plotly_chart(participation_figure, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Sem dados de participação para os filtros selecionados.")

st.subheader("Opções de voto")
st.dataframe(votes, hide_index=True, use_container_width=True, height=280)

st.subheader("Registros do boletim")
preview = run_query(
    files,
    signature,
    f"SELECT * FROM {SOURCE} {vote_where} LIMIT {PREVIEW_LIMIT}",
    vote_params,
)
st.dataframe(preview, hide_index=True, use_container_width=True, height=440)
st.caption(f"Exibindo até {PREVIEW_LIMIT} registros; os totais acima consideram todos os registros filtrados.")