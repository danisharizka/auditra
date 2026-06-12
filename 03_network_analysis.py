"""
Auditra - Step 3: Network Analysis & Knowledge Graph
Membangun Knowledge Graph dari relasi pengadaan, menghitung centrality,
dan mendeteksi cluster lembaga berisiko.

Node types:
  - Lembaga
  - Satker
  - Metode
  - JenisPengadaan
  - Lokasi (provinsi)

Edge types:
  - lembaga → satker         (HAS_SATKER)
  - satker → metode          (USES_METHOD)
  - satker → jenisPengadaan  (PROCURES)
  - lembaga → lokasi         (OPERATES_IN)

Output:
  - data_network.csv  : df dengan tambahan kolom network metrics
  - kg_nodes.csv      : semua node + metrics
  - kg_edges.csv      : semua edge + weight
  - kg_summary.txt    : ringkasan untuk esai
"""

import pandas as pd
import numpy as np
import networkx as nx
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

INPUT_PATH        = 'output/data_scored.csv'   # ganti sesuai lokasimu
OUTPUT_DATA       = 'output/data_network.csv'
OUTPUT_NODES      = 'output/kg_nodes.csv'
OUTPUT_EDGES      = 'output/kg_edges.csv'
OUTPUT_SUMMARY    = 'output/kg_summary.txt'

# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading scored data...")
df = pd.read_csv(INPUT_PATH, low_memory=False)
print(f"  Shape: {df.shape}")

# Ekstrak provinsi dari kolom lokasi (format: "Provinsi, Kota (Kab.)")
df['provinsi'] = df['lokasi'].astype(str).str.split(',').str[0].str.strip()

# ── Bangun Knowledge Graph ────────────────────────────────────────────────────
print("\nMembangun Knowledge Graph...")

G = nx.DiGraph()

# Helper: tambah node dengan attributes
def add_node(G, node_id, node_type, **attrs):
    G.add_node(node_id, type=node_type, **attrs)

# Tambah semua node
lembaga_rpi   = df.groupby('lembaga')['RPI'].mean().to_dict()
lembaga_count = df.groupby('lembaga')['id'].count().to_dict()

satker_rpi    = df.groupby('satker')['RPI'].mean().to_dict()
satker_count  = df.groupby('satker')['id'].count().to_dict()

for lembaga in df['lembaga'].unique():
    add_node(G, f"L::{lembaga}", 'lembaga',
             label=lembaga,
             avg_rpi=round(lembaga_rpi.get(lembaga, 0), 2),
             n_paket=lembaga_count.get(lembaga, 0))

for satker in df['satker'].unique():
    add_node(G, f"SK::{satker}", 'satker',
             label=satker,
             avg_rpi=round(satker_rpi.get(satker, 0), 2),
             n_paket=satker_count.get(satker, 0))

for metode in df['metode'].unique():
    add_node(G, f"M::{metode}", 'metode', label=metode)

for jenis in df['jenisPengadaan'].unique():
    add_node(G, f"J::{jenis}", 'jenis', label=jenis)

for prov in df['provinsi'].unique():
    add_node(G, f"P::{prov}", 'provinsi', label=prov)

# Tambah semua edge dengan weight = jumlah paket + avg RPI
print("  Menambah edges...")

# lembaga → satker
ls_weight = df.groupby(['lembaga','satker']).agg(
    n=('id','count'), avg_rpi=('RPI','mean')
).reset_index()
for _, row in ls_weight.iterrows():
    G.add_edge(f"L::{row['lembaga']}", f"SK::{row['satker']}",
               relation='HAS_SATKER', weight=row['n'], avg_rpi=round(row['avg_rpi'],2))

# satker → metode
sm_weight = df.groupby(['satker','metode']).agg(
    n=('id','count'), avg_rpi=('RPI','mean')
).reset_index()
for _, row in sm_weight.iterrows():
    G.add_edge(f"SK::{row['satker']}", f"M::{row['metode']}",
               relation='USES_METHOD', weight=row['n'], avg_rpi=round(row['avg_rpi'],2))

# satker → jenis
sj_weight = df.groupby(['satker','jenisPengadaan']).agg(
    n=('id','count'), avg_rpi=('RPI','mean')
).reset_index()
for _, row in sj_weight.iterrows():
    G.add_edge(f"SK::{row['satker']}", f"J::{row['jenisPengadaan']}",
               relation='PROCURES', weight=row['n'], avg_rpi=round(row['avg_rpi'],2))

# lembaga → provinsi
lp_weight = df.groupby(['lembaga','provinsi']).agg(
    n=('id','count')
).reset_index()
for _, row in lp_weight.iterrows():
    G.add_edge(f"L::{row['lembaga']}", f"P::{row['provinsi']}",
               relation='OPERATES_IN', weight=row['n'])

