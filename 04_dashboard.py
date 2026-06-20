"""
Auditra - Step 4: Dashboard (v3)
Dashboard interaktif dengan choropleth peta kabupaten/kota, dark theme biru-oranye.

Dependencies:
    pip install dash dash-bootstrap-components plotly pandas networkx geopandas

Run:
    python 04_dashboard.py
    Buka browser → http://127.0.0.1:8050

Prasyarat:
    Jalankan 03b_geo_matching.py dulu untuk menghasilkan:
      - geo/geo_lookup.csv
      - geo/kabkota_clean.geojson
"""

import json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import networkx as nx
import warnings
warnings.filterwarnings('ignore')

# ── Config ────────────────────────────────────────────────────────────────────
DATA_PATH       = 'output/data_network.csv'    # ganti sesuai lokasimu
NODES_PATH      = 'output/kg_nodes.csv'
EDGES_PATH      = 'output/kg_edges.csv'
GEO_LOOKUP_PATH = 'geo/geo_lookup.csv'
GEOJSON_PATH    = 'geo/kabkota_clean.geojson'

# ── Tema Warna: Biru-Oranye Dark ─────────────────────────────────────────────
COLORS = {
    'bg_dark':      '#0f172a',   # slate-900
    'bg_panel':     '#1e293b',   # slate-800
    'bg_panel2':    '#162032',   # antara
    'border':       '#334155',   # slate-700
    'text_primary': '#f1f5f9',
    'text_muted':   '#94a3b8',
    'accent_blue':  '#3b82f6',
    'accent_blue_light': '#60a5fa',
    'accent_orange':'#f97316',
    'accent_gold':  '#eab308',
}

RISK_COLORS = {
    'KRITIS': '#ef4444',
    'TINGGI': '#f97316',
    'SEDANG': '#eab308',
    'RENDAH': '#3b82f6',
}

# Skala choropleth biru (rendah) -> oranye/merah (tinggi), mirip referensi
CHOROPLETH_SCALE = [
    [0.0, '#1e293b'],
    [0.15, '#3b5278'],
    [0.35, '#6b7a8f'],
    [0.55, '#c4a35a'],
    [0.75, '#e08a3c'],
    [1.0, '#ef4444'],
]

# ── Load Data ─────────────────────────────────────────────────────────────────
print("Loading data...")
df          = pd.read_csv(DATA_PATH, low_memory=False)
df_nodes    = pd.read_csv(NODES_PATH)
df_edges    = pd.read_csv(EDGES_PATH)
df_geolook  = pd.read_csv(GEO_LOOKUP_PATH)

with open(GEOJSON_PATH) as f:
    geojson_kabkota = json.load(f)

df['pagu_miliar'] = (df['pagu'] / 1e9).round(3)

print(f"  Data paket  : {len(df):,}")
print(f"  Geo lookup  : {len(df_geolook):,} baris")

# ── Join data ke kabkota_id ───────────────────────────────────────────────────
# Satu lokasi_sirup bisa map ke banyak kabkot_id (paket multi-lokasi)
# Untuk agregasi peta, setiap paket dihitung ke SEMUA kabkota yang relevan
geo_map = df_geolook.groupby('lokasi_sirup').agg(
    kabkot_ids=('kabkot_id', list),
    kabkot_names=('kabkot_name', list),
    prov_names=('prov_name', list),
).reset_index()

df = df.merge(geo_map, left_on='lokasi', right_on='lokasi_sirup', how='left')

# Explode: 1 paket dengan N lokasi -> N baris (untuk agregasi peta saja)
df_temp = df.dropna(subset=['kabkot_ids']).copy()
df_temp['_pair'] = df_temp.apply(lambda r: list(zip(r['kabkot_ids'], r['prov_names'])), axis=1)
df_exploded = df_temp.explode('_pair')
df_exploded['kabkot_id'] = df_exploded['_pair'].apply(lambda x: x[0])
df_exploded['prov_name'] = df_exploded['_pair'].apply(lambda x: x[1])
df_exploded = df_exploded.drop(columns=['_pair'])

print(f"  Paket ter-mapping ke kabkota : {df['kabkot_ids'].notna().sum():,} / {len(df):,}")

