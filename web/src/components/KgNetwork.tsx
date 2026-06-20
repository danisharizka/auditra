import { useEffect, useRef, useState } from "react";
import { DataSet } from "vis-data";
import { Network } from "vis-network";
import { useTheme } from "../theme/ThemeContext";

interface Props {
  nodes: Record<string, unknown>[];
  edges: Record<string, unknown>[];
}

export default function KgNetwork({ nodes, edges }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const { colors } = useTheme();
  const [physicsOn, setPhysicsOn] = useState(true);

  useEffect(() => {
    if (!ref.current || nodes.length === 0) return;

    setPhysicsOn(true);

    const visNodes = new DataSet(
      nodes.map((n) => {
        const isHigh = Number(n.avg_rpi) >= 30;
        return {
          id: n.node_id as string,
          label: String(n.label || n.node_id).slice(0, 32),
          title: `${n.label}\nAvg RPI: ${n.avg_rpi}\nPaket: ${n.n_paket}`,
          color: isHigh
            ? { background: "#f97316", border: "#c2410c", highlight: { background: "#fb923c", border: "#ea580c" } }
            : { background: "#3b82f6", border: "#1d4ed8", highlight: { background: "#60a5fa", border: "#2563eb" } },
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
        };
      })
    );

    const visEdges = new DataSet(
      edges.map((e, idx) => ({
        id: idx,
        from: e.source as string,
        to: e.target as string,
        width: Math.min(3, Math.log(Number(e.weight || 1) + 1)),
        color: { color: colors.border, opacity: 0.85, highlight: colors.accentOrange },
        smooth: { type: "cubicBezier", forceDirection: "none", roundness: 0.2 },
      }))
    );

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
          tooltipDelay: 120,
          dragNodes: true,
          dragView: true,
          zoomView: true,
          navigationButtons: true,
          keyboard: { enabled: true, bindToWindow: false },
          zoomSpeed: 0.3,
        },
        nodes: { shape: "dot", scaling: { min: 12, max: 36 } },
        edges: { arrows: { to: { enabled: true, scaleFactor: 0.45 } } },
      }
    );

    network.on("stabilizationIterationsDone", () => {
      network.setOptions({ physics: { enabled: false } });
      setPhysicsOn(false);
    });

    networkRef.current = network;
    return () => {
      network.destroy();
      networkRef.current = null;
    };
  }, [nodes, edges, colors]);

  const handleFit = () =>
    networkRef.current?.fit({ animation: { duration: 400, easingFunction: "easeInOutQuad" } });

  const handleTogglePhysics = () => {
    const next = !physicsOn;
    networkRef.current?.setOptions({ physics: { enabled: next } });
    setPhysicsOn(next);
  };

  if (nodes.length === 0) {
    return (
      <div className="flex h-[460px] items-center justify-center text-muted">
        Knowledge Graph belum tersedia — jalankan 03_network_analysis.py
      </div>
    );
  }

  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-2">
        <button type="button" onClick={handleFit} className="btn-secondary text-xs">
          ⊡ Fit to view
        </button>
        <button type="button" onClick={handleTogglePhysics} className="btn-secondary text-xs">
          {physicsOn ? "⏸ Kunci layout" : "▶ Gerakkan lagi"}
        </button>
        <span className="self-center text-[11px] text-muted">
          Scroll = zoom · Drag background = geser · Drag node = pindah
        </span>
      </div>
      <div ref={ref} className="kg-canvas" />
    </div>
  );
}
