"use client";

interface StyleCardProps {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  selected: boolean;
  onClick: () => void;
  color?: string;
}

export default function StyleCard({
  label,
  description,
  icon,
  selected,
  onClick,
  color = "brand",
}: StyleCardProps) {
  const colorMap: Record<string, { border: string; bg: string; text: string; glow: string }> = {
    brand: { border: "border-brand-500", bg: "bg-brand-500/10", text: "text-brand-400", glow: "shadow-brand-500/20" },
    purple: { border: "border-purple-500", bg: "bg-purple-500/10", text: "text-purple-400", glow: "shadow-purple-500/20" },
    emerald: { border: "border-emerald-500", bg: "bg-emerald-500/10", text: "text-emerald-400", glow: "shadow-emerald-500/20" },
    amber: { border: "border-amber-500", bg: "bg-amber-500/10", text: "text-amber-400", glow: "shadow-amber-500/20" },
    rose: { border: "border-rose-500", bg: "bg-rose-500/10", text: "text-rose-400", glow: "shadow-rose-500/20" },
    cyan: { border: "border-cyan-500", bg: "bg-cyan-500/10", text: "text-cyan-400", glow: "shadow-cyan-500/20" },
  };

  const c = colorMap[color] || colorMap.brand;

  return (
    <button
      type="button"
      onClick={onClick}
      className={`group relative overflow-hidden rounded-xl border p-4 text-left transition-all duration-200 ${
        selected
          ? `${c.border} ${c.bg} shadow-lg ${c.glow}`
          : "border-gray-800 bg-gray-900/50 hover:border-gray-700 hover:bg-gray-900"
      }`}
    >
      <div className={`mb-2 text-2xl ${selected ? c.text : "text-gray-600 group-hover:text-gray-400"} transition-colors`}>
        {icon}
      </div>
      <h4 className={`text-sm font-semibold ${selected ? "text-white" : "text-gray-300"}`}>
        {label}
      </h4>
      <p className="mt-0.5 text-xs text-gray-500 line-clamp-2">
        {description}
      </p>
      {selected && (
        <div className={`absolute right-2 top-2 h-2 w-2 rounded-full ${c.border.replace("border-", "bg-")} animate-pulse`} />
      )}
    </button>
  );
}
