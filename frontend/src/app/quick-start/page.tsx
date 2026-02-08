"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, useRef } from "react";
import { api } from "@/lib/api";
import { showToast } from "@/components/Toast";
import StudioSlider from "@/components/StudioSlider";
import StyleCard from "@/components/StyleCard";
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

  // Mix sliders
  const [vocalGain, setVocalGain] = useState(0);
  const [instrumentalGain, setInstrumentalGain] = useState(-3);
  const [reverbAmount, setReverbAmount] = useState(25);
  const [compression, setCompression] = useState(40);

  // UI
  const [showAdvanced, setShowAdvanced] = useState(false);

  const applyStyle = (styleId: string) => {
    setVocalStyle(styleId);
    const style = VOCAL_STYLES.find((s) => s.id === styleId);
    if (style) {
      setVocalParams(style.params);
    }
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
      <div className="mb-10 text-center">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo.svg" alt="ClovisAI" className="mx-auto mb-4 h-16 w-16 rounded-2xl shadow-lg shadow-brand-500/20" />
        <h1 className="text-3xl font-bold text-white">ClovisAI</h1>
        <p className="mt-2 text-gray-400">
          Configure o vocal dos seus sonhos em poucos cliques
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-5">
        {/* Left column: Upload + Lyrics */}
        <div className="lg:col-span-2 space-y-6">
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
        <div className="lg:col-span-3 space-y-6">
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
              <StudioSlider
                label="Gênero (grave ↔ agudo)"
                value={vocalParams.gender}
                min={0} max={100}
                unit="%"
                color="brand"
                onChange={(v) => { setVocalParams((p) => ({ ...p, gender: v })); setVocalStyle("custom"); }}
              />
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
      <div className="sticky bottom-0 z-40 -mx-4 mt-8 border-t border-gray-800 bg-gray-950/90 px-4 py-4 backdrop-blur-lg">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          {/* Summary */}
          <div className="hidden sm:flex items-center gap-4 text-xs text-gray-500">
            <span className={file ? "text-green-400" : "text-gray-600"}>
              {file ? file.name.substring(0, 20) : "Sem áudio"}
            </span>
            <span className="text-gray-700">|</span>
            <span className={lyrics.trim() ? "text-green-400" : "text-gray-600"}>
              {lyrics.trim() ? `${lyrics.trim().split("\n").length} linhas` : "Sem letra"}
            </span>
            <span className="text-gray-700">|</span>
            <span className="text-gray-400">
              {VOCAL_STYLES.find((s) => s.id === vocalStyle)?.label}
            </span>
            <span className="text-gray-700">|</span>
            <span className="text-gray-400 uppercase">{language}</span>
            <span className="text-gray-700">|</span>
            <span className="text-gray-400">{engine === "diffsinger" ? "DiffSinger" : "ACE-Step"}</span>
          </div>

          {/* Action */}
          <button
            onClick={() => quickStartMutation.mutate()}
            disabled={!canSubmit}
            className="btn-primary flex items-center gap-2 px-8 py-3 text-base shadow-lg shadow-brand-600/20 disabled:shadow-none"
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
