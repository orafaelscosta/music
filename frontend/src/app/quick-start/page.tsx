"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, useRef } from "react";
import { api } from "@/lib/api";
import { showToast } from "@/components/Toast";
import StudioSlider from "@/components/StudioSlider";
import StyleCard from "@/components/StyleCard";
import VoicePreviewButton from "@/components/VoicePreviewButton";
import {
  Upload,
  Zap,
  FileAudio,
  Loader2,
  X,
  Music,
  Mic,
  Waves,
  Wind,
  Flame,
  Snowflake,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Volume2,
  Radio,
  Gauge,
  Theater,
  User,
  Users,
} from "lucide-react";

// Vocal style presets
const VOCAL_STYLES = [
  {
    id: "operatic",
    label: "Operístico",
    description: "Vocal lírico, projeção clássica",
    icon: <Theater className="h-6 w-6" />,
    color: "purple",
    params: { breathiness: 15, tension: 70, energy: 80, vibrato: 75, pitch_range: 85, gender: 50 },
  },
  {
    id: "pop",
    label: "Pop",
    description: "Vocal limpo, moderno e direto",
    icon: <Radio className="h-6 w-6" />,
    color: "brand",
    params: { breathiness: 30, tension: 45, energy: 65, vibrato: 40, pitch_range: 60, gender: 50 },
  },
  {
    id: "breathy",
    label: "Aéreo",
    description: "Suave, sussurrado, intimista",
    icon: <Wind className="h-6 w-6" />,
    color: "cyan",
    params: { breathiness: 80, tension: 20, energy: 35, vibrato: 25, pitch_range: 45, gender: 55 },
  },
  {
    id: "powerful",
    label: "Potente",
    description: "Voz forte, belting, intensa",
    icon: <Flame className="h-6 w-6" />,
    color: "rose",
    params: { breathiness: 10, tension: 80, energy: 95, vibrato: 55, pitch_range: 90, gender: 45 },
  },
  {
    id: "ethereal",
    label: "Etéreo",
    description: "Delicado, reverberante, ambient",
    icon: <Snowflake className="h-6 w-6" />,
    color: "emerald",
    params: { breathiness: 60, tension: 25, energy: 40, vibrato: 50, pitch_range: 70, gender: 60 },
  },
  {
    id: "custom",
    label: "Personalizado",
    description: "Ajuste cada parâmetro manualmente",
    icon: <Sparkles className="h-6 w-6" />,
    color: "amber",
    params: { breathiness: 40, tension: 50, energy: 60, vibrato: 45, pitch_range: 65, gender: 50 },
  },
];

// Mix presets
const MIX_STYLES = [
  { id: "balanced", label: "Equilibrado", description: "Mix natural e equilibrado" },
  { id: "vocal_forward", label: "Vocal em Destaque", description: "Vocal acima do instrumental" },
  { id: "ambient", label: "Ambiente", description: "Reverb largo, espacial" },
  { id: "radio", label: "Radio Ready", description: "Comprimido, alto, broadcast" },
  { id: "dry", label: "Seco", description: "Mínimo de efeitos, natural" },
];

const LANGUAGES = [
  { code: "it", label: "Italiano", flag: "IT" },
  { code: "pt", label: "Português", flag: "PT" },
  { code: "en", label: "English", flag: "EN" },
  { code: "es", label: "Español", flag: "ES" },
  { code: "fr", label: "Français", flag: "FR" },
  { code: "de", label: "Deutsch", flag: "DE" },
  { code: "ja", label: "日本語", flag: "JP" },
];

// Gender options
type GenderOption = "male" | "neutral" | "female";
const GENDER_OPTIONS: { value: GenderOption; label: string; numericValue: number }[] = [
  { value: "male", label: "Masculino", numericValue: 20 },
  { value: "neutral", label: "Neutro", numericValue: 50 },
  { value: "female", label: "Feminino", numericValue: 80 },
];