print(f"  Nodes: {G.number_of_nodes():,}")
print(f"  Edges: {G.number_of_edges():,}")

# ── Hitung Centrality Metrics ─────────────────────────────────────────────────
print("\nMenghitung centrality metrics...")

# Degree centrality (normalized)
degree_cent = nx.degree_centrality(G)

# In-degree centrality (seberapa banyak yang "pointing ke" node ini)
in_degree_cent = nx.in_degree_centrality(G)

# Weighted Degree Centrality — lebih meaningful dari PageRank untuk sparse graph
# = total bobot edge (jumlah paket) yang masuk/keluar dari node
print("  Weighted degree centrality...")
weighted_degree = {}
for node in G.nodes():
    out_weight = sum(d.get('weight', 1) for _, _, d in G.out_edges(node, data=True))
    in_weight  = sum(d.get('weight', 1) for _, _, d in G.in_edges(node, data=True))
    weighted_degree[node] = out_weight + in_weight

# Normalize ke 0-1
max_wd = max(weighted_degree.values()) if weighted_degree else 1
pagerank = {n: v / max_wd for n, v in weighted_degree.items()}  # pakai nama pagerank agar kompatibel

# Risk-weighted influence — untuk lembaga: weighted degree * avg_rpi node
print("  Risk-weighted influence score...")
risk_influence = {}
for node in G.nodes():
    avg_rpi = G.nodes[node].get('avg_rpi', 0)
    wd = weighted_degree.get(node, 0)
    risk_influence[node] = (wd / max_wd) * (avg_rpi / 100)

# Betweenness centrality hanya untuk lembaga & satker nodes (mahal secara komputasi)
print("  Betweenness centrality (subgraph lembaga-satker)...")
lembaga_satker_nodes = [n for n in G.nodes if G.nodes[n]['type'] in ('lembaga', 'satker')]
subG = G.subgraph(lembaga_satker_nodes)
betweenness = nx.betweenness_centrality(subG, weight='weight', normalized=True)
# Isi 0 untuk node yang tidak ada di subgraph
betweenness_full = {n: betweenness.get(n, 0) for n in G.nodes}

# ── Deteksi Komunitas / Cluster ───────────────────────────────────────────────
print("\nDeteksi cluster lembaga berisiko...")

# Buat undirected graph hanya untuk lembaga nodes
lembaga_nodes = [n for n in G.nodes if G.nodes[n]['type'] == 'lembaga']
G_lembaga = G.subgraph(lembaga_nodes).to_undirected()

# Tambah edge antar lembaga yang punya satker overlap (connected via satker)
G_lembaga_full = nx.Graph()
G_lembaga_full.add_nodes_from(lembaga_nodes)

# Lembaga terhubung jika share metode berisiko yang sama di satker
METODE_BERISIKO = {'Penunjukan Langsung', 'Dikecualikan'}
lembaga_berisiko_methods = defaultdict(set)
for _, row in df[df['metode'].isin(METODE_BERISIKO)].iterrows():
    lembaga_berisiko_methods[f"L::{row['lembaga']}"].add(row['metode'])

# Buat edge berdasarkan shared risk profile
lembaga_list = list(lembaga_berisiko_methods.keys())
for i in range(len(lembaga_list)):
    for j in range(i+1, len(lembaga_list)):
        shared = lembaga_berisiko_methods[lembaga_list[i]] & \
                 lembaga_berisiko_methods[lembaga_list[j]]
        if shared:
            G_lembaga_full.add_edge(lembaga_list[i], lembaga_list[j],
                                    weight=len(shared))

# Greedy modularity communities
if G_lembaga_full.number_of_edges() > 0:
    from networkx.algorithms.community import greedy_modularity_communities
    communities = list(greedy_modularity_communities(G_lembaga_full, weight='weight'))
    community_map = {}
    for i, comm in enumerate(communities):
        for node in comm:
            community_map[node] = i
else:
    community_map = {}

print(f"  Cluster terdeteksi: {len(set(community_map.values()))}")

# ── Buat Node DataFrame ───────────────────────────────────────────────────────
print("\nMenyusun output...")

nodes_data = []
for node, attrs in G.nodes(data=True):
    nodes_data.append({
        'node_id':      node,
        'node_type':    attrs.get('type'),
        'label':        attrs.get('label', node),
        'avg_rpi':      attrs.get('avg_rpi', 0),
        'n_paket':      attrs.get('n_paket', 0),
        'degree_cent':    round(degree_cent.get(node, 0), 4),
        'in_degree':      round(in_degree_cent.get(node, 0), 4),
        'pagerank':       round(pagerank.get(node, 0), 6),        # weighted degree normalized
        'risk_influence': round(risk_influence.get(node, 0), 6),  # weighted degree * avg_rpi
        'betweenness':    round(betweenness_full.get(node, 0), 4),
        'cluster_id':     community_map.get(node, -1),
    })