ALL_LEMBAGA = sorted(df['lembaga'].dropna().unique())
ALL_METODE  = sorted(df['metode'].dropna().unique())
ALL_PROV    = sorted(df_geolook['prov_name'].dropna().unique())

# ── Aggregate kabkota stats untuk choropleth ──────────────────────────────────
def aggregate_kabkota(data_exploded):
    stats = data_exploded.groupby('kabkot_id').agg(
        n_paket=('id', 'count'),
        avg_rpi=('RPI', 'mean'),
        total_pagu=('pagu_miliar', 'sum'),
        n_kritis=('risk_label', lambda x: (x == 'KRITIS').sum()),
        n_tinggi=('risk_label', lambda x: (x == 'TINGGI').sum()),
    ).reset_index()
    return stats

# ── Style global Dash + Plotly dark theme ────────────────────────────────────
def dark_layout_kwargs(height=400, margin=None):
    return dict(
        paper_bgcolor=COLORS['bg_panel'],
        plot_bgcolor=COLORS['bg_panel'],
        font=dict(color=COLORS['text_primary'], family='Inter, system-ui'),
        height=height,
        margin=margin or dict(t=10, b=10, l=10, r=10),
    )

# ── Charts ────────────────────────────────────────────────────────────────────

def fig_choropleth(data_exploded):
    stats = aggregate_kabkota(data_exploded)
    geo_ids_present = set(stats['kabkot_id'])

    fig = px.choropleth_mapbox(
        stats,
        geojson=geojson_kabkota,
        locations='kabkot_id',
        featureidkey='properties.kabkot_id',
        color='avg_rpi',
        color_continuous_scale=CHOROPLETH_SCALE,
        range_color=(0, max(60, stats['avg_rpi'].max() if len(stats) else 60)),
        hover_data={'n_paket': True, 'total_pagu': ':.1f', 'n_kritis': True,
                    'n_tinggi': True, 'avg_rpi': ':.1f'},
        mapbox_style='carto-darkmatter',
        zoom=4.0,
        center={'lat': -2.3, 'lon': 117.5},
        opacity=0.85,
    )
    fig.update_layout(
        **dark_layout_kwargs(height=520, margin=dict(t=0, b=0, l=0, r=0)),
        coloraxis_colorbar=dict(
            title=dict(text='Avg RPI', font=dict(color=COLORS['text_primary'])),
            tickfont=dict(color=COLORS['text_muted']),
            bgcolor='rgba(0,0,0,0)',
        ),
    )
    return fig

def fig_risk_donut(data):
    counts = data['risk_label'].value_counts().reset_index()
    counts.columns = ['risk_label', 'count']
    order = ['KRITIS', 'TINGGI', 'SEDANG', 'RENDAH']
    counts['risk_label'] = pd.Categorical(counts['risk_label'], categories=order, ordered=True)
    counts = counts.sort_values('risk_label')
    fig = go.Figure(go.Pie(
        labels=counts['risk_label'], values=counts['count'], hole=0.6,
        marker=dict(colors=[RISK_COLORS[r] for r in counts['risk_label']],
                    line=dict(color=COLORS['bg_panel'], width=2)),
        textinfo='percent', textfont=dict(color='white', size=11),
        hovertemplate='%{label}<br>%{value:,} paket<extra></extra>',
    ))
    fig.update_layout(**dark_layout_kwargs(height=240),
                       showlegend=True,
                       legend=dict(orientation='h', y=-0.1, font=dict(size=10, color=COLORS['text_muted'])))
    return fig

def fig_metode_bar(data):
    s = data.groupby('metode').agg(jumlah=('id', 'count'), avg_rpi=('RPI', 'mean')
        ).reset_index().sort_values('avg_rpi', ascending=True)
    fig = go.Figure(go.Bar(
        x=s['avg_rpi'], y=s['metode'], orientation='h',
        marker_color=[COLORS['accent_orange'] if v >= 30 else COLORS['accent_blue'] for v in s['avg_rpi']],
        text=s['avg_rpi'].round(1), textposition='outside', textfont=dict(color=COLORS['text_primary']),
        hovertemplate='%{y}<br>Avg RPI: %{x:.1f}<br>Jumlah: %{customdata[0]:,}<extra></extra>',
        customdata=s[['jumlah']].values,
    ))
    fig.update_layout(**dark_layout_kwargs(height=260, margin=dict(t=10, b=30, l=150, r=50)),
                       xaxis=dict(gridcolor=COLORS['border'], title='Rata-rata RPI'),
                       yaxis=dict(gridcolor=COLORS['border']))
    return fig

