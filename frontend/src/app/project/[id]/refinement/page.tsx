"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import AudioPlayer from "@/components/AudioPlayer";
import {
  ArrowLeft,
  ArrowRight,
  Loader2,
  RefreshCw,
  SkipForward,
  Sliders,
} from "lucide-react";

export default function RefinementPage() {
  const params = useParams();
  const queryClient = useQueryClient();
  const projectId = params.id as string;

  const [rvcParams, setRvcParams] = useState({
    model_name: "",
    pitch_shift: 0,
    index_rate: 0.75,
    filter_radius: 3,
    rms_mix_rate: 0.25,
    protect: 0.33,
    f0_method: "rmvpe",
  });

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
  });

  const { data: comparison, refetch: refetchComparison } = useQuery({
    queryKey: ["refinement-compare", projectId],
    queryFn: () => api.getRefinementComparison(projectId),
  });

  const { data: models } = useQuery({
    queryKey: ["rvc-models", projectId],
    queryFn: () => api.listRVCModels(projectId),
  });

  const convertMutation = useMutation({
    mutationFn: () => api.refineVocal(projectId, rvcParams),
    onSuccess: () => {
      refetchComparison();
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });

  const bypassMutation = useMutation({
    mutationFn: () => api.bypassRefinement(projectId),
    onSuccess: () => {
      refetchComparison();
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    },
  });

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
          <span className="text-gray-300">Refinamento Vocal</span>
        </div>
        <h1 className="mt-4 text-2xl font-bold text-white flex items-center gap-2">
          <Sliders className="h-6 w-6 text-brand-400" />
          Refinamento de Timbre
        </h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main */}
        <div className="lg:col-span-2 space-y-6">
          {/* A/B Comparison */}
          <div className="card">
            <h2 className="mb-4 text-lg font-semibold text-white">
              Comparação A/B
            </h2>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <p className="mb-2 text-sm font-medium text-gray-400">
                  Antes (vocal raw)
                </p>
                {comparison?.before ? (
                  <AudioPlayer
                    projectId={projectId}
                    filename={comparison.before.file}
                  />
                ) : (
                  <div className="rounded-lg border border-gray-700 p-8 text-center text-sm text-gray-600">
                    Vocal não disponível
                  </div>
                )}
              </div>
              <div>
                <p className="mb-2 text-sm font-medium text-gray-400">
                  Depois (vocal refinado)
                </p>
                {comparison?.after ? (
                  <AudioPlayer
                    projectId={projectId}
                    filename={comparison.after.file}
                  />
                ) : (
                  <div className="rounded-lg border border-gray-700 p-8 text-center text-sm text-gray-600">
                    Execute a conversão primeiro
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* RVC Parameters */}
          <div className="card">
            <h2 className="mb-4 text-lg font-semibold text-white">
              Parâmetros RVC
            </h2>
            <div className="space-y-4">
              {/* Model selector */}
              <div>
                <label className="mb-1 block text-sm text-gray-400">
                  Modelo de voz
                </label>
                {models && models.models.length > 0 ? (
                  <select
                    className="input"
                    value={rvcParams.model_name}
                    onChange={(e) =>
                      setRvcParams((p) => ({ ...p, model_name: e.target.value }))
                    }
                  >
                    <option value="">Sem modelo (placeholder)</option>
                    {models.models.map((m) => (
                      <option key={m.name} value={m.name}>
                        {m.name} {m.has_index ? "(+ index)" : ""}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="rounded-lg border border-gray-700 p-3 text-sm text-gray-500">
                    Nenhum modelo instalado. Coloque arquivos .pth em engines/applio/models/
                  </div>
                )}
              </div>

              {/* Pitch Shift */}
              <div>
                <label className="mb-1 flex items-center justify-between text-sm text-gray-400">
                  <span>Pitch Shift (semitons)</span>
                  <span className="text-gray-600">{rvcParams.pitch_shift}</span>
                </label>
                <input
                  type="range"
                  min={-24}
                  max={24}
                  step={1}
                  value={rvcParams.pitch_shift}
                  onChange={(e) =>
                    setRvcParams((p) => ({ ...p, pitch_shift: parseInt(e.target.value) }))
                  }
                  className="h-1 w-full cursor-pointer accent-brand-500"
                />
              </div>

              {/* Index Rate */}
              <div>
                <label className="mb-1 flex items-center justify-between text-sm text-gray-400">
                  <span>Index Rate</span>
                  <span className="text-gray-600">{rvcParams.index_rate.toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={rvcParams.index_rate}
                  onChange={(e) =>
                    setRvcParams((p) => ({ ...p, index_rate: parseFloat(e.target.value) }))
                  }
                  className="h-1 w-full cursor-pointer accent-brand-500"
                />
              </div>

              {/* RMS Mix Rate */}
              <div>
                <label className="mb-1 flex items-center justify-between text-sm text-gray-400">
                  <span>RMS Mix Rate</span>
                  <span className="text-gray-600">{rvcParams.rms_mix_rate.toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={rvcParams.rms_mix_rate}
                  onChange={(e) =>
                    setRvcParams((p) => ({ ...p, rms_mix_rate: parseFloat(e.target.value) }))
                  }
                  className="h-1 w-full cursor-pointer accent-brand-500"
                />
              </div>

              {/* Protect */}
              <div>
                <label className="mb-1 flex items-center justify-between text-sm text-gray-400">
                  <span>Protect (consonantes)</span>
                  <span className="text-gray-600">{rvcParams.protect.toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={0.5}
                  step={0.01}
                  value={rvcParams.protect}
                  onChange={(e) =>
                    setRvcParams((p) => ({ ...p, protect: parseFloat(e.target.value) }))
                  }
                  className="h-1 w-full cursor-pointer accent-brand-500"
                />
              </div>

              {/* F0 Method */}
              <div>
                <label className="mb-1 block text-sm text-gray-400">
                  Método F0
                </label>
                <select
                  className="input"
                  value={rvcParams.f0_method}
                  onChange={(e) =>
                    setRvcParams((p) => ({ ...p, f0_method: e.target.value }))
                  }
                >
                  <option value="rmvpe">RMVPE (recomendado)</option>
                  <option value="crepe">CREPE</option>
                  <option value="harvest">Harvest</option>
                  <option value="pm">PM</option>
                </select>
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
              onClick={() => convertMutation.mutate()}
              disabled={convertMutation.isPending}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {convertMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Converter Timbre
            </button>

            <button
              onClick={() => bypassMutation.mutate()}
              disabled={bypassMutation.isPending}
              className="btn-secondary w-full flex items-center justify-center gap-2"
            >
              {bypassMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <SkipForward className="h-4 w-4" />
              )}
              Pular Refinamento
            </button>
          </div>

          {/* Errors */}
          {convertMutation.isError && (
            <div className="rounded-lg border border-red-800 bg-red-900/20 p-3 text-sm text-red-400">
              {convertMutation.error.message}
            </div>
          )}

          {/* Navigation */}
          <div className="card flex gap-2">
            <a
              href={`/project/${projectId}/synthesis`}
              className="btn-secondary flex-1 flex items-center justify-center gap-1"
            >
              <ArrowLeft className="h-4 w-4" />
              Síntese
            </a>
            <a
              href={`/project/${projectId}/mix`}
              className="btn-primary flex-1 flex items-center justify-center gap-1"
            >
              Mix
              <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