// Voice presets library
interface VoicePreset {
  id: string;
  name: string;
  description: string;
  gender: "male" | "female";
  icon: string;
  tags: string[];
  params: VocalParams;
}

const VOICE_PRESETS: VoicePreset[] = [
  {
    id: "tenor_lirico", name: "Tenor Lírico",
    description: "Voz clara e projetada, ideal para ópera e baladas",
    gender: "male", icon: "🎭", tags: ["operatic", "classical"],
    params: { breathiness: 15, tension: 70, energy: 80, vibrato: 75, pitch_range: 85, gender: 20 },
  },
  {
    id: "baritono_pop", name: "Barítono Pop",
    description: "Voz quente e moderna, perfeita para pop e R&B",
    gender: "male", icon: "🎤", tags: ["pop", "warm"],
    params: { breathiness: 30, tension: 40, energy: 65, vibrato: 35, pitch_range: 55, gender: 25 },
  },
  {
    id: "tenor_rock", name: "Tenor Rock",
    description: "Voz potente e rasgada, para rock e alternativo",
    gender: "male", icon: "🔥", tags: ["rock", "powerful"],
    params: { breathiness: 10, tension: 85, energy: 95, vibrato: 30, pitch_range: 75, gender: 20 },
  },
  {
    id: "crooner_jazz", name: "Crooner Jazz",
    description: "Voz suave e aveludada, estilo jazz e bossa nova",
    gender: "male", icon: "🎷", tags: ["jazz", "smooth"],
    params: { breathiness: 45, tension: 25, energy: 45, vibrato: 40, pitch_range: 50, gender: 30 },
  },
  {
    id: "soprano_lirica", name: "Soprano Lírica",
    description: "Voz poderosa e cristalina, para ópera e clássico",
    gender: "female", icon: "✨", tags: ["operatic", "classical"],
    params: { breathiness: 15, tension: 65, energy: 85, vibrato: 80, pitch_range: 95, gender: 80 },
  },
  {
    id: "mezzo_pop", name: "Mezzo Pop",
    description: "Voz versátil e expressiva, ideal para pop e dance",
    gender: "female", icon: "💫", tags: ["pop", "expressive"],
    params: { breathiness: 25, tension: 45, energy: 70, vibrato: 40, pitch_range: 65, gender: 75 },
  },
  {
    id: "alto_indie", name: "Alto Indie",
    description: "Voz intimista e aérea, estilo indie e folk",
    gender: "female", icon: "🌙", tags: ["indie", "breathy"],
    params: { breathiness: 70, tension: 20, energy: 40, vibrato: 25, pitch_range: 50, gender: 65 },
  },
  {
    id: "soprano_ethereal", name: "Soprano Etérea",
    description: "Voz delicada e sonhadora, para ambient e new age",
    gender: "female", icon: "🦋", tags: ["ethereal", "ambient"],
    params: { breathiness: 60, tension: 20, energy: 35, vibrato: 55, pitch_range: 80, gender: 80 },
  },
  // --- Novas vozes masculinas ---
  {
    id: "contratenor", name: "Contratenor",
    description: "Voz aguda em falsete, registro celestial e raro",
    gender: "male", icon: "👼", tags: ["classical", "falsetto"],
    params: { breathiness: 35, tension: 50, energy: 60, vibrato: 65, pitch_range: 95, gender: 35 },
  },
  {
    id: "soul_gospel", name: "Soul Gospel",
    description: "Voz quente e emotiva, belting espiritual",
    gender: "male", icon: "🙏", tags: ["soul", "gospel"],
    params: { breathiness: 20, tension: 75, energy: 90, vibrato: 60, pitch_range: 80, gender: 25 },
  },
  {
    id: "rapper_mc", name: "Rapper/MC",
    description: "Voz rítmica e percussiva, flow e atitude",
    gender: "male", icon: "🎙️", tags: ["hip-hop", "rap"],
    params: { breathiness: 15, tension: 60, energy: 85, vibrato: 10, pitch_range: 30, gender: 15 },
  },
  {
    id: "country_masculino", name: "Country Tenor",
    description: "Voz narrativa e acolhedora, estilo Nashville",
    gender: "male", icon: "🤠", tags: ["country", "warm"],
    params: { breathiness: 35, tension: 45, energy: 60, vibrato: 45, pitch_range: 60, gender: 25 },
  },
  {
    id: "indie_soft_male", name: "Indie Sussurrado",
    description: "Voz suave e sussurrada, lo-fi e intimista",
    gender: "male", icon: "🌿", tags: ["indie", "soft"],
    params: { breathiness: 80, tension: 15, energy: 30, vibrato: 15, pitch_range: 40, gender: 30 },
  },
  {
    id: "metal_gutural", name: "Metal Gutural",
    description: "Voz agressiva e intensa, grito e peso",
    gender: "male", icon: "⚡", tags: ["metal", "aggressive"],
    params: { breathiness: 5, tension: 95, energy: 100, vibrato: 10, pitch_range: 65, gender: 15 },
  },
  // --- Novas vozes femininas ---
  {
    id: "diva_rnb", name: "Diva R&B",
    description: "Voz poderosa e melismática, runs e expressão",
    gender: "female", icon: "👑", tags: ["r&b", "soulful"],
    params: { breathiness: 20, tension: 55, energy: 80, vibrato: 65, pitch_range: 85, gender: 75 },
  },
  {
    id: "country_feminino", name: "Country Folk",
    description: "Voz calorosa e narrativa, violão e história",
    gender: "female", icon: "🌾", tags: ["country", "folk"],
    params: { breathiness: 40, tension: 35, energy: 55, vibrato: 35, pitch_range: 55, gender: 70 },
  },
  {
    id: "punk_feminino", name: "Punk Rock",
    description: "Voz crua e explosiva, atitude e energia",
    gender: "female", icon: "💥", tags: ["punk", "rock"],
    params: { breathiness: 10, tension: 80, energy: 95, vibrato: 15, pitch_range: 70, gender: 70 },
  },
  {
    id: "jazz_lounge", name: "Jazz Lounge",
    description: "Voz esfumada e sedutora, noites de jazz",
    gender: "female", icon: "🍷", tags: ["jazz", "smoky"],
    params: { breathiness: 55, tension: 30, energy: 45, vibrato: 45, pitch_range: 55, gender: 65 },
  },
  {
    id: "mpb_bossa", name: "MPB / Bossa",
    description: "Voz suave e brasileira, bossa nova e MPB",
    gender: "female", icon: "🌴", tags: ["bossa nova", "mpb"],
    params: { breathiness: 50, tension: 20, energy: 40, vibrato: 30, pitch_range: 50, gender: 70 },
  },
  {
    id: "gospel_feminino", name: "Gospel Power",
    description: "Voz explosiva e espiritual, belting e fé",
    gender: "female", icon: "🔔", tags: ["gospel", "powerful"],
    params: { breathiness: 10, tension: 70, energy: 95, vibrato: 70, pitch_range: 90, gender: 80 },
  },
];