def fig_pagu_scatter(data):
    sample = data.sample(min(3000, len(data)), random_state=42) if len(data) > 0 else data
    fig = px.scatter(
        sample, x='pagu_miliar', y='RPI', color='risk_label',
        color_discrete_map=RISK_COLORS,
        hover_data=['paket', 'lembaga', 'metode'],
        labels={'pagu_miliar': 'Pagu (Miliar Rp)', 'RPI': 'Risk Priority Index'},
        opacity=0.65,
    )
    fig.update_traces(marker=dict(size=6, line=dict(width=0)))
    fig.update_layout(**dark_layout_kwargs(height=320, margin=dict(t=10, b=40, l=60, r=10)),
                       legend=dict(font=dict(color=COLORS['text_muted']), title=''),
                       xaxis=dict(gridcolor=COLORS['border']), yaxis=dict(gridcolor=COLORS['border']))
    return fig

def fig_kg_network(nodes_df, edges_df, max_nodes=70, focus_lembaga=None):
    top_nodes = nodes_df[nodes_df['node_type'].isin(['lembaga', 'satker'])]
    if focus_lembaga and focus_lembaga != 'ALL':
        focus_id = f"L::{focus_lembaga}"
        connected_satker_ids = edges_df[edges_df['source'] == focus_id]['target'].tolist()
        keep_ids = set([focus_id] + connected_satker_ids)
        top_nodes = top_nodes[top_nodes['node_id'].isin(keep_ids)]
    else:
        top_nodes = top_nodes.sort_values('risk_influence', ascending=False).head(max_nodes)

    top_ids = set(top_nodes['node_id'])
    edges_sub = edges_df[(edges_df['source'].isin(top_ids)) & (edges_df['target'].isin(top_ids))]

    G = nx.DiGraph()
    for _, row in top_nodes.iterrows():
        G.add_node(row['node_id'], **row.to_dict())
    for _, row in edges_sub.iterrows():
        G.add_edge(row['source'], row['target'], weight=row['weight'])

    if G.number_of_nodes() == 0:
        fig = go.Figure()
        fig.update_layout(**dark_layout_kwargs(height=420))
        return fig

    pos = nx.spring_layout(G, seed=42, k=0.5)
    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]; x1, y1 = pos[e[1]]
        edge_x += [x0, x1, None]; edge_y += [y0, y1, None]

    node_x = [pos[n][0] for n in G.nodes()]
    node_y = [pos[n][1] for n in G.nodes()]
    node_text = [G.nodes[n].get('label', n)[:30] for n in G.nodes()]
    node_rpi  = [G.nodes[n].get('avg_rpi', 0) for n in G.nodes()]
    node_type = [G.nodes[n].get('node_type', '') for n in G.nodes()]
    node_color = [COLORS['accent_orange'] if r >= 30 else COLORS['accent_blue_light'] for r in node_rpi]
    node_size = [max(8, min(28, G.nodes[n].get('n_paket', 1)/5)) for n in G.nodes()]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode='lines',
                              line=dict(width=0.5, color=COLORS['border']), hoverinfo='none'))
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode='markers+text',
        marker=dict(size=node_size, color=node_color, line=dict(width=1, color=COLORS['bg_panel'])),
        text=node_text, textposition='top center', textfont=dict(size=8, color=COLORS['text_muted']),
        hovertemplate='%{text}<br>Avg RPI: %{customdata[0]:.1f}<br>Tipe: %{customdata[1]}<extra></extra>',
        customdata=list(zip(node_rpi, node_type)),
    ))
    fig.update_layout(**dark_layout_kwargs(height=420),
                       showlegend=False,
                       xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
    return fig

def fig_signal_radar(data):
    signals = {
        'Metode': data['s1_metode'].mean(), 'Pagu Anomali': data['s2_pagu_anomali'].mean(),
        'Fragmentasi': data['s3_fragmentasi'].mean(), 'Konsentrasi': data['s4_konsentrasi'].mean(),
        'UMKM': data['s5_umkm'].mean(), 'Dana+Metode': data['s6_dana_metode'].mean(),
        'Reputasi KG': data['s7_reputasi'].mean(),
    }
    categories = list(signals.keys())
    values = list(signals.values())
    max_v = max(values) if max(values) > 0 else 1
    values_norm = [v / max_v for v in values]
    fig = go.Figure(go.Scatterpolar(
        r=values_norm + [values_norm[0]], theta=categories + [categories[0]],
        fill='toself', fillcolor='rgba(249,115,22,0.2)',
        line=dict(color=COLORS['accent_orange'], width=2),
        hovertemplate='%{theta}<br>Score: %{r:.3f}<extra></extra>',
    ))
    fig.update_layout(
        **dark_layout_kwargs(height=260, margin=dict(t=20, b=20, l=40, r=40)),
        polar=dict(
            bgcolor=COLORS['bg_panel'],
            radialaxis=dict(visible=True, range=[0, 1], color=COLORS['text_muted'], gridcolor=COLORS['border']),
            angularaxis=dict(color=COLORS['text_muted'], gridcolor=COLORS['border']),
        ),
    )
    return fig

# ── Stat Cards ────────────────────────────────────────────────────────────────
def stat_card(title, value, subtitle='', accent=None):
    accent = accent or COLORS['accent_blue']
    return html.Div([
        html.P(title, style={'fontSize':'11px','color':COLORS['text_muted'],
                              'marginBottom':'4px','letterSpacing':'0.5px','textTransform':'uppercase'}),
        html.H3(value, style={'fontWeight':'800','color':accent,'marginBottom':'2px','fontSize':'24px'}),
        html.P(subtitle, style={'fontSize':'11px','color':COLORS['text_muted'],'marginBottom':'0'}),
    ], style={'backgroundColor':COLORS['bg_panel'],'borderRadius':'10px','padding':'16px 18px',
              'border':f"1px solid {COLORS['border']}",
              'borderTop':f"3px solid {accent}", 'height':'100%'})

def section_panel(title, subtitle, children, width):
    header_children = [html.P(title, style={'fontWeight':'600','color':COLORS['text_primary'],
                                              'marginBottom':'2px','fontSize':'13px'})]
    if subtitle:
        header_children.append(html.P(subtitle, style={'fontSize':'11px','color':COLORS['text_muted'],
                                                          'marginBottom':'10px'}))
    else:
        header_children.append(html.Div(style={'marginBottom':'4px'}))
    return dbc.Col([
        html.Div(header_children + children, style={
            'backgroundColor':COLORS['bg_panel'], 'borderRadius':'10px','padding':'16px',
            'border':f"1px solid {COLORS['border']}", 'marginBottom':'16px', 'height':'100%'
        })
    ], width=width)

# ── App ───────────────────────────────────────────────────────────────────────
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP],
                 title='Auditra — Prioritas Audit Pengadaan Publik')

