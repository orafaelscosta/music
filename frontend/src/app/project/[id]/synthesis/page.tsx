"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, SynthesisParams } from "@/lib/api";
import AudioPlayer from "@/components/AudioPlayer";
import VoiceSelector from "@/components/VoiceSelector";
import {
  ArrowLeft,
  ArrowRight,
  Eye,
  Loader2,
  Mic,
  Play,
  Sparkles,
  Volume2,
} from "lucide-react";

const DEFAULT_PARAMS: SynthesisParams = {
  engine: "diffsinger",
  voicebank: "leif",
  breathiness: 0,
  tension: 0,
  energy: 1.0,
  voicing: 1.0,
  pitch_deviation: 0,
  gender: 0,
  guidance_scale: 3.5,
  num_inference_steps: 50,
  seed: -1,
};

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}

function ParamSlider({ label, value, min, max, step, onChange }: SliderProps) {
  return (
    <div className="flex items-center gap-3">
      <label className="w-28 text-xs text-gray-400">{label}</label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="h-1 flex-1 cursor-pointer accent-brand-500"
      />
      <span className="w-10 text-right text-xs text-gray-500">
        {value.toFixed(2)}
      </span>
    </div>
  );
}

export default function SynthesisPage() {
  const params = useParams();
  const queryClient = useQueryClient();
  const projectId = params.id as string;
  const [synthParams, setSynthParams] = useState<SynthesisParams>(DEFAULT_PARAMS);

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
  });

  const { data: synthStatus, refetch: refetchStatus } = useQuery({
    queryKey: ["synthesis-status", projectId],
    queryFn: () => api.getSynthesisStatus(projectId),
    refetchInterval: 3000,
  });

  const renderMutation = useMutation({
    mutationFn: () => api.renderVocal(projectId, synthParams),
    onSuccess: () => {
      refetchStatus();
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });

  const previewMutation = useMutation({
    mutationFn: () =>
      api.previewVocal(projectId, { ...synthParams, preview_seconds: 15 }),
    onSuccess: () => refetchStatus(),
  });

  const variationsMutation = useMutation({
    mutationFn: () => api.generateVariations(projectId, synthParams, 3),
    onSuccess: () => refetchStatus(),
  });

  const updateParam = (key: keyof SynthesisParams, value: number | string) => {
    setSynthParams((prev) => ({ ...prev, [key]: value }));
  };

  const files = (synthStatus as Record<string, Record<string, unknown>>)?.files || {};
  const rawVocal = files["vocals_raw.wav"] as
    | { exists: boolean; download_url: string }
    | undefined;
  const previewVocal = files["vocals_preview.wav"] as
    | { exists: boolean; download_url: string }
    | undefined;
  const variations = (files["variations"] || []) as {
    file: string;
    download_url: string;
  }[];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-brand-500" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <h2 className="text-xl font-semibold text-gray-400">
          Projeto não encontrado
        </h2>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 text-sm">
          <a
            href={`/project/${projectId}`}
            className="text-gray-500 hover:text-gray-300"
          >
            <ArrowLeft className="inline h-4 w-4 mr-1" />
            {project.name}
          </a>
          <span className="text-gray-600">/</span>
          <span className="text-gray-300">Síntese Vocal</span>
        </div>
        <h1 className="mt-4 text-2xl font-bold text-white flex items-center gap-2">
          <Mic className="h-6 w-6 text-brand-400" />
          Síntese Vocal
        </h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main area */}
        <div className="lg:col-span-2 space-y-6">
          {/* Engine Selector */}
          <div className="card">
            <h2 className="mb-4 text-lg font-semibold text-white">
              Engine de Síntese
            </h2>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => updateParam("engine", "diffsinger")}
                className={`rounded-lg border p-4 text-left transition-colors ${
                  synthParams.engine === "diffsinger"
                    ? "border-brand-500 bg-brand-500/10"
                    : "border-gray-700 hover:border-gray-600"
                }`}
              >
                <p className="font-medium text-white">DiffSinger</p>
                <p className="text-xs text-gray-400 mt-1">
                  Alta qualidade, MIDI + letra, controles de expressão
                </p>
              </button>
              <button
                onClick={() => updateParam("engine", "acestep")}
                className={`rounded-lg border p-4 text-left transition-colors ${
                  synthParams.engine === "acestep"
                    ? "border-brand-500 bg-brand-500/10"
                    : "border-gray-700 hover:border-gray-600"
                }`}
              >
                <p className="font-medium text-white">ACE-Step</p>
                <p className="text-xs text-gray-400 mt-1">
                  Rápido, Lyric2Vocal, bom para previews
                </p>
              </button>
            </div>
          </div>

          {/* Expression Controls (DiffSinger) */}
          {synthParams.engine === "diffsinger" && (
            <div className="card">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                <Volume2 className="h-5 w-5 text-brand-400" />
                Controles de Expressão
              </h2>
              <div className="space-y-3">
                <ParamSlider
                  label="Breathiness"
                  value={synthParams.breathiness ?? 0}
                  min={-1}
                  max={1}
                  step={0.05}
                  onChange={(v) => updateParam("breathiness", v)}
                />
                <ParamSlider
                  label="Tension"
                  value={synthParams.tension ?? 0}
                  min={-1}
                  max={1}
                  step={0.05}
                  onChange={(v) => updateParam("tension", v)}
                />
                <ParamSlider
                  label="Energy"
                  value={synthParams.energy ?? 1}
                  min={0}
                  max={2}
                  step={0.05}
                  onChange={(v) => updateParam("energy", v)}
                />
                <ParamSlider
                  label="Voicing"
                  value={synthParams.voicing ?? 1}
                  min={0}
                  max={2}
                  step={0.05}
                  onChange={(v) => updateParam("voicing", v)}
                />
                <ParamSlider
                  label="Pitch Dev."
                  value={synthParams.pitch_deviation ?? 0}
                  min={-1}
                  max={1}
                  step={0.05}
                  onChange={(v) => updateParam("pitch_deviation", v)}
                />
                <ParamSlider
                  label="Gender"
                  value={synthParams.gender ?? 0}
                  min={-1}
                  max={1}
                  step={0.05}
                  onChange={(v) => updateParam("gender", v)}
                />
              </div>
            </div>
          )}

          {/* ACE-Step Controls */}
          {synthParams.engine === "acestep" && (
            <div className="card">
              <h2 className="mb-4 text-lg font-semibold text-white">
                Parâmetros ACE-Step
              </h2>
              <div className="space-y-3">
                <ParamSlider
                  label="Guidance"
                  value={synthParams.guidance_scale ?? 3.5}
                  min={1}
                  max={10}
                  step={0.5}
                  onChange={(v) => updateParam("guidance_scale", v)}
                />
                <ParamSlider
                  label="Steps"
                  value={synthParams.num_inference_steps ?? 50}
                  min={10}
                  max={200}
                  step={10}
                  onChange={(v) => updateParam("num_inference_steps", v)}
                />
                <div className="flex items-center gap-3">
                  <label className="w-28 text-xs text-gray-400">Seed</label>
                  <input
                    type="number"
                    className="input w-24"
                    value={synthParams.seed ?? -1}
                    onChange={(e) => updateParam("seed", parseInt(e.target.value) || -1)}
                  />
                  <span className="text-xs text-gray-600">-1 = aleatório</span>
                </div>
              </div>
            </div>
          )}

          {/* Results */}
          {previewVocal?.exists && (
            <div className="card">
              <h2 className="mb-4 text-lg font-semibold text-white">
                Preview Vocal
              </h2>
              <AudioPlayer
                projectId={projectId}
                filename="vocals_preview.wav"
              />
            </div>
          )}

          {rawVocal?.exists && (
            <div className="card">
              <h2 className="mb-4 text-lg font-semibold text-white">
                Vocal Completo
              </h2>
              <AudioPlayer
                projectId={projectId}
                filename="vocals_raw.wav"
              />
            </div>
          )}

          {/* Variations */}
          {variations.length > 0 && (
            <div className="card">
              <h2 className="mb-4 text-lg font-semibold text-white">
                Variações
              </h2>
              <div className="space-y-4">
                {variations.map((v, i) => (
                  <div key={v.file}>
                    <p className="mb-2 text-sm text-gray-400">
                      Variação {i + 1}
                    </p>
                    <AudioPlayer projectId={projectId} filename={v.file} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Voice Selector */}
          <div className="card">
            <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">
              Voz
            </h3>
            <VoiceSelector
              engine={synthParams.engine}
              selectedVoice={synthParams.voicebank}
              onSelect={(v) => updateParam("voicebank", v)}
            />
          </div>

          {/* Actions */}
          <div className="card space-y-3">
            <h3 className="mb-1 text-sm font-semibold uppercase text-gray-500">
              Ações
            </h3>
            <button
              onClick={() => previewMutation.mutate()}
              disabled={previewMutation.isPending}
              className="btn-secondary w-full flex items-center justify-center gap-2"
            >
              {previewMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
              Preview (15s)
            </button>

            <button
              onClick={() => renderMutation.mutate()}
              disabled={renderMutation.isPending}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {renderMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              Renderizar Completo
            </button>

            <button
              onClick={() => variationsMutation.mutate()}
              disabled={variationsMutation.isPending}
              className="btn-secondary w-full flex items-center justify-center gap-2"
            >
              {variationsMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              3 Variações
            </button>
          </div>

          {/* Errors */}
          {renderMutation.isError && (
            <div className="rounded-lg border border-red-800 bg-red-900/20 p-3 text-sm text-red-400">
              {renderMutation.error.message}
            </div>
          )}
          {previewMutation.isError && (
            <div className="rounded-lg border border-red-800 bg-red-900/20 p-3 text-sm text-red-400">
              {previewMutation.error.message}
            </div>
          )}

          {/* Navigation */}
          <div className="card flex gap-2">
            <a
              href={`/project/${projectId}/melody`}
              className="btn-secondary flex-1 flex items-center justify-center gap-1"
            >
              <ArrowLeft className="h-4 w-4" />
              Melodia
            </a>
            <a
              href={`/project/${projectId}/refinement`}
              className="btn-primary flex-1 flex items-center justify-center gap-1"
            >
              Refinar
              <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
