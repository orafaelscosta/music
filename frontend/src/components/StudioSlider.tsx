"use client";

interface StudioSliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  onChange: (value: number) => void;
  color?: string;
}

export default function StudioSlider({
  label,
  value,
  min,
  max,
  step = 1,
  unit = "",
  onChange,
  color = "brand",
}: StudioSliderProps) {
  const percent = ((value - min) / (max - min)) * 100;

  const colorMap: Record<string, { track: string; thumb: string; text: string }> = {
    brand: { track: "bg-brand-500", thumb: "border-brand-400 shadow-brand-500/30", text: "text-brand-400" },
    purple: { track: "bg-purple-500", thumb: "border-purple-400 shadow-purple-500/30", text: "text-purple-400" },
    emerald: { track: "bg-emerald-500", thumb: "border-emerald-400 shadow-emerald-500/30", text: "text-emerald-400" },
    amber: { track: "bg-amber-500", thumb: "border-amber-400 shadow-amber-500/30", text: "text-amber-400" },
    rose: { track: "bg-rose-500", thumb: "border-rose-400 shadow-rose-500/30", text: "text-rose-400" },
    cyan: { track: "bg-cyan-500", thumb: "border-cyan-400 shadow-cyan-500/30", text: "text-cyan-400" },
  };

  const c = colorMap[color] || colorMap.brand;

  return (
    <div className="group">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-medium text-gray-400 group-hover:text-gray-300 transition-colors">
          {label}
        </span>
        <span className={`text-xs font-mono ${c.text}`}>
          {value}{unit}
        </span>
      </div>
      <div className="relative h-6 flex items-center">
        {/* Track background */}
        <div className="absolute inset-x-0 h-1.5 rounded-full bg-gray-800" />
        {/* Track fill */}
        <div
          className={`absolute h-1.5 rounded-full ${c.track} transition-all`}
          style={{ width: `${percent}%` }}
        />
        {/* Native input */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="absolute inset-x-0 h-6 w-full cursor-pointer opacity-0"
        />
        {/* Custom thumb */}
        <div
          className={`pointer-events-none absolute h-4 w-4 rounded-full border-2 bg-gray-900 ${c.thumb} shadow-lg transition-all`}
          style={{ left: `calc(${percent}% - 8px)` }}
        />
      </div>
    </div>
  );
}
