"""
Auditra - Step 4: Dashboard
Dashboard interaktif simple & clean untuk visualisasi hasil scoring dan KG.

Dependencies:
    pip install dash dash-bootstrap-components plotly pandas networkx

Run:
    python 04_dashboard.py
    Buka browser → http://127.0.0.1:8050
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import networkx as nx
import warnings
warnings.filterwarnings('ignore')

# ── Config ────────────────────────────────────────────────────────────────────
DATA_PATH  = 'output/data_network.csv'   # ganti sesuai lokasimu
NODES_PATH = 'output/kg_nodes.csv'
EDGES_PATH = 'output/kg_edges.csv'

RISK_COLORS = {
    'KRITIS': '#ef4444',
    'TINGGI': '#f97316',
    'SEDANG': '#eab308',
    'RENDAH': '#22c55e',
}

# ── Load Data ─────────────────────────────────────────────────────────────────
print("Loading data...")
df       = pd.read_csv(DATA_PATH, low_memory=False)
df_nodes = pd.read_csv(NODES_PATH)
df_edges = pd.read_csv(EDGES_PATH)

# Format pagu ke miliar
df['pagu_miliar'] = (df['pagu'] / 1e9).round(3)

# Ekstrak provinsi
df['provinsi'] = df['lokasi'].astype(str).str.split(',').str[0].str.strip()

print(f"  Data loaded: {len(df):,} paket")

# ── Helper Charts ─────────────────────────────────────────────────────────────

def fig_risk_donut(data):
    counts = data['risk_label'].value_counts().reset_index()
    counts.columns = ['risk_label', 'count']
    order = ['KRITIS', 'TINGGI', 'SEDANG', 'RENDAH']
    counts['risk_label'] = pd.Categorical(counts['risk_label'], categories=order, ordered=True)
    counts = counts.sort_values('risk_label')
    fig = go.Figure(go.Pie(
        labels=counts['risk_label'],
        values=counts['count'],
        hole=0.55,
        marker_colors=[RISK_COLORS[r] for r in counts['risk_label']],
        textinfo='label+percent',
        hovertemplate='%{label}<br>%{value:,} paket<extra></extra>',
    ))
    fig.update_layout(
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor='white',
        height=260,
    )
    return fig

def fig_metode_bar(data):
    metode_stats = data.groupby('metode').agg(
        jumlah=('id','count'),
        avg_rpi=('RPI','mean'),
        total_pagu=('pagu_miliar','sum')
    ).reset_index().sort_values('avg_rpi', ascending=True)

    fig = go.Figure(go.Bar(
        x=metode_stats['avg_rpi'],
        y=metode_stats['metode'],
        orientation='h',
        marker_color=[
            '#ef4444' if v >= 50 else '#f97316' if v >= 30 else '#22c55e'
            for v in metode_stats['avg_rpi']
        ],
        text=metode_stats['avg_rpi'].round(1),
        textposition='outside',
        hovertemplate='%{y}<br>Avg RPI: %{x:.1f}<br>Jumlah: %{customdata[0]:,}<extra></extra>',
        customdata=metode_stats[['jumlah']].values,
    ))
    fig.update_layout(
        xaxis_title='Rata-rata RPI',
        margin=dict(t=10, b=40, l=160, r=60),
        paper_bgcolor='white',
        plot_bgcolor='white',
        height=280,
        xaxis=dict(gridcolor='#f0f0f0'),
    )
    return fig

def fig_pagu_scatter(data):
    sample = data.sample(min(3000, len(data)), random_state=42)
    fig = px.scatter(
        sample,
        x='pagu_miliar',
        y='RPI',
        color='risk_label',
        color_discrete_map=RISK_COLORS,
        hover_data=['paket', 'lembaga', 'metode'],
        labels={'pagu_miliar': 'Pagu (Miliar Rp)', 'RPI': 'Risk Priority Index'},
        opacity=0.6,
    )
    fig.update_layout(
        margin=dict(t=10, b=40, l=60, r=10),
        paper_bgcolor='white',
        plot_bgcolor='white',
        height=300,
        legend_title='',
        xaxis=dict(gridcolor='#f0f0f0'),
        yaxis=dict(gridcolor='#f0f0f0'),
    )
    return fig

def fig_provinsi_map(data):
    prov_stats = data.groupby('provinsi').agg(
        n_paket=('id','count'),
        avg_rpi=('RPI','mean'),
        n_kritis=('risk_label', lambda x: (x=='KRITIS').sum()),
    ).reset_index().sort_values('avg_rpi', ascending=False).head(20)

    fig = go.Figure(go.Bar(
        x=prov_stats['avg_rpi'],
        y=prov_stats['provinsi'],
        orientation='h',
        marker_color='#3b82f6',
        hovertemplate='%{y}<br>Avg RPI: %{x:.1f}<br>Paket: %{customdata[0]:,}<extra></extra>',
        customdata=prov_stats[['n_paket']].values,
    ))
    fig.update_layout(
        xaxis_title='Rata-rata RPI',
        margin=dict(t=10, b=40, l=180, r=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        height=420,
        xaxis=dict(gridcolor='#f0f0f0'),
    )
    return fig

def fig_kg_network(nodes_df, edges_df, max_nodes=80):
    """Visualisasi Knowledge Graph - top nodes by pagerank"""
    top_nodes = nodes_df[nodes_df['node_type'].isin(['lembaga','satker'])]\
        .sort_values('pagerank', ascending=False).head(max_nodes)

    top_ids = set(top_nodes['node_id'])
    edges_sub = edges_df[
        (edges_df['source'].isin(top_ids)) &
        (edges_df['target'].isin(top_ids))
    ]

    G = nx.DiGraph()
    for _, row in top_nodes.iterrows():
        G.add_node(row['node_id'], **row.to_dict())
    for _, row in edges_sub.iterrows():
        G.add_edge(row['source'], row['target'], weight=row['weight'])

    pos = nx.spring_layout(G, seed=42, k=0.5)

    edge_x, edge_y = [], []
    for e in G.edges():
        x0, y0 = pos[e[0]]
        x1, y1 = pos[e[1]]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    node_x = [pos[n][0] for n in G.nodes()]
    node_y = [pos[n][1] for n in G.nodes()]
    node_text = [G.nodes[n].get('label', n)[:30] for n in G.nodes()]
    node_rpi  = [G.nodes[n].get('avg_rpi', 0) for n in G.nodes()]
    node_type = [G.nodes[n].get('node_type', '') for n in G.nodes()]
    node_color = [
        '#ef4444' if r >= 50 else '#f97316' if r >= 30 else '#3b82f6'
        for r in node_rpi
    ]
    node_size = [
        max(8, min(30, G.nodes[n].get('n_paket', 1) / 5))
        for n in G.nodes()
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        mode='lines',
        line=dict(width=0.5, color='#d1d5db'),
        hoverinfo='none',
    ))
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        marker=dict(size=node_size, color=node_color, line=dict(width=1, color='white')),
        text=node_text,
        textposition='top center',
        textfont=dict(size=8),
        hovertemplate='%{text}<br>Avg RPI: %{customdata[0]:.1f}<br>Tipe: %{customdata[1]}<extra></extra>',
        customdata=list(zip(node_rpi, node_type)),
    ))
    fig.update_layout(
        showlegend=False,
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor='white',
        plot_bgcolor='white',
        height=450,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )
    return fig

def fig_signal_radar(data):
    """Radar chart rata-rata kontribusi sinyal"""
    signals = {
        'Metode':       data['s1_metode'].mean(),
        'Pagu Anomali': data['s2_pagu_anomali'].mean(),
        'Fragmentasi':  data['s3_fragmentasi'].mean(),
        'Konsentrasi':  data['s4_konsentrasi'].mean(),
        'UMKM':         data['s5_umkm'].mean(),
        'Dana+Metode':  data['s6_dana_metode'].mean(),
        'Reputasi KG':  data['s7_reputasi'].mean(),
    }
    categories = list(signals.keys())
    values     = list(signals.values())
    values_norm = [v / max(values) for v in values]

    fig = go.Figure(go.Scatterpolar(
        r=values_norm + [values_norm[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(59,130,246,0.15)',
        line=dict(color='#3b82f6', width=2),
        hovertemplate='%{theta}<br>Score: %{r:.3f}<extra></extra>',
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,1])),
        margin=dict(t=20, b=20, l=40, r=40),
        paper_bgcolor='white',
        height=280,
    )
    return fig

# ── Stat Cards ────────────────────────────────────────────────────────────────
def stat_card(title, value, subtitle='', color='#1e293b'):
    return dbc.Card([
        dbc.CardBody([
            html.P(title, className='text-muted mb-1', style={'fontSize':'12px'}),
            html.H4(value, style={'fontWeight':'700', 'color': color, 'marginBottom':'2px'}),
            html.P(subtitle, className='text-muted', style={'fontSize':'11px', 'marginBottom':'0'}),
        ])
    ], style={'border':'1px solid #e2e8f0', 'borderRadius':'8px'})

# ── Layout ────────────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title='Auditra — Prioritas Audit Pengadaan Publik'
)

STYLE_SECTION = {'backgroundColor':'white', 'borderRadius':'8px',
                 'padding':'16px', 'border':'1px solid #e2e8f0', 'marginBottom':'16px'}

app.layout = dbc.Container([

    # Header
    dbc.Row([
        dbc.Col([
            html.H2("🔍 Auditra", style={'fontWeight':'800', 'marginBottom':'2px'}),
            html.P("Sistem Prioritas Audit Pengadaan Publik — Knowledge Graph & Analisis Jaringan",
                   className='text-muted', style={'fontSize':'14px'}),
        ], width=8),
        dbc.Col([
            html.Div([
                html.P("Filter Metode", className='text-muted mb-1', style={'fontSize':'12px'}),
                dcc.Dropdown(
                    id='filter-metode',
                    options=[{'label':'Semua Metode','value':'ALL'}] +
                            [{'label':m,'value':m} for m in sorted(df['metode'].unique())],
                    value='ALL',
                    clearable=False,
                    style={'fontSize':'13px'}
                ),
            ]),
        ], width=4),
    ], className='mb-3 mt-3'),

    # Stat cards
    dbc.Row(id='stat-cards', className='mb-3'),

    # Row 1: Donut + Metode bar + Radar
    dbc.Row([
        dbc.Col([
            html.Div([
                html.P("Distribusi Risiko", style={'fontWeight':'600', 'marginBottom':'8px', 'fontSize':'13px'}),
                dcc.Graph(id='chart-donut', config={'displayModeBar':False}),
            ], style=STYLE_SECTION),
        ], width=3),
        dbc.Col([
            html.Div([
                html.P("Rata-rata RPI per Metode Pengadaan", style={'fontWeight':'600', 'marginBottom':'8px', 'fontSize':'13px'}),
                dcc.Graph(id='chart-metode', config={'displayModeBar':False}),
            ], style=STYLE_SECTION),
        ], width=5),
        dbc.Col([
            html.Div([
                html.P("Profil Sinyal Risiko", style={'fontWeight':'600', 'marginBottom':'8px', 'fontSize':'13px'}),
                dcc.Graph(id='chart-radar', config={'displayModeBar':False}),
            ], style=STYLE_SECTION),
        ], width=4),
    ]),

    # Row 2: Scatter pagu vs RPI + Top provinsi
    dbc.Row([
        dbc.Col([
            html.Div([
                html.P("Distribusi Pagu vs RPI", style={'fontWeight':'600', 'marginBottom':'8px', 'fontSize':'13px'}),
                dcc.Graph(id='chart-scatter', config={'displayModeBar':False}),
            ], style=STYLE_SECTION),
        ], width=7),
        dbc.Col([
            html.Div([
                html.P("Top 20 Provinsi — Rata-rata RPI", style={'fontWeight':'600', 'marginBottom':'8px', 'fontSize':'13px'}),
                dcc.Graph(id='chart-provinsi', config={'displayModeBar':False}),
            ], style=STYLE_SECTION),
        ], width=5),
    ]),

    # Row 3: Knowledge Graph
    dbc.Row([
        dbc.Col([
            html.Div([
                html.P("Knowledge Graph — Jaringan Lembaga & Satker (Top 80 by PageRank)",
                       style={'fontWeight':'600', 'marginBottom':'8px', 'fontSize':'13px'}),
                html.P("🔴 RPI ≥ 50  🟠 RPI 30–50  🔵 RPI < 30  |  Ukuran node = jumlah paket",
                       className='text-muted', style={'fontSize':'11px', 'marginBottom':'8px'}),
                dcc.Graph(id='chart-kg', figure=fig_kg_network(df_nodes, df_edges),
                          config={'displayModeBar':True}),
            ], style=STYLE_SECTION),
        ], width=12),
    ]),

    # Row 4: Tabel prioritas
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Div([
                    html.P("Daftar Paket Prioritas Audit", style={'fontWeight':'600', 'fontSize':'13px', 'margin':'0'}),
                    dcc.Dropdown(
                        id='filter-risk',
                        options=[
                            {'label':'Semua','value':'ALL'},
                            {'label':'🔴 KRITIS','value':'KRITIS'},
                            {'label':'🟠 TINGGI','value':'TINGGI'},
                            {'label':'🟡 SEDANG','value':'SEDANG'},
                        ],
                        value='KRITIS',
                        clearable=False,
                        style={'fontSize':'13px', 'width':'160px'}
                    ),
                ], style={'display':'flex', 'justifyContent':'space-between',
                          'alignItems':'center', 'marginBottom':'12px'}),
                dash_table.DataTable(
                    id='table-prioritas',
                    columns=[
                        {'name':'#','id':'rank'},
                        {'name':'RPI','id':'RPI'},
                        {'name':'Label','id':'risk_label'},
                        {'name':'Paket','id':'paket'},
                        {'name':'Lembaga','id':'lembaga'},
                        {'name':'Metode','id':'metode'},
                        {'name':'Pagu (Rp Miliar)','id':'pagu_miliar'},
                        {'name':'Provinsi','id':'provinsi'},
                    ],
                    style_table={'overflowX':'auto'},
                    style_cell={'fontSize':'12px','padding':'6px 10px',
                                'fontFamily':'system-ui','textAlign':'left',
                                'maxWidth':'300px','overflow':'hidden',
                                'textOverflow':'ellipsis'},
                    style_header={'fontWeight':'600','backgroundColor':'#f8fafc',
                                  'borderBottom':'2px solid #e2e8f0'},
                    style_data_conditional=[
                        {'if':{'filter_query':'{risk_label} = "KRITIS"'},
                         'backgroundColor':'#fef2f2','color':'#991b1b'},
                        {'if':{'filter_query':'{risk_label} = "TINGGI"'},
                         'backgroundColor':'#fff7ed','color':'#9a3412'},
                        {'if':{'filter_query':'{risk_label} = "SEDANG"'},
                         'backgroundColor':'#fefce8','color':'#854d0e'},
                        {'if':{'row_index':'odd'},'backgroundColor':'#fafafa'},
                    ],
                    page_size=15,
                    sort_action='native',
                    filter_action='native',
                    tooltip_data=[],
                    tooltip_duration=None,
                ),
            ], style=STYLE_SECTION),
        ], width=12),
    ]),

    html.P("Auditra © 2026 — Data: SIRUP LKPP | Metode: Knowledge Graph + Rule-based Scoring",
           className='text-muted text-center', style={'fontSize':'11px', 'marginTop':'8px', 'marginBottom':'16px'}),

], fluid=True, style={'backgroundColor':'#f8fafc', 'minHeight':'100vh', 'fontFamily':'system-ui'})

# ── Callbacks ─────────────────────────────────────────────────────────────────

def filter_df(metode):
    if metode == 'ALL':
        return df
    return df[df['metode'] == metode]

@app.callback(
    Output('stat-cards', 'children'),
    Input('filter-metode', 'value'),
)
def update_stats(metode):
    d = filter_df(metode)
    total       = f"{len(d):,}"
    total_pagu  = f"Rp {d['pagu_miliar'].sum():,.1f} M"
    n_kritis    = f"{(d['risk_label']=='KRITIS').sum():,}"
    avg_rpi     = f"{d['RPI'].mean():.1f}"
    n_frag      = f"{(d['s3_fragmentasi'] >= 0.6).sum():,}"

    return [
        dbc.Col(stat_card("Total Paket", total, "dalam filter"), width=2),
        dbc.Col(stat_card("Total Pagu", total_pagu, "miliar rupiah"), width=3),
        dbc.Col(stat_card("Paket KRITIS", n_kritis, "RPI ≥ 70", color='#dc2626'), width=2),
        dbc.Col(stat_card("Rata-rata RPI", avg_rpi, "skala 0–100"), width=2),
        dbc.Col(stat_card("Potensi Split Contract", n_frag, "similarity ≥ 0.6"), width=3),
    ]

@app.callback(
    Output('chart-donut',   'figure'),
    Output('chart-metode',  'figure'),
    Output('chart-scatter', 'figure'),
    Output('chart-provinsi','figure'),
    Output('chart-radar',   'figure'),
    Input('filter-metode',  'value'),
)
def update_charts(metode):
    d = filter_df(metode)
    return (
        fig_risk_donut(d),
        fig_metode_bar(d),
        fig_pagu_scatter(d),
        fig_provinsi_map(d),
        fig_signal_radar(d),
    )

@app.callback(
    Output('table-prioritas', 'data'),
    Input('filter-metode',    'value'),
    Input('filter-risk',      'value'),
)
def update_table(metode, risk):
    d = filter_df(metode)
    if risk != 'ALL':
        d = d[d['risk_label'] == risk]
    d = d.sort_values('RPI', ascending=False).head(500).reset_index(drop=True)
    d['rank'] = d.index + 1
    cols = ['rank','RPI','risk_label','paket','lembaga','metode','pagu_miliar','provinsi']
    return d[cols].to_dict('records')

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("\n✓ Dashboard siap!")
    print("  Buka browser → http://127.0.0.1:8050\n")
    app.run(debug=False, host='0.0.0.0', port=8050)
