"use client";
import React, { useEffect, useMemo, useState } from "react";
import { Responsive, WidthProvider } from "react-grid-layout";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, RefreshCw, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

const ResponsiveGridLayout = WidthProvider(Responsive);

type PanelState = { id: string; parameter: string };

const PARAMETERS = [
  { id: "sea_level", name: "Sea Level", tileURL: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" },
  { id: "chlorophyll", name: "Chlorophyll", tileURL: "https://{s}.tile.openstreetmap.de/{z}/{x}/{y}.png" },
  { id: "sea_height", name: "Sea Height", tileURL: "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png" },
  { id: "wave_height", name: "Wave Height", tileURL: "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png" },
];

const NINGALOO_BOUNDS: [number, number][] = [[-25, 111], [-20, 114]];
const uid = () => Math.random().toString(36).slice(2, 9);

function FitToBounds({ bounds }: { bounds: [number, number][] }) {
  const map = useMap();
  useEffect(() => { map.fitBounds(bounds as any, { padding: [12, 12] as any }); }, []);
  return null;
}

function MapPanel({
  id,
  parameter,
  onChange,
  onClose,
  panelCount,
}: {
  id: string;
  parameter: string;
  onChange: (id: string, patch: Partial<PanelState>) => void;
  onClose: (id: string) => void;
  panelCount: number;
}) {
  const paramMeta = useMemo(() => PARAMETERS.find((p) => p.id === parameter)!, [parameter]);
  return (
    <Card className="h-full w-full overflow-hidden rounded-2xl border border-white/20 bg-white/10 backdrop-blur-md shadow-lg">
      <CardHeader className="py-2 px-3 flex flex-row items-center justify-between gap-2 bg-white/5">
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="secondary" size="sm" className="rounded-xl">
                {paramMeta?.name || "Parameter"}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              {PARAMETERS.map((p) => (
                <DropdownMenuItem key={p.id} onClick={() => onChange(id, { parameter: p.id })}>
                  {p.name}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        {panelCount > 1 && (
          <Button variant="ghost" size="icon" onClick={() => onClose(id)} className="hover:bg-white/10">
            <X className="h-4 w-4" />
          </Button>
        )}
      </CardHeader>
      <CardContent className="h-[calc(100%-40px)] p-0">
        <MapContainer className="h-full w-full" center={[-22.5, 112.5]} zoom={6} zoomControl={true}>
          <FitToBounds bounds={NINGALOO_BOUNDS as any} />
          <TileLayer url={paramMeta.tileURL} />
        </MapContainer>
      </CardContent>
    </Card>
  );
}

export default function UWAOceanDashboard() {
  const [panels, setPanels] = useState<PanelState[]>([{ id: uid(), parameter: "sea_level" }]);

  const computeLayout = (ids: string[]) => {
    if (ids.length === 2) return [
      { i: ids[0], x: 0, y: 0, w: 6, h: 14 },
      { i: ids[1], x: 6, y: 0, w: 6, h: 14 },
    ];
    if (ids.length >= 3) return [
      { i: ids[0], x: 0, y: 0, w: 6, h: 14 },
      { i: ids[1], x: 6, y: 0, w: 6, h: 7 },
      { i: ids[2], x: 6, y: 7, w: 6, h: 7 },
    ];
    return [{ i: ids[0], x: 0, y: 0, w: 12, h: 14 }];
  };
  const [layout, setLayout] = useState<any[]>(computeLayout(panels.map(p=>p.id)));
  useEffect(() => { setLayout(computeLayout(panels.map(p=>p.id))); }, [panels.length]);

  const addPanel = () => { if (panels.length < 3) setPanels([...panels, { id: uid(), parameter: "chlorophyll" }]); };
  const removePanel = (id: string) => setPanels((p) => p.filter((x) => x.id !== id));
  const updatePanel = (id: string, patch: Partial<PanelState>) => setPanels((prev) => prev.map((p) => (p.id === id ? { ...p, ...patch } : p)));
  const refreshAll = () => setPanels((prev) => prev.map((p) => ({ ...p })));

  return (
    <div className="min-h-screen text-white">
      {/* Floating top bar */}
      <div className="fixed top-0 inset-x-0 z-50 border-b border-white/10 bg-black/20 backdrop-blur-md">
        <div className="max-w-screen-2xl mx-auto px-4 py-2 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-xl bg-white/20 text-white flex items-center justify-center font-bold">U</div>
              <span className="font-semibold text-white">UWA Ocean • Satellite Visualisation</span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                  variant="outline"
                size="sm"
                onClick={refreshAll}
                className="bg-white/10 text-white border-white/20 hover:bg-white/20"
              >
              <RefreshCw className="h-4 w-4 mr-1" /> Reload
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={addPanel}
        disabled={panels.length >= 3}
        className="bg-white/10 text-white border-white/20 hover:bg-white/20"
      >
        <Plus className="h-4 w-4 mr-1" /> Add Map
      </Button>
    </div>
  </div>
</div>

      {/* Main map(s) */}
      {panels.length === 1 ? (
        <div className="pt-14 w-full h-[100vh]">
          <MapContainer className="w-full h-full" center={[-22.5, 112.5]} zoom={6} zoomControl={true}>
            <FitToBounds bounds={NINGALOO_BOUNDS as any} />
            <TileLayer url={PARAMETERS.find((p) => p.id === panels[0].parameter)!.tileURL} />
          </MapContainer>
        </div>
      ) : (
        <div className="pt-14 px-2 w-full h-[calc(100vh-56px)]">
  <ResponsiveGridLayout
    className="layout h-full"
    rowHeight={Math.floor(window.innerHeight / 14)} // each panel h=14 rows = full height
    cols={{ lg: 12, md: 12, sm: 6, xs: 4, xxs: 2 }}
    layout={layout as any}
    isDraggable={false}
    isResizable={false}
    margin={[10, 10]} // small spacing between panels
    containerPadding={[10, 10]}
  >


            {panels.map((panel) => (
              <div key={panel.id} data-grid={layout.find((l: any) => l.i === panel.id) || { x: 0, y: 0, w: 6, h: 14 }}>
                <MapPanel id={panel.id} parameter={panel.parameter} onChange={updatePanel} onClose={removePanel} panelCount={panels.length} />
              </div>
            ))}
          </ResponsiveGridLayout>
        </div>
      )}

      {/* Floating add button */}
      <AnimatePresence>
        {panels.length < 3 && (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 12 }} className="fixed bottom-20 right-6 z-50">
            <Button onClick={addPanel} size="lg" className="rounded-full h-14 w-14 shadow-lg bg-white/20 hover:bg-white/30 border border-white/30">
              <Plus />
            </Button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating footer */}
      <div className="fixed bottom-4 right-4 z-40">
        <div className="flex items-center gap-2 rounded-xl px-3 py-2 bg-black/30 backdrop-blur-md border border-white/20 text-xs shadow-lg">
          <span>© 2025 UWA Ocean • ™ UWA</span>
        </div>
      </div>
    </div>
  );
}
