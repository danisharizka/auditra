import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DataSet } from "vis-data";
import { Network } from "vis-network";
import ColorLegend from "./ColorLegend";
import { useTheme } from "../theme/ThemeContext";
import { formatNodeLabel, formatRelation, isHighRisk, nodeTypeLabel } from "../utils/kgLabels";

interface Props {
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
}

interface EdgeMeta {
  id: number;
  from: string;
  to: string;
  relation: string;
  weight: number;
}

interface ConnectionRow {
  direction: "keluar" | "masuk";
  peerLabel: string;
  peerType: string;
  relation: string;
  weight: number;
}

const HIGH_COLOR = "#f97316";
const LOW_COLOR = "#3b82f6";
const DIM_NODE_OPACITY = 0.1;
const DIM_EDGE_OPACITY = 0.05;

function edgeColors(colors: { kgEdge: string; kgEdgeHover: string }) {
  return {
    color: colors.kgEdge,
    opacity: 0.85,
    hover: colors.kgEdgeHover,
    highlight: colors.kgEdgeHover,
  };
}

function dimNodeStyle(base: Record<string, unknown>, colors: { kgLabel: string }) {
  const high = Boolean(base._high);
  return {
    id: base.id,
    color: {
      background: high ? "rgba(249,115,22,0.18)" : "rgba(59,130,246,0.18)",
      border: high ? "rgba(194,65,12,0.22)" : "rgba(29,78,216,0.22)",
    },
    font: {
      ...(base.font as object),
      color: colors.kgLabel,
      strokeWidth: 2,
      background: "transparent",
    },
    borderWidth: 1,
    size: Math.max(10, Number(base.size) * 0.82),
    opacity: DIM_NODE_OPACITY,
  };
}

function buildKgSummary(nodes: Record<string, unknown>[], edges: Record<string, unknown>[]): string {
  const lembaga = nodes.filter((n) => n.node_type === "lembaga").length;
  const satker = nodes.filter((n) => n.node_type === "satker").length;
  const high = nodes.filter((n) => isHighRisk(n.avg_rpi)).length;
  const low = nodes.length - high;

  const top = [...nodes]
    .filter((n) => n.node_type === "lembaga")
    .sort((a, b) => Number(b.risk_influence ?? 0) - Number(a.risk_influence ?? 0))
    .slice(0, 2)
    .map((n) => formatNodeLabel(n.label, n.node_type))
    .join(" & ");

  return [
    `Graf ini menampilkan ${lembaga} lembaga dan ${satker} satker yang saling terhubung melalui ${edges.length} relasi pengadaan.`,
    `Node oranye (${high}): rata-rata RPI ≥ 30 (prioritas audit). Node biru (${low}): RPI di bawah ambang.`,
    top
      ? `Lembaga dengan pengaruh risiko tertinggi dalam subgraf: ${top}.`
      : "",
    "Arahkan kursor ke node untuk sorot relasi · klik untuk panel detail (keluar ↑ / masuk ↓).",
  ]
    .filter(Boolean)
    .join(" ");
}