interface VocalParams {
  breathiness: number;
  tension: number;
  energy: number;
  vibrato: number;
  pitch_range: number;
  gender: number;
}

export default function QuickStartPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Core
  const [file, setFile] = useState<File | null>(null);
  const [lyrics, setLyrics] = useState("");
  const [name, setName] = useState("");
  const [dragActive, setDragActive] = useState(false);

  // Style & params
  const [language, setLanguage] = useState("it");
  const [engine, setEngine] = useState("diffsinger");
  const [vocalStyle, setVocalStyle] = useState("pop");
  const [vocalParams, setVocalParams] = useState<VocalParams>({
    breathiness: 30, tension: 45, energy: 65, vibrato: 40, pitch_range: 60, gender: 50,
  });
  const [mixPreset, setMixPreset] = useState("balanced");
  const [selectedVoice, setSelectedVoice] = useState<string | null>(null);
  const [genderOption, setGenderOption] = useState<GenderOption>("neutral");
  const [voiceFilter, setVoiceFilter] = useState<"all" | "male" | "female">("all");

  // Mix sliders
  const [vocalGain, setVocalGain] = useState(0);
  const [instrumentalGain, setInstrumentalGain] = useState(-3);
  const [reverbAmount, setReverbAmount] = useState(25);
  const [compression, setCompression] = useState(40);

  // Tipo de áudio
  const [hasVocals, setHasVocals] = useState(false);

  // UI
  const [showAdvanced, setShowAdvanced] = useState(false);

  const applyStyle = (styleId: string) => {
    setVocalStyle(styleId);
    setSelectedVoice(null);
    const style = VOCAL_STYLES.find((s) => s.id === styleId);
    if (style) {
      setVocalParams(style.params);
      // Sync gender toggle
      const g = style.params.gender;
      setGenderOption(g <= 35 ? "male" : g >= 65 ? "female" : "neutral");
    }
  };

  const applyVoicePreset = (presetId: string) => {
    const preset = VOICE_PRESETS.find((p) => p.id === presetId);
    if (!preset) return;
    setSelectedVoice(presetId);
    setVocalParams(preset.params);
    setGenderOption(preset.gender === "male" ? "male" : "female");
    setVocalStyle("custom");
  };

  const handleGenderChange = (opt: GenderOption) => {
    setGenderOption(opt);
    const numVal = GENDER_OPTIONS.find((g) => g.value === opt)?.numericValue ?? 50;
    setVocalParams((p) => ({ ...p, gender: numVal }));
    setSelectedVoice(null);
    setVocalStyle("custom");
  };

  const quickStartMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("Selecione um arquivo de áudio");
      if (!lyrics.trim()) throw new Error("Insira a letra da música");
      return api.quickStart({
        file,
        lyrics: lyrics.trim(),
        name: name.trim() || undefined,
        language,
        synthesis_engine: engine,
        has_vocals: hasVocals,
        voice_preset: selectedVoice || undefined,
        vocal_style: vocalStyle,
        breathiness: vocalParams.breathiness,
        tension: vocalParams.tension,
        energy: vocalParams.energy,
        vibrato: vocalParams.vibrato,
        pitch_range: vocalParams.pitch_range,
        gender: vocalParams.gender,
        mix_preset: mixPreset,
        vocal_gain_db: vocalGain,
        instrumental_gain_db: instrumentalGain,
        reverb_amount: reverbAmount,
        compression_amount: compression,
      });
    },
    onSuccess: (project) => {
      showToast({
        type: "success",
        title: "Pipeline iniciado!",
        message: `Projeto "${project.name}" criado. Redirecionando...`,
      });
      router.push(`/project/${project.id}`);
    },
    onError: (err: Error) => {
      showToast({
        type: "error",
        title: "Erro no Quick Start",
        message: err.message,
        duration: 8000,
      });
    },
  });

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
      if (!name) setName(droppedFile.name.replace(/\.[^.]+$/, ""));
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      if (!name) setName(selectedFile.name.replace(/\.[^.]+$/, ""));
    }
  };

  const canSubmit = file && lyrics.trim() && !quickStartMutation.isPending;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {/* Header */}
      <div className="mb-10 text-center animate-slide-down">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo.svg" alt="ClovisAI" className="mx-auto mb-4 h-16 w-16 rounded-2xl shadow-lg shadow-brand-500/20 animate-float" />
        <h1 className="text-3xl font-bold tracking-tight text-white">
          Clovis<span className="bg-gradient-to-r from-brand-400 to-purple-400 bg-clip-text text-transparent">AI</span>
        </h1>
        <p className="mt-2 text-sm text-gray-500">
          Configure o vocal dos seus sonhos em poucos cliques
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-5">
        {/* Left column: Upload + Lyrics */}
        <div className="lg:col-span-2 space-y-6 animate-slide-up stagger-1">
          {/* Upload */}
          <div className="card">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-gray-500">
              <FileAudio className="h-4 w-4" />
              Instrumental
            </h2>
            {file ? (
              <div className="flex items-center justify-between rounded-lg border border-gray-700 bg-gray-800/50 p-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-brand-600/20">
                    <FileAudio className="h-5 w-5 text-brand-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-white">{file.name}</p>
                    <p className="text-xs text-gray-500">
                      {(file.size / (1024 * 1024)).toFixed(1)} MB
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => { setFile(null); if (fileInputRef.current) fileInputRef.current.value = ""; }}
                  className="ml-2 flex-shrink-0 text-gray-500 hover:text-red-400"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <div
                onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                onDragLeave={() => setDragActive(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-all ${
                  dragActive
                    ? "border-brand-500 bg-brand-500/5 scale-[1.02]"
                    : "border-gray-700 hover:border-gray-500"
                }`}
              >
                <Upload className="mb-2 h-8 w-8 text-gray-600" />
                <p className="text-xs text-gray-400">Arraste ou clique</p>
                <p className="mt-0.5 text-xs text-gray-600">WAV, MP3, FLAC, OGG</p>
              </div>
            )}
            <input ref={fileInputRef} type="file" accept=".wav,.mp3,.flac,.ogg,.m4a" className="hidden" onChange={handleFileSelect} />

            {/* Toggle: música com vocal */}
            <div className="mt-3 flex items-center justify-between rounded-lg border border-gray-800 bg-gray-900/50 p-3">
              <div>
                <p className="text-sm text-gray-300">Contém vocal?</p>
                <p className="text-xs text-gray-600">
                  {hasVocals
                    ? "Demucs separa vocal + instrumental"
                    : "Apenas instrumental (sem vocal)"}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setHasVocals(!hasVocals)}
                className={`relative h-6 w-11 rounded-full transition-colors ${
                  hasVocals ? "bg-brand-600" : "bg-gray-700"
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
                    hasVocals ? "translate-x-5" : "translate-x-0"
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Lyrics */}
          <div className="card">
            <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-gray-500">
              <Music className="h-4 w-4" />
              Letra
            </h2>
            <textarea
              className="input min-h-[200px] resize-y font-mono text-sm leading-relaxed"
              placeholder={"Nel blu dipinto di blu\nFelice di stare lassù\nE volavo, volavo\nFelice più in alto del sole..."}
              value={lyrics}
              onChange={(e) => setLyrics(e.target.value)}
            />
            <div className="mt-2 flex items-center justify-between">
              <p className="text-xs text-gray-600">
                {lyrics.trim()
                  ? `${lyrics.trim().split("\n").length} linhas`
                  : "Cole a letra da música"}
              </p>
              {/* Language pills */}
              <div className="flex gap-1">
                {LANGUAGES.map((lang) => (
                  <button
                    key={lang.code}
                    type="button"
                    onClick={() => setLanguage(lang.code)}
                    className={`rounded px-1.5 py-0.5 text-xs font-medium transition-colors ${
                      language === lang.code
                        ? "bg-brand-600 text-white"
                        : "bg-gray-800 text-gray-500 hover:text-gray-300"
                    }`}
                    title={lang.label}
                  >
                    {lang.flag}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Project name */}
          <div className="card">
            <label className="mb-2 block text-sm font-semibold uppercase tracking-wider text-gray-500">
              Nome do Projeto
            </label>
            <input
              type="text"
              className="input"
              placeholder="Automático a partir do arquivo"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
        </div>

        {/* Right column: Style & Controls */}
        <div className="lg:col-span-3 space-y-6 animate-slide-up stagger-2">
          {/* Voice Library */}
          <div className="card">
            <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-gray-500">
              <Users className="h-4 w-4" />
              Biblioteca de Vozes
            </h2>

            {/* Gender filter tabs */}
            <div className="mb-4 flex gap-2">
              {(["all", "male", "female"] as const).map((filter) => {
                const filterLabels = { all: "Todas", male: "Masculinas", female: "Femininas" };
                const filteredCount = filter === "all"
                  ? VOICE_PRESETS.length
                  : VOICE_PRESETS.filter((p) => p.gender === filter).length;
                return (
                  <button
                    key={filter}
                    type="button"
                    onClick={() => setVoiceFilter(filter)}
                    className={`rounded-lg border px-3 py-1.5 text-xs transition-colors ${
                      voiceFilter === filter
                        ? "border-brand-500 bg-brand-500/10 text-brand-400"
                        : "border-gray-800 text-gray-400 hover:border-gray-700 hover:text-gray-300"
                    }`}
                  >
                    {filterLabels[filter]} ({filteredCount})
                  </button>
                );
              })}
            </div>

            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5">
              {VOICE_PRESETS.filter((p) => voiceFilter === "all" || p.gender === voiceFilter).map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => applyVoicePreset(preset.id)}
                  className={`group relative overflow-hidden rounded-xl border p-3 text-left transition-all duration-200 ${
                    selectedVoice === preset.id
                      ? "border-brand-500 bg-brand-500/10 shadow-lg shadow-brand-500/20"
                      : "border-gray-800 bg-gray-900/50 hover:border-gray-700 hover:bg-gray-900"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-lg">{preset.icon}</span>
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                      preset.gender === "male"
                        ? "bg-blue-500/15 text-blue-400"
                        : "bg-pink-500/15 text-pink-400"
                    }`}>
                      {preset.gender === "male" ? "M" : "F"}
                    </span>
                    <div className="ml-auto">
                      <VoicePreviewButton presetId={preset.id} size="sm" />
                    </div>
                  </div>
                  <h4 className={`text-xs font-semibold ${
                    selectedVoice === preset.id ? "text-white" : "text-gray-300"
                  }`}>
                    {preset.name}
                  </h4>
                  <p className="mt-0.5 text-[10px] text-gray-500 line-clamp-2">
                    {preset.description}
                  </p>
                  {selectedVoice === preset.id && (
                    <div className="absolute right-2 top-2 h-2 w-2 rounded-full bg-brand-500 animate-pulse" />
                  )}
                </button>
              ))}
            </div>

            {selectedVoice && (
              <button
                type="button"
                onClick={() => { setSelectedVoice(null); }}
                className="mt-3 text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                Limpar seleção (usar configuração manual)
              </button>
            )}
          </div>

          {/* Vocal Style */}
          <div className="card">
            <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-gray-500">
              <Mic className="h-4 w-4" />
              Estilo Vocal
            </h2>
            <div className="grid grid-cols-3 gap-3">
              {VOCAL_STYLES.map((style) => (
                <StyleCard
                  key={style.id}
                  id={style.id}
                  label={style.label}
                  description={style.description}
                  icon={style.icon}
                  color={style.color}
                  selected={vocalStyle === style.id}
                  onClick={() => applyStyle(style.id)}
                />
              ))}
            </div>
          </div>

          {/* Vocal Parameters */}
          <div className="card">
            <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-gray-500">
              <Waves className="h-4 w-4" />
              Parâmetros Vocais
            </h2>
            <div className="grid gap-5 sm:grid-cols-2">
              <StudioSlider
                label="Respiração"
                value={vocalParams.breathiness}
                min={0} max={100}
                unit="%"
                color="cyan"
                onChange={(v) => { setVocalParams((p) => ({ ...p, breathiness: v })); setVocalStyle("custom"); }}
              />
              <StudioSlider
                label="Tensão"
                value={vocalParams.tension}
                min={0} max={100}
                unit="%"
                color="rose"
                onChange={(v) => { setVocalParams((p) => ({ ...p, tension: v })); setVocalStyle("custom"); }}
              />
              <StudioSlider
                label="Energia"
                value={vocalParams.energy}
                min={0} max={100}
                unit="%"
                color="amber"
                onChange={(v) => { setVocalParams((p) => ({ ...p, energy: v })); setVocalStyle("custom"); }}
              />
              <StudioSlider
                label="Vibrato"
                value={vocalParams.vibrato}
                min={0} max={100}
                unit="%"
                color="purple"
                onChange={(v) => { setVocalParams((p) => ({ ...p, vibrato: v })); setVocalStyle("custom"); }}
              />
              <StudioSlider
                label="Extensão Vocal"
                value={vocalParams.pitch_range}
                min={0} max={100}
                unit="%"
                color="emerald"
                onChange={(v) => { setVocalParams((p) => ({ ...p, pitch_range: v })); setVocalStyle("custom"); }}
              />
              <div>
                <label className="mb-2 block text-xs font-medium text-gray-400">
                  Gênero Vocal
                </label>
                <div className="grid grid-cols-3 gap-1.5 rounded-lg border border-gray-800 bg-gray-900/50 p-1.5">
                  {GENDER_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => handleGenderChange(opt.value)}
                      className={`rounded-md px-3 py-2 text-xs font-medium transition-all ${
                        genderOption === opt.value
                          ? "bg-brand-600 text-white shadow-sm"
                          : "text-gray-500 hover:text-gray-300 hover:bg-gray-800"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Engine selector */}
          <div className="card">
            <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-gray-500">
              <Gauge className="h-4 w-4" />
              Engine de Síntese
            </h2>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setEngine("diffsinger")}
                className={`rounded-xl border p-4 text-left transition-all ${
                  engine === "diffsinger"
                    ? "border-brand-500 bg-brand-500/10 shadow-lg shadow-brand-500/10"
                    : "border-gray-800 hover:border-gray-700"
                }`}
              >
                <div className="text-lg font-bold text-white">DiffSinger</div>
                <p className="mt-1 text-xs text-gray-500">Alta qualidade, mais lento</p>
                <div className="mt-2 flex gap-1">
                  {[1,2,3,4,5].map((i) => (
                    <div key={i} className={`h-1 flex-1 rounded-full ${i <= 5 ? "bg-brand-500" : "bg-gray-800"}`} />
                  ))}
                </div>
                <p className="mt-1 text-xs text-gray-600">Qualidade</p>
              </button>
              <button
                type="button"
                onClick={() => setEngine("acestep")}
                className={`rounded-xl border p-4 text-left transition-all ${
                  engine === "acestep"
                    ? "border-emerald-500 bg-emerald-500/10 shadow-lg shadow-emerald-500/10"
                    : "border-gray-800 hover:border-gray-700"
                }`}
              >
                <div className="text-lg font-bold text-white">ACE-Step</div>
                <p className="mt-1 text-xs text-gray-500">Rápido, boa qualidade</p>
                <div className="mt-2 flex gap-1">
                  {[1,2,3,4,5].map((i) => (
                    <div key={i} className={`h-1 flex-1 rounded-full ${i <= 5 ? "bg-emerald-500" : "bg-gray-800"}`} />
                  ))}
                </div>
                <p className="mt-1 text-xs text-gray-600">Velocidade</p>
              </button>
            </div>
          </div>

          {/* Mix Style */}
          <div className="card">
            <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-gray-500">
              <Volume2 className="h-4 w-4" />
              Estilo de Mixagem
            </h2>
            <div className="flex flex-wrap gap-2 mb-5">
              {MIX_STYLES.map((ms) => (
                <button
                  key={ms.id}
                  type="button"
                  onClick={() => setMixPreset(ms.id)}
                  className={`rounded-lg border px-3 py-2 text-xs transition-all ${
                    mixPreset === ms.id
                      ? "border-brand-500 bg-brand-500/10 text-brand-400"
                      : "border-gray-800 text-gray-500 hover:border-gray-700 hover:text-gray-300"
                  }`}
                  title={ms.description}
                >
                  {ms.label}
                </button>
              ))}
            </div>

            {/* Advanced toggle */}
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex w-full items-center justify-between rounded-lg border border-gray-800 p-3 text-xs text-gray-500 hover:border-gray-700 hover:text-gray-400 transition-colors"
            >
              <span>Controles avançados de mixagem</span>
              {showAdvanced ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>

            {showAdvanced && (
              <div className="mt-4 grid gap-5 sm:grid-cols-2">
                <StudioSlider
                  label="Volume Vocal"
                  value={vocalGain}
                  min={-12} max={6} step={0.5}
                  unit=" dB"
                  color="brand"
                  onChange={setVocalGain}
                />
                <StudioSlider
                  label="Volume Instrumental"
                  value={instrumentalGain}
                  min={-12} max={6} step={0.5}
                  unit=" dB"
                  color="purple"
                  onChange={setInstrumentalGain}
                />
                <StudioSlider
                  label="Reverb"
                  value={reverbAmount}
                  min={0} max={100}
                  unit="%"
                  color="cyan"
                  onChange={setReverbAmount}
                />
                <StudioSlider
                  label="Compressão"
                  value={compression}
                  min={0} max={100}
                  unit="%"
                  color="amber"
                  onChange={setCompression}
                />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Sticky bottom bar */}
      <div className="sticky bottom-0 z-40 -mx-4 mt-8 border-t border-white/[0.06] bg-gray-950/80 px-4 py-4 backdrop-blur-xl">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          {/* Summary pills */}
          <div className="hidden sm:flex items-center gap-2 text-xs">
            <span className={`rounded-md px-2 py-1 ${file ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-gray-800/50 text-gray-600"}`}>
              {file ? file.name.substring(0, 20) : "Sem áudio"}
            </span>
            <span className={`rounded-md px-2 py-1 ${lyrics.trim() ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-gray-800/50 text-gray-600"}`}>
              {lyrics.trim() ? `${lyrics.trim().split("\n").length} linhas` : "Sem letra"}
            </span>
            <span className="rounded-md border border-gray-700/50 bg-gray-800/30 px-2 py-1 text-gray-400">
              {selectedVoice
                ? VOICE_PRESETS.find((p) => p.id === selectedVoice)?.name
                : VOCAL_STYLES.find((s) => s.id === vocalStyle)?.label}
            </span>
            <span className={`rounded-md border px-2 py-1 text-gray-400 ${
              genderOption === "male" ? "border-blue-500/30 bg-blue-500/10 text-blue-400" :
              genderOption === "female" ? "border-pink-500/30 bg-pink-500/10 text-pink-400" :
              "border-gray-700/50 bg-gray-800/30"
            }`}>
              {genderOption === "male" ? "M" : genderOption === "female" ? "F" : "N"}
            </span>
            <span className="rounded-md border border-gray-700/50 bg-gray-800/30 px-2 py-1 font-medium uppercase text-gray-400">
              {language}
            </span>
            <span className="rounded-md border border-gray-700/50 bg-gray-800/30 px-2 py-1 text-gray-400">
              {engine === "diffsinger" ? "DiffSinger" : "ACE-Step"}
            </span>
          </div>

          {/* Action */}
          <button
            onClick={() => quickStartMutation.mutate()}
            disabled={!canSubmit}
            className="btn-primary flex items-center gap-2 px-8 py-3 text-base shadow-xl shadow-brand-600/30 disabled:shadow-none"
          >
            {quickStartMutation.isPending ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Gerando...
              </>
            ) : (
              <>
                <Zap className="h-5 w-5" />
                Gerar Vocal
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