DROPDOWN_STYLE = {'fontSize':'12px', 'backgroundColor':COLORS['bg_panel2']}

app.layout = html.Div([
    dbc.Container([

        # ── HEADER ──
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div("AD", style={
                        'width':'42px','height':'42px','borderRadius':'10px',
                        'background':f"linear-gradient(135deg, {COLORS['accent_blue']}, {COLORS['accent_orange']})",
                        'display':'flex','alignItems':'center','justifyContent':'center',
                        'fontWeight':'800','color':'white','fontSize':'15px','marginRight':'12px'
                    }),
                    html.Div([
                        html.H4("Auditra", style={'fontWeight':'800','marginBottom':'0','color':COLORS['text_primary']}),
                        html.P("Sistem Prioritas Audit Pengadaan Publik — Knowledge Graph & Analisis Jaringan",
                               style={'fontSize':'12px','color':COLORS['text_muted'],'marginBottom':'0'}),
                    ]),
                ], style={'display':'flex','alignItems':'center'}),
            ], width=8),
            dbc.Col([
                html.Div([
                    html.Span("● LIVE", style={'color':COLORS['accent_orange'],'fontSize':'11px',
                                                'fontWeight':'600','marginRight':'12px'}),
                    html.Span("TA 2026", style={'color':COLORS['text_primary'],'fontSize':'11px',
                                                  'fontWeight':'700','backgroundColor':COLORS['bg_panel2'],
                                                  'padding':'4px 10px','borderRadius':'6px',
                                                  'border':f"1px solid {COLORS['border']}"}),
                ], style={'display':'flex','justifyContent':'flex-end','alignItems':'center','height':'100%'}),
            ], width=4),
        ], style={'paddingTop':'18px','paddingBottom':'14px'}),

        # ── FILTER BAR ──
        dbc.Row([
            dbc.Col([
                html.P("Provinsi", style={'fontSize':'10px','color':COLORS['text_muted'],'marginBottom':'4px'}),
                dcc.Dropdown(id='filter-provinsi',
                    options=[{'label':'Semua Provinsi','value':'ALL'}] + [{'label':p,'value':p} for p in ALL_PROV],
                    value='ALL', clearable=False, style=DROPDOWN_STYLE,
                    className='dash-dark-dropdown'),
            ], width=3),
            dbc.Col([
                html.P("Lembaga", style={'fontSize':'10px','color':COLORS['text_muted'],'marginBottom':'4px'}),
                dcc.Dropdown(id='filter-lembaga',
                    options=[{'label':'Semua Lembaga','value':'ALL'}] + [{'label':l,'value':l} for l in ALL_LEMBAGA],
                    value='ALL', clearable=False, style=DROPDOWN_STYLE, placeholder='Cari lembaga...'),
            ], width=4),
            dbc.Col([
                html.P("Metode", style={'fontSize':'10px','color':COLORS['text_muted'],'marginBottom':'4px'}),
                dcc.Dropdown(id='filter-metode',
                    options=[{'label':'Semua Metode','value':'ALL'}] + [{'label':m,'value':m} for m in ALL_METODE],
                    value='ALL', clearable=False, style=DROPDOWN_STYLE),
            ], width=3),
            dbc.Col([
                html.P("Min. RPI", style={'fontSize':'10px','color':COLORS['text_muted'],'marginBottom':'4px'}),
                dcc.Dropdown(id='filter-risk-min',
                    options=[{'label':'Semua','value':0},{'label':'≥30 Sedang+','value':30},
                             {'label':'≥50 Tinggi+','value':50},{'label':'≥70 Kritis','value':70}],
                    value=0, clearable=False, style=DROPDOWN_STYLE),
            ], width=2),
        ], className='mb-3'),

        # ── STAT CARDS ──
        dbc.Row(id='stat-cards', className='mb-3 g-3'),

        # ── PETA + DONUT/RADAR ──
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.P("🗺️ Peta Risiko Pengadaan per Kabupaten/Kota",
                           style={'fontWeight':'600','color':COLORS['text_primary'],'marginBottom':'2px','fontSize':'13px'}),
                    html.P("Warna gelap → biru → oranye → merah menunjukkan eskalasi rata-rata RPI wilayah",
                           style={'fontSize':'11px','color':COLORS['text_muted'],'marginBottom':'10px'}),
                    dcc.Graph(id='chart-choropleth', config={'displayModeBar': False}),
                ], style={'backgroundColor':COLORS['bg_panel'],'borderRadius':'10px','padding':'16px',
                          'border':f"1px solid {COLORS['border']}", 'marginBottom':'16px'})
            ], width=8),
            dbc.Col([
                html.Div([
                    html.P("Distribusi Risiko", style={'fontWeight':'600','color':COLORS['text_primary'],
                                                        'marginBottom':'8px','fontSize':'13px'}),
                    dcc.Graph(id='chart-donut', config={'displayModeBar': False}),
                ], style={'backgroundColor':COLORS['bg_panel'],'borderRadius':'10px','padding':'16px',
                          'border':f"1px solid {COLORS['border']}", 'marginBottom':'16px'}),
                html.Div([
                    html.P("Profil Sinyal Risiko", style={'fontWeight':'600','color':COLORS['text_primary'],
                                                           'marginBottom':'8px','fontSize':'13px'}),
                    dcc.Graph(id='chart-radar', config={'displayModeBar': False}),
                ], style={'backgroundColor':COLORS['bg_panel'],'borderRadius':'10px','padding':'16px',
                          'border':f"1px solid {COLORS['border']}"}),
            ], width=4),
        ]),

        # ── METODE BAR + SCATTER ──
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.P("Rata-rata RPI per Metode Pengadaan",
                           style={'fontWeight':'600','color':COLORS['text_primary'],'marginBottom':'8px','fontSize':'13px'}),
                    dcc.Graph(id='chart-metode', config={'displayModeBar': False}),
                ], style={'backgroundColor':COLORS['bg_panel'],'borderRadius':'10px','padding':'16px',
                          'border':f"1px solid {COLORS['border']}", 'marginBottom':'16px'})
            ], width=5),
            dbc.Col([
                html.Div([
                    html.P("Distribusi Pagu vs RPI",
                           style={'fontWeight':'600','color':COLORS['text_primary'],'marginBottom':'8px','fontSize':'13px'}),
                    dcc.Graph(id='chart-scatter', config={'displayModeBar': False}),
                ], style={'backgroundColor':COLORS['bg_panel'],'borderRadius':'10px','padding':'16px',
                          'border':f"1px solid {COLORS['border']}", 'marginBottom':'16px'})
            ], width=7),
        ]),

        # ── KNOWLEDGE GRAPH ──
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.P("🕸️ Knowledge Graph — Jaringan Lembaga & Satker",
                           style={'fontWeight':'600','color':COLORS['text_primary'],'marginBottom':'2px','fontSize':'13px'}),
                    html.P("🟠 RPI ≥ 30   🔵 RPI < 30 — Pilih lembaga di filter untuk fokus jaringan",
                           style={'fontSize':'11px','color':COLORS['text_muted'],'marginBottom':'8px'}),
                    dcc.Graph(id='chart-kg', config={'displayModeBar': True}),
                ], style={'backgroundColor':COLORS['bg_panel'],'borderRadius':'10px','padding':'16px',
                          'border':f"1px solid {COLORS['border']}", 'marginBottom':'16px'})
            ], width=12),
        ]),

        # ── DAFTAR WILAYAH & LEMBAGA KRITIS (side by side) ──
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.P("🏛️ Lembaga Paling Berisiko",
                           style={'fontWeight':'600','color':COLORS['text_primary'],'marginBottom':'10px','fontSize':'13px'}),
                    html.Div(id='list-lembaga'),
                ], style={'backgroundColor':COLORS['bg_panel'],'borderRadius':'10px','padding':'16px',
                          'border':f"1px solid {COLORS['border']}", 'marginBottom':'16px',
                          'maxHeight':'480px','overflowY':'auto'})
            ], width=6),
            dbc.Col([
                html.Div([
                    html.P("📍 Provinsi Paling Berisiko",
                           style={'fontWeight':'600','color':COLORS['text_primary'],'marginBottom':'10px','fontSize':'13px'}),
                    html.Div(id='list-provinsi'),
                ], style={'backgroundColor':COLORS['bg_panel'],'borderRadius':'10px','padding':'16px',
                          'border':f"1px solid {COLORS['border']}", 'marginBottom':'16px',
                          'maxHeight':'480px','overflowY':'auto'})
            ], width=6),
        ]),

        # ── TABEL PAKET ──
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.P("📋 Daftar Paket Prioritas Audit",
                           style={'fontWeight':'600','color':COLORS['text_primary'],'marginBottom':'12px','fontSize':'13px'}),
                    html.Div(id='table-prioritas-wrap'),
                ], style={'backgroundColor':COLORS['bg_panel'],'borderRadius':'10px','padding':'16px',
                          'border':f"1px solid {COLORS['border']}", 'marginBottom':'16px'})
            ], width=12),
        ]),

        html.P("Auditra © 2026 — Data: SIRUP LKPP | Metode: Knowledge Graph + Rule-based Scoring (Transparan, Tanpa AI Black-box)",
               style={'fontSize':'11px','color':COLORS['text_muted'],'textAlign':'center',
                      'marginTop':'8px','marginBottom':'20px'}),

    ], fluid=True, style={'maxWidth':'1500px'})
], style={'backgroundColor': COLORS['bg_dark'], 'minHeight':'100vh', 'fontFamily':'Inter, system-ui',
          'paddingBottom':'20px'})