export default function KgNetwork({ nodes, edges }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const nodesDsRef = useRef<DataSet<Record<string, unknown>> | null>(null);
  const edgesDsRef = useRef<DataSet<Record<string, unknown>> | null>(null);
  const nodeMapRef = useRef<Map<string, Record<string, unknown>>>(new Map());
  const edgeMetaRef = useRef<EdgeMeta[]>([]);
  const nodeBaseRef = useRef<Map<string, Record<string, unknown>>>(new Map());
  const selectedIdRef = useRef<string | null>(null);
  const { colors } = useTheme();
  const [physicsOn, setPhysicsOn] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);

  const summary = useMemo(() => buildKgSummary(nodes, edges), [nodes, edges]);

  const selectedNode = useMemo(
    () => (selectedId ? nodes.find((n) => String(n.node_id) === selectedId) : null),
    [selectedId, nodes]
  );

  const connections = useMemo((): ConnectionRow[] => {
    if (!selectedId || !selectedNode) return [];

    const nodeMap = new Map(nodes.map((n) => [String(n.node_id), n]));

    const rows: ConnectionRow[] = [];
    for (const e of edgeMetaRef.current) {
      if (e.from === selectedId) {
        const peer = nodeMap.get(e.to);
        rows.push({
          direction: "keluar",
          peerLabel: formatNodeLabel(peer?.label, peer?.node_type),
          peerType: nodeTypeLabel(peer?.node_type),
          relation: formatRelation(e.relation),
          weight: e.weight,
        });
      } else if (e.to === selectedId) {
        const peer = nodeMap.get(e.from);
        rows.push({
          direction: "masuk",
          peerLabel: formatNodeLabel(peer?.label, peer?.node_type),
          peerType: nodeTypeLabel(peer?.node_type),
          relation: formatRelation(e.relation),
          weight: e.weight,
        });
      }
    }
    return rows.sort((a, b) => b.weight - a.weight).slice(0, 12);
  }, [selectedId, selectedNode, nodes, edges]);

  const resetGraphVisuals = useCallback(() => {
    const nodesDs = nodesDsRef.current;
    const edgesDs = edgesDsRef.current;
    if (!nodesDs || !edgesDs) return;

    nodeBaseRef.current.forEach((base) => {
      nodesDs.update(base);
    });
    edgeMetaRef.current.forEach((e) => {
      edgesDs.update({
        id: e.id,
        color: edgeColors(colors),
        width: Math.min(4, Math.max(2, Math.log(e.weight + 1))),
      });
    });
    networkRef.current?.unselectAll();
  }, [colors]);

  const applyNodeFocus = useCallback(
    (nodeId: string | null, mode: "hover" | "select") => {
      const network = networkRef.current;
      const nodesDs = nodesDsRef.current;
      const edgesDs = edgesDsRef.current;
      if (!nodesDs || !edgesDs) return;

      if (!nodeId) {
        resetGraphVisuals();
        return;
      }

      const connectedEdges = (network?.getConnectedEdges(nodeId) ?? []) as number[];
      const focusNodes = new Set<string>([
        nodeId,
        ...((network?.getConnectedNodes(nodeId) ?? []) as string[]),
      ]);
      const focusEdgeSet = new Set(connectedEdges);
      const accentEdge = mode === "select" ? HIGH_COLOR : colors.kgEdgeHover;

      nodeBaseRef.current.forEach((base, id) => {
        if (focusNodes.has(id)) {
          const isCenter = id === nodeId;
          nodesDs.update({
            ...base,
            opacity: 1,
            borderWidth: isCenter ? 3 : 2,
            size: isCenter ? Number(base.size) * 1.1 : base.size,
          });
        } else {
          nodesDs.update(dimNodeStyle(base, colors));
        }
      });

      edgeMetaRef.current.forEach((e) => {
        if (focusEdgeSet.has(e.id)) {
          edgesDs.update({
            id: e.id,
            color: { color: accentEdge, opacity: 1, hover: accentEdge, highlight: accentEdge },
            width: mode === "select" ? 4 : 3,
          });
        } else {
          edgesDs.update({
            id: e.id,
            color: {
              color: colors.kgEdge,
              opacity: DIM_EDGE_OPACITY,
              hover: colors.kgEdgeHover,
              highlight: colors.kgEdgeHover,
            },
            width: 1,
          });
        }
      });

      if (mode === "select") {
        network?.selectNodes([nodeId]);
        network?.selectEdges(connectedEdges);
      } else {
        network?.unselectAll();
      }
    },
    [colors, resetGraphVisuals]
  );

  useEffect(() => {
    if (!ref.current || nodes.length === 0) return;

    setPhysicsOn(true);
    setSelectedId(null);

    const nodeMap = new Map<string, Record<string, unknown>>();
    nodes.forEach((n) => nodeMap.set(String(n.node_id), n));
    nodeMapRef.current = nodeMap;
    nodeBaseRef.current.clear();

    const visNodes = new DataSet(
      nodes.map((n) => {
        const id = String(n.node_id);
        const high = isHighRisk(n.avg_rpi);
        const label = formatNodeLabel(n.label, n.node_type);
        const base = {
          id,
          label: label.length > 28 ? `${label.slice(0, 26)}…` : label,
          title: `${nodeTypeLabel(n.node_type)}: ${label}\nRPI rata-rata: ${n.avg_rpi}\nJumlah paket: ${n.n_paket}`,
          color: high
            ? { background: HIGH_COLOR, border: "#c2410c", highlight: { background: "#fb923c", border: "#ea580c" } }
            : { background: LOW_COLOR, border: "#1d4ed8", highlight: { background: "#60a5fa", border: "#2563eb" } },
          font: {
            color: colors.kgLabel,
            size: 13,
            face: "Inter, system-ui, sans-serif",
            strokeWidth: 4,
            strokeColor: colors.kgLabelStroke,
            background: colors.kgLabelBg,
          },
          size: Math.max(16, Math.min(32, Number(n.n_paket || 1) / 400)),
          borderWidth: 2,
          opacity: 1,
          _high: high,
        };
        nodeBaseRef.current.set(id, base);
        return base;
      })
    );

    const edgeMeta: EdgeMeta[] = edges.map((e, idx) => ({
      id: idx,
      from: String(e.source),
      to: String(e.target),
      relation: String(e.relation ?? ""),
      weight: Number(e.weight || 1),
    }));
    edgeMetaRef.current = edgeMeta;

    const visEdges = new DataSet(
      edgeMeta.map((e) => ({
        id: e.id,
        from: e.from,
        to: e.to,
        width: Math.min(4, Math.max(2, Math.log(e.weight + 1))),
        color: edgeColors(colors),
        smooth: { type: "cubicBezier", forceDirection: "none", roundness: 0.2 },
      }))
    );

    nodesDsRef.current = visNodes;
    edgesDsRef.current = visEdges;

    const network = new Network(
      ref.current,
      { nodes: visNodes as never, edges: visEdges as never },
      {
        physics: {
          enabled: true,
          stabilization: { iterations: 100, fit: true },
          barnesHut: {
            gravitationalConstant: -3000,
            centralGravity: 0.15,
            springLength: 140,
            springConstant: 0.04,
            damping: 0.15,
          },
        },
        interaction: {
          hover: true,
          hoverConnectedEdges: false,
          tooltipDelay: 120,
          dragNodes: true,
          dragView: true,
          zoomView: true,
          navigationButtons: true,
          keyboard: { enabled: true, bindToWindow: false },
          zoomSpeed: 0.3,
          selectConnectedEdges: false,
        },
        nodes: { shape: "dot", scaling: { min: 12, max: 36 } },
        edges: {
          color: edgeColors(colors),
          arrows: { to: { enabled: true, scaleFactor: 0.75, type: "arrow" } },
        },
      }
    );

    network.on("stabilizationIterationsDone", () => {
      network.setOptions({ physics: { enabled: false } });
      setPhysicsOn(false);
    });

    network.on("hoverNode", (params) => {
      const nodeId = params.node as string;
      applyNodeFocus(nodeId, "hover");
    });

    network.on("blurNode", () => {
      const sel = selectedIdRef.current;
      if (sel) applyNodeFocus(sel, "select");
      else resetGraphVisuals();
    });

    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0] as string;
        setSelectedId(nodeId);
        applyNodeFocus(nodeId, "select");
      } else {
        setSelectedId(null);
        resetGraphVisuals();
      }
    });

    networkRef.current = network;
    return () => {
      network.destroy();
      networkRef.current = null;
      nodesDsRef.current = null;
      edgesDsRef.current = null;
      nodeBaseRef.current.clear();
    };
  }, [nodes, edges, colors, applyNodeFocus, resetGraphVisuals]);

  const handleFit = () =>
    networkRef.current?.fit({ animation: { duration: 400, easingFunction: "easeInOutQuad" } });

  const handleTogglePhysics = () => {
    const next = !physicsOn;
    networkRef.current?.setOptions({ physics: { enabled: next } });
    setPhysicsOn(next);
  };

  const handleClearSelection = () => {
    setSelectedId(null);
    resetGraphVisuals();
  };

  if (nodes.length === 0) {
    return (
      <div className="flex h-[460px] items-center justify-center text-muted">
        Knowledge Graph belum tersedia — jalankan 03_network_analysis.py
      </div>
    );
  }

  const selectedLabel = selectedNode
    ? formatNodeLabel(selectedNode.label, selectedNode.node_type)
    : null;

  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-2">
        <button type="button" onClick={handleFit} className="btn-secondary text-xs">
          Sesuaikan tampilan
        </button>
        <button type="button" onClick={handleTogglePhysics} className="btn-secondary text-xs">
          {physicsOn ? "Kunci layout" : "Gerakkan lagi"}
        </button>
        {selectedId && (
          <button type="button" onClick={handleClearSelection} className="btn-secondary text-xs">
            Hapus pilihan
          </button>
        )}
        <span className="self-center text-[11px] text-muted">
          Arahkan ke node · klik detail · scroll zoom · drag geser
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-12">
        <div className={selectedId ? "relative lg:col-span-8" : "relative lg:col-span-12"}>
          <div ref={ref} className="kg-canvas" />
          <ColorLegend
            className="pointer-events-none absolute left-2 top-2 z-10 !flex-col !gap-x-0 !gap-y-1 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-panel)]/92 px-2.5 py-1.5 shadow-sm backdrop-blur-sm"
            items={[
              { color: LOW_COLOR, label: "Biru — RPI < 30 (risiko rendah–sedang)" },
              { color: HIGH_COLOR, label: "Oranye — RPI ≥ 30 (prioritas audit)" },
            ]}
          />
        </div>

        {selectedId && selectedLabel && (
          <div className="panel lg:col-span-4 !p-3">
            <h3 className="mb-1 text-xs font-semibold text-primary">
              Relasi · {nodeTypeLabel(selectedNode?.node_type)}
            </h3>
            <p className="mb-2 text-[11px] font-medium text-primary">{selectedLabel}</p>
            {connections.length === 0 ? (
              <p className="text-[11px] text-muted">Tidak ada relasi dalam subgraf ini.</p>
            ) : (
              <ul className="max-h-[400px] space-y-1.5 overflow-y-auto text-[11px]">
                {connections.map((c, i) => (
                  <li
                    key={`${c.direction}-${c.peerLabel}-${i}`}
                    className="rounded border border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-2 py-1.5"
                  >
                    <span className="font-semibold" style={{ color: c.direction === "keluar" ? HIGH_COLOR : LOW_COLOR }}>
                      {c.direction === "keluar" ? "→ Keluar" : "← Masuk"}
                    </span>
                    <span className="text-muted"> {c.direction === "keluar" ? "ke" : "dari"} </span>
                    <span className="font-medium text-primary">{c.peerType}</span>
                    <span className="text-primary"> {c.peerLabel}</span>
                    <br />
                    <span className="text-muted">{c.relation} · {c.weight.toLocaleString("id-ID")} paket</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <p className="mt-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-3 py-2 text-[11px] leading-relaxed text-muted">
        <span className="font-semibold text-primary">Kesimpulan: </span>
        {summary}
      </p>
    </div>
  );
}
