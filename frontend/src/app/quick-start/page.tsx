"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, useRef } from "react";
import { api } from "@/lib/api";
import { showToast } from "@/components/Toast";
import {
  Upload,
  Zap,
  FileAudio,
  Loader2,
  X,
  Music,
  Mic,
} from "lucide-react";

export default function QuickStartPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [lyrics, setLyrics] = useState("");
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("it");
  const [engine, setEngine] = useState("diffsinger");
  const [dragActive, setDragActive] = useState(false);

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
      if (!name) {
        setName(droppedFile.name.replace(/\.[^.]+$/, ""));
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      if (!name) {
        setName(selectedFile.name.replace(/\.[^.]+$/, ""));
      }
    }
  };

  const canSubmit = file && lyrics.trim() && !quickStartMutation.isPending;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-brand-600/20">
          <Zap className="h-8 w-8 text-brand-400" />
        </div>
        <h1 className="text-3xl font-bold text-white">Quick Start</h1>
        <p className="mt-2 text-gray-400">
          Envie o instrumental e a letra — o pipeline roda automaticamente
        </p>
      </div>

      <div className="space-y-6">
        {/* Step 1: Audio Upload */}
        <div className="card">
          <div className="mb-4 flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">
              1
            </span>
            <h2 className="text-lg font-semibold text-white">Instrumental</h2>
          </div>

          {file ? (
            <div className="flex items-center justify-between rounded-lg border border-gray-700 bg-gray-800/50 p-4">
              <div className="flex items-center gap-3">
                <FileAudio className="h-8 w-8 text-brand-400" />
                <div>
                  <p className="text-sm font-medium text-white">{file.name}</p>
                  <p className="text-xs text-gray-500">
                    {(file.size / (1024 * 1024)).toFixed(1)} MB
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = "";
                }}
                className="text-gray-500 hover:text-red-400"
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
              className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
                dragActive
                  ? "border-brand-500 bg-brand-500/5"
                  : "border-gray-700 hover:border-gray-600"
              }`}
            >
              <Upload className="mb-3 h-10 w-10 text-gray-500" />
              <p className="text-sm text-gray-400">
                Arraste o arquivo de áudio ou clique para selecionar
              </p>
              <p className="mt-1 text-xs text-gray-600">
                WAV, MP3, FLAC, OGG, M4A (até 500MB)
              </p>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".wav,.mp3,.flac,.ogg,.m4a"
            className="hidden"
            onChange={handleFileSelect}
          />
        </div>

        {/* Step 2: Lyrics */}
        <div className="card">
          <div className="mb-4 flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">
              2
            </span>
            <h2 className="text-lg font-semibold text-white">Letra</h2>
          </div>
          <textarea
            className="input min-h-[160px] resize-y font-mono text-sm"
            placeholder={"Nel blu dipinto di blu\nFelice di stare lassù\nE volavo, volavo\nFelice più in alto del sole..."}
            value={lyrics}
            onChange={(e) => setLyrics(e.target.value)}
          />
          <p className="mt-2 text-xs text-gray-600">
            {lyrics.trim()
              ? `${lyrics.trim().split("\n").length} linhas, ${lyrics.trim().length} caracteres`
              : "Cole ou digite a letra da música"}
          </p>
        </div>

        {/* Step 3: Settings */}
        <div className="card">
          <div className="mb-4 flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">
              3
            </span>
            <h2 className="text-lg font-semibold text-white">Configurações</h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs text-gray-400">
                Nome do projeto (opcional)
              </label>
              <input
                type="text"
                className="input"
                placeholder="Nome automático do arquivo"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">
                Idioma da letra
              </label>
              <select
                className="input"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              >
                <option value="it">Italiano</option>
                <option value="pt">Português</option>
                <option value="en">English</option>
                <option value="es">Español</option>
                <option value="fr">Français</option>
                <option value="de">Deutsch</option>
                <option value="ja">日本語</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">
                Engine de síntese
              </label>
              <select
                className="input"
                value={engine}
                onChange={(e) => setEngine(e.target.value)}
              >
                <option value="diffsinger">DiffSinger (qualidade)</option>
                <option value="acestep">ACE-Step (rápido)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Pipeline summary */}
        <div className="rounded-lg border border-gray-800 bg-gray-900/30 p-4">
          <h3 className="mb-3 text-sm font-medium text-gray-400">
            O que vai acontecer:
          </h3>
          <div className="flex flex-wrap gap-2">
            {[
              { icon: <FileAudio className="h-3 w-3" />, label: "Upload + Análise" },
              { icon: <Music className="h-3 w-3" />, label: "Extração de Melodia" },
              { icon: <Mic className="h-3 w-3" />, label: "Síntese Vocal" },
              { icon: <Mic className="h-3 w-3" />, label: "Refinamento" },
              { icon: <Music className="h-3 w-3" />, label: "Mixagem Final" },
            ].map((step, i) => (
              <div
                key={i}
                className="flex items-center gap-1.5 rounded-full border border-gray-700 px-3 py-1 text-xs text-gray-400"
              >
                {step.icon}
                {step.label}
                {i < 4 && <span className="ml-1 text-gray-600">→</span>}
              </div>
            ))}
          </div>
        </div>

        {/* Submit */}
        <button
          onClick={() => quickStartMutation.mutate()}
          disabled={!canSubmit}
          className="btn-primary flex w-full items-center justify-center gap-2 py-3 text-lg"
        >
          {quickStartMutation.isPending ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Criando projeto e iniciando pipeline...
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
  );
}