df_nodes = pd.DataFrame(nodes_data)

# ── Buat Edge DataFrame ───────────────────────────────────────────────────────
edges_data = []
for src, dst, attrs in G.edges(data=True):
    edges_data.append({
        'source':   src,
        'target':   dst,
        'relation': attrs.get('relation'),
        'weight':   attrs.get('weight', 1),
        'avg_rpi':  attrs.get('avg_rpi', 0),
    })

df_edges = pd.DataFrame(edges_data)

# ── Merge network metrics ke data utama ──────────────────────────────────────
lembaga_metrics = df_nodes[df_nodes['node_type']=='lembaga'][
    ['label','pagerank','risk_influence','betweenness','degree_cent','cluster_id']
].rename(columns={
    'label':          'lembaga',
    'pagerank':       'kg_pagerank',       # weighted degree normalized
    'risk_influence': 'kg_risk_influence', # weighted degree * avg_rpi (S7 baru)
    'betweenness':    'kg_betweenness',
    'degree_cent':    'kg_degree',
    'cluster_id':     'kg_cluster',
})

df = df.merge(lembaga_metrics, on='lembaga', how='left')

# Update S7 dengan risk_influence (weighted degree * avg_rpi — lebih meaningful)
if 'kg_risk_influence' in df.columns:
    max_ri = df['kg_risk_influence'].max()
    if max_ri > 0:
        df['s7_reputasi'] = df['kg_risk_influence'] / max_ri
        # Recalculate RPI dengan S7 yang baru
        WEIGHTS = {
            's1_metode':       0.20,
            's2_pagu_anomali': 0.20,
            's3_fragmentasi':  0.15,
            's4_konsentrasi':  0.15,
            's5_umkm':         0.10,
            's6_dana_metode':  0.10,
            's7_reputasi':     0.10,
        }
        df['RPI'] = sum(df[col] * w for col, w in WEIGHTS.items())
        df['RPI'] = (df['RPI'] * 100).round(2)

        def label_rpi(score):
            if score >= 70: return 'KRITIS'
            if score >= 50: return 'TINGGI'
            if score >= 30: return 'SEDANG'
            return 'RENDAH'
        df['risk_label'] = df['RPI'].apply(label_rpi)

# ── Summary untuk Esai ────────────────────────────────────────────────────────
top_lembaga_pr = df_nodes[df_nodes['node_type']=='lembaga']\
    .sort_values('risk_influence', ascending=False).head(10)

top_lembaga_rpi = df_nodes[df_nodes['node_type']=='lembaga']\
    .sort_values('avg_rpi', ascending=False).head(10)

summary = f"""
============================================================
AUDITRA - KNOWLEDGE GRAPH SUMMARY
============================================================

STATISTIK GRAPH
  Total nodes        : {G.number_of_nodes():,}
  Total edges        : {G.number_of_edges():,}
  Density            : {nx.density(G):.6f}

DISTRIBUSI NODE
{df_nodes['node_type'].value_counts().to_string()}

DISTRIBUSI RISK LABEL (final, post-KG)
{df['risk_label'].value_counts().to_string()}

TOP 10 LEMBAGA - RISK INFLUENCE TERTINGGI (weighted degree * avg_rpi)
{top_lembaga_pr[['label','risk_influence','avg_rpi','n_paket']].to_string(index=False)}

TOP 10 LEMBAGA - RATA-RATA RPI TERTINGGI
{top_lembaga_rpi[['label','avg_rpi','n_paket','risk_influence']].to_string(index=False)}

CLUSTER LEMBAGA BERISIKO
  Jumlah cluster     : {len(set(community_map.values()))}
  Lembaga per cluster:
{pd.Series(community_map).value_counts().to_string()}

============================================================
"""

print(summary)

# ── Save ──────────────────────────────────────────────────────────────────────
df.to_csv(OUTPUT_DATA, index=False)
df_nodes.to_csv(OUTPUT_NODES, index=False)
df_edges.to_csv(OUTPUT_EDGES, index=False)
with open(OUTPUT_SUMMARY, 'w') as f:
    f.write(summary)

print(f"✓ data_network.csv  → {OUTPUT_DATA}")
print(f"✓ kg_nodes.csv      → {OUTPUT_NODES}")
print(f"✓ kg_edges.csv      → {OUTPUT_EDGES}")
print(f"✓ kg_summary.txt    → {OUTPUT_SUMMARY}")