# ── Filter helper ─────────────────────────────────────────────────────────────
def apply_filters(provinsi, lembaga, metode, risk_min, exploded=False):
    d = df_exploded if exploded else df
    if provinsi != 'ALL':
        col = 'prov_name' if exploded else 'lokasi'
        d = d[d[col].astype(str).str.contains(provinsi, case=False, na=False)]
    if lembaga != 'ALL':
        d = d[d['lembaga'] == lembaga]
    if metode != 'ALL':
        d = d[d['metode'] == metode]
    if risk_min > 0:
        d = d[d['RPI'] >= risk_min]
    return d

def risk_row_item(name, avg_rpi, n_kritis, n_tinggi, n_paket, extra=''):
    accent = COLORS['accent_orange'] if avg_rpi >= 30 else COLORS['accent_blue_light']
    return html.Div([
        html.Div([
            html.Span(name, style={'fontWeight':'600','fontSize':'12.5px','color':COLORS['text_primary']}),
            html.Span(f"RPI {avg_rpi:.1f}", style={'fontSize':'11px','fontWeight':'700','color':accent,
                                                      'backgroundColor':COLORS['bg_panel2'],'padding':'2px 8px',
                                                      'borderRadius':'5px'}),
        ], style={'display':'flex','justifyContent':'space-between','alignItems':'center','marginBottom':'4px'}),
        html.Div([
            html.Span(f"Kritis: {n_kritis}", style={'fontSize':'10.5px','color':'#fca5a5','marginRight':'10px'}),
            html.Span(f"Tinggi: {n_tinggi}", style={'fontSize':'10.5px','color':'#fdba74','marginRight':'10px'}),
            html.Span(f"Total paket: {n_paket:,}{extra}", style={'fontSize':'10.5px','color':COLORS['text_muted']}),
        ]),
    ], style={'padding':'10px 0', 'borderBottom':f"1px solid {COLORS['border']}"})

# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(
    Output('stat-cards', 'children'),
    Input('filter-provinsi','value'), Input('filter-lembaga','value'),
    Input('filter-metode','value'), Input('filter-risk-min','value'),
)
def update_stats(provinsi, lembaga, metode, risk_min):
    d = apply_filters(provinsi, lembaga, metode, risk_min)
    cards = [
        ('Total Paket', f"{len(d):,}", "dalam filter", COLORS['accent_blue']),
        ('Total Pagu', f"Rp {d['pagu_miliar'].sum():,.1f} M", "miliar rupiah", COLORS['accent_blue']),
        ('Paket Kritis', f"{(d['risk_label']=='KRITIS').sum():,}", "RPI ≥ 70", COLORS['accent_orange']),
        ('Rata-rata RPI', f"{d['RPI'].mean():.1f}" if len(d)>0 else "0", "skala 0–100", COLORS['accent_gold']),
        ('Potensi Split Contract', f"{(d['s3_fragmentasi']>=0.6).sum():,}", "similarity ≥ 0.6", COLORS['accent_orange']),
    ]
    return [dbc.Col(stat_card(t, v, s, a), width=True) for t, v, s, a in cards]

@app.callback(
    Output('chart-choropleth','figure'),
    Input('filter-lembaga','value'), Input('filter-metode','value'), Input('filter-risk-min','value'),
)
def update_choropleth(lembaga, metode, risk_min):
    d = apply_filters('ALL', lembaga, metode, risk_min, exploded=True)
    return fig_choropleth(d)

