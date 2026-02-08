"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import AudioPlayer from "@/components/AudioPlayer";
import {
  ArrowLeft,
  Download,
  Loader2,
  Music2,
  Play,
  Settings2,
  Sparkles,
} from "lucide-react";

interface MixParams {
  vocal_gain_db: number;
  instrumental_gain_db: number;
  eq_low_gain_db: number;
  eq_mid_gain_db: number;
  eq_high_gain_db: number;
  compressor_threshold_db: number;
  compressor_ratio: number;
  reverb_room_size: number;
  reverb_wet_level: number;
  limiter_threshold_db: number;
  preset: string | null;
}

const DEFAULT_PARAMS: MixParams = {
  vocal_gain_db: 0,
  instrumental_gain_db: -3,
  eq_low_gain_db: 0,
  eq_mid_gain_db: 2,
  eq_high_gain_db: 1,
  compressor_threshold_db: -18,
  compressor_ratio: 3,
  reverb_room_size: 0.3,
  reverb_wet_level: 0.15,
  limiter_threshold_db: -1,
  preset: null,
};

export default function MixPage() {
  const params = useParams();
  const queryClient = useQueryClient();
  const projectId = params.id as string;

  const [mixParams, setMixParams] = useState<MixParams>({ ...DEFAULT_PARAMS });
  const [exportFormat, setExportFormat] = useState("wav");

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
  });

  const { data: mixStatus, refetch: refetchStatus } = useQuery({
    queryKey: ["mix-status", projectId],
    queryFn: () => api.getMixStatus(projectId),
  });

  const { data: presets } = useQuery({
    queryKey: ["mix-presets", projectId],
    queryFn: () => api.getMixPresets(projectId),
  });

  const renderMutation = useMutation({
    mutationFn: () => api.renderMix(projectId, mixParams),
    onSuccess: () => {
      refetchStatus();
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });

  const exportMutation = useMutation({
    mutationFn: () => api.exportMix(projectId, exportFormat),
    onSuccess: () => {
      refetchStatus();
    },
  });

  const applyPreset = (presetName: string) => {
    const preset = presets?.presets?.find(
      (p: { name: string; params: Record<string, number> }) =>
        p.name === presetName
    );
    if (preset) {
      setMixParams((prev) => ({
        ...prev,
        ...preset.params,
        preset: presetName,
      }));
    }
  };

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
          <span className="text-gray-300">Mixagem & Export</span>
        </div>
        <h1 className="mt-4 text-2xl font-bold text-white flex items-center gap-2">
          <Music2 className="h-6 w-6 text-brand-400" />
          Mixagem Final
        </h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main */}
        <div className="lg:col-span-2 space-y-6">
          {/* Preview */}
          <div className="card">
            <h2 className="mb-4 text-lg font-semibold text-white">
              Preview da Mixagem
            </h2>
            {mixStatus?.has_mix ? (
              <AudioPlayer projectId={projectId} filename="mix_final.wav" />
            ) : (
              <div className="rounded-lg border border-gray-700 p-8 text-center text-sm text-gray-600">
                Renderize a mixagem para ouvir o preview
              </div>
            )}
          </div>

          {/* Mixer Controls */}
          <div className="card">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Settings2 className="h-5 w-5 text-brand-400" />
                Controles de Mixagem
              </h2>
              {/* Preset selector */}
              <select
                className="input w-48"
                value={mixParams.preset || ""}
                onChange={(e) => {
                  if (e.target.value) {
                    applyPreset(e.target.value);
                  }
                }}
              >
                <option value="">Preset customizado</option>
                {presets?.presets?.map(
                  (p: { name: string; params: Record<string, number> }) => (
                    <option key={p.name} value={p.name}>
                      {p.name.charAt(0).toUpperCase() + p.name.slice(1)}
                    </option>
                  )
                )}
              </select>
            </div>

            <div className="space-y-5">
              {/* Volume Section */}
              <div>
                <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">
                  Volume
                </h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-1 flex items-center justify-between text-sm text-gray-400">
                      <span>Vocal</span>
                      <span className="text-gray-600">
                        {mixParams.vocal_gain_db.toFixed(1)} dB
                      </span>
                    </label>
                    <input
                      type="range"
                      min={-24}
                      max={12}
                      step={0.5}
                      value={mixParams.vocal_gain_db}
                      onChange={(e) =>
                        setMixParams((p) => ({
                          ...p,
                          vocal_gain_db: parseFloat(e.target.value),
                          preset: null,
                        }))
                      }
                      className="h-1 w-full cursor-pointer accent-brand-500"
                    />
                  </div>
                  <div>
                    <label className="mb-1 flex items-center justify-between text-sm text-gray-400">
                      <span>Instrumental</span>
                      <span className="text-gray-600">
                        {mixParams.instrumental_gain_db.toFixed(1)} dB
                      </span>
                    </label>
                    <input
                      type="range"
                      min={-24}
                      max={12}
                      step={0.5}
                      value={mixParams.instrumental_gain_db}
                      onChange={(e) =>
                        setMixParams((p) => ({
                          ...p,
                          instrumental_gain_db: parseFloat(e.target.value),
                          preset: null,
                        }))
                      }
                      className="h-1 w-full cursor-pointer accent-brand-500"
                    />
                  </div>
                </div>
              </div>

              {/* EQ Section */}
              <div>
                <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">
                  Equalização (Vocal)
                </h3>
                <div className="grid gap-4 md:grid-cols-3">
                  <div>
                    <label className="mb-1 flex items-center justify-between text-sm text-gray-400">
                      <span>Low (250Hz)</span>
                      <span className="text-gray-600">
                        {mixParams.eq_low_gain_db.toFixed(1)} dB
                      </span>
                    </label>
                    <input
                      type="range"
                      min={-12}
                      max={12}
                      step={0.5}
                      value={mixParams.eq_low_gain_db}
                      onChange={(e) =>
                        setMixParams((p) => ({
                          ...p,
                          eq_low_gain_db: parseFloat(e.target.value),
                          preset: null,
                        }))
                      }
                      className="h-1 w-full cursor-pointer accent-brand-500"
                    />
                  </div>
                  <div>
                    <label className="mb-1 flex items-center justify-between text-sm text-gray-400">
                      <span>Mid (2.5kHz)</span>
                      <span className="text-gray-600">
                        {mixParams.eq_mid_gain_db.toFixed(1)} dB
                      </span>
                    </label>
                    <input
                      type="range"
                      min={-12}
                      max={12}
                      step={0.5}
                      value={mixParams.eq_mid_gain_db}
                      onChange={(e) =>
                        setMixParams((p) => ({
                          ...p,
                          eq_mid_gain_db: parseFloat(e.target.value),
                          preset: null,
                        }))
                      }
                      className="h-1 w-full cursor-pointer accent-brand-500"
                    />
                  </div>
                  <div>
                    <label className="mb-1 flex items-center justify-between text-sm text-gray-400">
                      <span>High (8kHz)</span>
                      <span className="text-gray-600">
                        {mixParams.eq_high_gain_db.toFixed(1)} dB
                      </span>
                    </label>
                    <input
                      type="range"
                      min={-12}
                      max={12}
                      step={0.5}
                      value={mixParams.eq_high_gain_db}
                      onChange={(e) =>
                        setMixParams((p) => ({
                          ...p,
                          eq_high_gain_db: parseFloat(e.target.value),
                          preset: null,
                        }))
                      }
                      className="h-1 w-full cursor-pointer accent-brand-500"
                    />
                  </div>
                </div>
              </div>

              {/* Dynamics Section */}
              <div>
                <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">
                  Dinâmica
                </h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-1 flex items-center justify-between text-sm text-gray-400">
                      <span>Compressor Threshold</span>
                      <span className="text-gray-600">
                        {mixParams.compressor_threshold_db.toFixed(1)} dB
                      </span>
                    </label>
                    <input
                      type="range"
                      min={-40}
                      max={0}
                      step={1}
                      value={mixParams.compressor_threshold_db}
                      onChange={(e) =>
                        setMixParams((p) => ({
                          ...p,
                          compressor_threshold_db: parseFloat(e.target.value),
                          preset: null,
                        }))
                      }
                      className="h-1 w-full cursor-pointer accent-brand-500"
                    />
                  </div>
                  <div>
                    <label className="mb-1 flex items-center justify-between text-sm text-gray-400">
                      <span>Compressor Ratio</span>
                      <span className="text-gray-600">
                        {mixParams.compressor_ratio.toFixed(1)}:1
                      </span>
                    </label>
                    <input
                      type="range"
                      min={1}
                      max={20}
                      step={0.5}
                      value={mixParams.compressor_ratio}
                      onChange={(e) =>
                        setMixParams((p) => ({
                          ...p,
                          compressor_ratio: parseFloat(e.target.value),
                          preset: null,
                        }))
                      }
                      className="h-1 w-full cursor-pointer accent-brand-500"
                    />
                  </div>
                </div>
              </div>

              {/* Reverb Section */}
              <div>
                <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">
                  Reverb
                </h3>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="mb-1 flex items-center justify-between text-sm text-gray-400">
                      <span>Room Size</span>
                      <span className="text-gray-600">
                        {mixParams.reverb_room_size.toFixed(2)}
                      </span>
                    </label>
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={mixParams.reverb_room_size}
                      onChange={(e) =>
                        setMixParams((p) => ({
                          ...p,
                          reverb_room_size: parseFloat(e.target.value),
                          preset: null,
                        }))
                      }
                      className="h-1 w-full cursor-pointer accent-brand-500"
                    />
                  </div>
                  <div>
                    <label className="mb-1 flex items-center justify-between text-sm text-gray-400">
                      <span>Wet Level</span>
                      <span className="text-gray-600">
                        {mixParams.reverb_wet_level.toFixed(2)}
                      </span>
                    </label>
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={mixParams.reverb_wet_level}
                      onChange={(e) =>
                        setMixParams((p) => ({
                          ...p,
                          reverb_wet_level: parseFloat(e.target.value),
                          preset: null,
                        }))
                      }
                      className="h-1 w-full cursor-pointer accent-brand-500"
                    />
                  </div>
                </div>
              </div>

              {/* Limiter */}
              <div>
                <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">
                  Limiter (Master)
                </h3>
                <div>
                  <label className="mb-1 flex items-center justify-between text-sm text-gray-400">
                    <span>Threshold</span>
                    <span className="text-gray-600">
                      {mixParams.limiter_threshold_db.toFixed(1)} dB
                    </span>
                  </label>
                  <input
                    type="range"
                    min={-12}
                    max={0}
                    step={0.5}
                    value={mixParams.limiter_threshold_db}
                    onChange={(e) =>
                      setMixParams((p) => ({
                        ...p,
                        limiter_threshold_db: parseFloat(e.target.value),
                        preset: null,
                      }))
                    }
                    className="h-1 w-full cursor-pointer accent-brand-500"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Actions */}
          <div className="card space-y-3">
            <h3 className="mb-1 text-sm font-semibold uppercase text-gray-500">
              Ações
            </h3>
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
              Renderizar Mix
            </button>

            {/* Status info */}
            <div className="space-y-2 rounded-lg border border-gray-700 p-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Vocal</span>
                <span
                  className={
                    mixStatus?.has_vocal ? "text-green-400" : "text-gray-600"
                  }
                >
                  {mixStatus?.has_vocal ? "Disponível" : "Não disponível"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Instrumental</span>
                <span
                  className={
                    mixStatus?.has_instrumental
                      ? "text-green-400"
                      : "text-gray-600"
                  }
                >
                  {mixStatus?.has_instrumental
                    ? "Disponível"
                    : "Não disponível"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Mix renderizado</span>
                <span
                  className={
                    mixStatus?.has_mix ? "text-green-400" : "text-gray-600"
                  }
                >
                  {mixStatus?.has_mix ? "Sim" : "Não"}
                </span>
              </div>
            </div>
          </div>

          {/* Export */}
          <div className="card space-y-3">
            <h3 className="mb-1 text-sm font-semibold uppercase text-gray-500 flex items-center gap-2">
              <Download className="h-4 w-4" />
              Exportar
            </h3>
            <select
              className="input"
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value)}
            >
              <option value="wav">WAV (lossless)</option>
              <option value="flac">FLAC (lossless comprimido)</option>
              <option value="mp3">MP3 (320kbps)</option>
              <option value="ogg">OGG Vorbis</option>
            </select>
            <button
              onClick={() => exportMutation.mutate()}
              disabled={exportMutation.isPending || !mixStatus?.has_mix}
              className="btn-secondary w-full flex items-center justify-center gap-2"
            >
              {exportMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Exportar {exportFormat.toUpperCase()}
            </button>

            {/* Previous exports */}
            {mixStatus?.exports && mixStatus.exports.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-gray-500">
                  Exports anteriores:
                </p>
                {mixStatus.exports.map(
                  (
                    exp: {
                      file: string;
                      format: string;
                      download_url: string;
                    },
                    i: number
                  ) => (
                    <a
                      key={i}
                      href={`http://localhost:8000${exp.download_url}`}
                      className="flex items-center justify-between rounded-lg border border-gray-700 p-2 text-xs text-gray-400 hover:border-gray-600 hover:text-gray-300"
                    >
                      <span className="truncate">{exp.file}</span>
                      <span className="ml-2 uppercase text-brand-400">
                        {exp.format}
                      </span>
                    </a>
                  )
                )}
              </div>
            )}
          </div>

          {/* Presets quick-apply */}
          <div className="card space-y-3">
            <h3 className="mb-1 text-sm font-semibold uppercase text-gray-500 flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              Presets Rápidos
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {presets?.presets?.map(
                (p: { name: string; params: Record<string, number> }) => (
                  <button
                    key={p.name}
                    onClick={() => applyPreset(p.name)}
                    className={`rounded-lg border p-2 text-xs font-medium transition-colors ${
                      mixParams.preset === p.name
                        ? "border-brand-500 bg-brand-500/10 text-brand-400"
                        : "border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-300"
                    }`}
                  >
                    {p.name.charAt(0).toUpperCase() + p.name.slice(1)}
                  </button>
                )
              )}
            </div>
          </div>

          {/* Errors */}
          {renderMutation.isError && (
            <div className="rounded-lg border border-red-800 bg-red-900/20 p-3 text-sm text-red-400">
              {renderMutation.error.message}
            </div>
          )}
          {exportMutation.isError && (
            <div className="rounded-lg border border-red-800 bg-red-900/20 p-3 text-sm text-red-400">
              {exportMutation.error.message}
            </div>
          )}

          {/* Navigation */}
          <div className="card">
            <a
              href={`/project/${projectId}/refinement`}
              className="btn-secondary w-full flex items-center justify-center gap-1"
            >
              <ArrowLeft className="h-4 w-4" />
              Voltar ao Refinamento
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