@app.callback(
    Output('chart-donut','figure'), Output('chart-metode','figure'),
    Output('chart-scatter','figure'), Output('chart-radar','figure'),
    Input('filter-provinsi','value'), Input('filter-lembaga','value'),
    Input('filter-metode','value'), Input('filter-risk-min','value'),
)
def update_charts(provinsi, lembaga, metode, risk_min):
    d = apply_filters(provinsi, lembaga, metode, risk_min)
    return fig_risk_donut(d), fig_metode_bar(d), fig_pagu_scatter(d), fig_signal_radar(d)

@app.callback(Output('chart-kg', 'figure'), Input('filter-lembaga', 'value'))
def update_kg(lembaga):
    return fig_kg_network(df_nodes, df_edges, focus_lembaga=lembaga)

@app.callback(
    Output('list-lembaga', 'children'),
    Input('filter-provinsi','value'), Input('filter-metode','value'), Input('filter-risk-min','value'),
)
def update_list_lembaga(provinsi, metode, risk_min):
    d = apply_filters(provinsi, 'ALL', metode, risk_min)
    lem = d.groupby('lembaga').agg(
        avg_rpi=('RPI','mean'), n_kritis=('risk_label', lambda x:(x=='KRITIS').sum()),
        n_tinggi=('risk_label', lambda x:(x=='TINGGI').sum()), n_paket=('id','count'),
    ).reset_index().sort_values('avg_rpi', ascending=False).head(25)
    return [risk_row_item(r['lembaga'], r['avg_rpi'], r['n_kritis'], r['n_tinggi'], r['n_paket'])
            for _, r in lem.iterrows()]

@app.callback(
    Output('list-provinsi', 'children'),
    Input('filter-lembaga','value'), Input('filter-metode','value'), Input('filter-risk-min','value'),
)
def update_list_provinsi(lembaga, metode, risk_min):
    d = apply_filters('ALL', lembaga, metode, risk_min, exploded=True)
    prov = d.groupby('prov_name').agg(
        avg_rpi=('RPI','mean'), n_kritis=('risk_label', lambda x:(x=='KRITIS').sum()),
        n_tinggi=('risk_label', lambda x:(x=='TINGGI').sum()), n_paket=('id','count'),
    ).reset_index().sort_values('avg_rpi', ascending=False).head(25)
    return [risk_row_item(r['prov_name'], r['avg_rpi'], r['n_kritis'], r['n_tinggi'], r['n_paket'])
            for _, r in prov.iterrows()]

@app.callback(
    Output('table-prioritas-wrap', 'children'),
    Input('filter-provinsi','value'), Input('filter-lembaga','value'),
    Input('filter-metode','value'), Input('filter-risk-min','value'),
)
def update_table(provinsi, lembaga, metode, risk_min):
    d = apply_filters(provinsi, lembaga, metode, max(risk_min, 30))
    d = d.sort_values('RPI', ascending=False).head(300).reset_index(drop=True)
    d['rank'] = d.index + 1
    cols = ['rank','RPI','risk_label','paket','lembaga','metode','pagu_miliar','lokasi']
    return dash_table.DataTable(
        columns=[{'name':'#','id':'rank'},{'name':'RPI','id':'RPI'},{'name':'Label','id':'risk_label'},
                 {'name':'Paket','id':'paket'},{'name':'Lembaga','id':'lembaga'},
                 {'name':'Metode','id':'metode'},{'name':'Pagu (M)','id':'pagu_miliar'},
                 {'name':'Lokasi','id':'lokasi'}],
        data=d[cols].to_dict('records'),
        style_table={'overflowX':'auto'},
        style_cell={'fontSize':'12px','padding':'8px 10px','fontFamily':'Inter, system-ui',
                    'backgroundColor':COLORS['bg_panel'],'color':COLORS['text_primary'],
                    'border':f"1px solid {COLORS['border']}",
                    'maxWidth':'260px','overflow':'hidden','textOverflow':'ellipsis'},
        style_header={'fontWeight':'600','backgroundColor':COLORS['bg_panel2'],
                      'color':COLORS['text_primary'],'border':f"1px solid {COLORS['border']}"},
        style_data_conditional=[
            {'if':{'filter_query':'{risk_label} = "KRITIS"'}, 'backgroundColor':'#3b1818', 'color':'#fca5a5'},
            {'if':{'filter_query':'{risk_label} = "TINGGI"'}, 'backgroundColor':'#3b2818', 'color':'#fdba74'},
        ],
        page_size=15, sort_action='native', filter_action='native',
    )

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("\n✓ Dashboard siap!")
    print("  Buka browser → http://127.0.0.1:8050\n")
    app.run(debug=False, host='0.0.0.0', port=8050)
