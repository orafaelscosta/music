"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import { STATUS_LABELS } from "@/lib/audio";
import AudioPlayer from "@/components/AudioPlayer";
import { ArrowLeft, Loader2, FileAudio, Mic, Sliders, Music2 } from "lucide-react";

interface AudioStage {
  id: string;
  label: string;
  filename: string;
  icon: React.ReactNode;
  description: string;
}

const AUDIO_STAGES: AudioStage[] = [
  {
    id: "instrumental",
    label: "Instrumental",
    filename: "", // será preenchido com extensão real
    icon: <FileAudio className="h-4 w-4" />,
    description: "Áudio instrumental original",
  },
  {
    id: "vocals_raw",
    label: "Vocal Bruto",
    filename: "vocals_raw.wav",
    icon: <Mic className="h-4 w-4" />,
    description: "Vocal gerado pelo engine de síntese",
  },
  {
    id: "vocals_refined",
    label: "Vocal Refinado",
    filename: "vocals_refined.wav",
    icon: <Sliders className="h-4 w-4" />,
    description: "Vocal após refinamento de timbre (RVC)",
  },
  {
    id: "mix_final",
    label: "Mix Final",
    filename: "mix_final.wav",
    icon: <Music2 className="h-4 w-4" />,
    description: "Mixagem final do vocal com instrumental",
  },
];

export default function ComparePage() {
  const params = useParams();
  const projectId = params.id as string;
  const [selectedA, setSelectedA] = useState("vocals_raw");
  const [selectedB, setSelectedB] = useState("vocals_refined");

  const { data: project, isLoading } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
  });

  const { data: pipelineStatus } = useQuery({
    queryKey: ["pipeline-status", projectId],
    queryFn: () => api.getPipelineStatus(projectId),
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

  // Montar lista de stages com o filename correto do instrumental
  const stages = AUDIO_STAGES.map((s) => {
    if (s.id === "instrumental" && project.audio_format) {
      return { ...s, filename: `instrumental.${project.audio_format}` };
    }
    return s;
  });

  // Verificar quais stages têm arquivos disponíveis
  const stepsStatus = (pipelineStatus as Record<string, Record<string, Record<string, boolean>>>)?.steps;
  const isStageAvailable = (stageId: string): boolean => {
    switch (stageId) {
      case "instrumental":
        return !!project.instrumental_filename;
      case "vocals_raw":
        return !!stepsStatus?.synthesis?.completed;
      case "vocals_refined":
        return !!stepsStatus?.refinement?.completed;
      case "mix_final":
        return !!stepsStatus?.mix?.completed;
      default:
        return false;
    }
  };

  const availableStages = stages.filter((s) => isStageAvailable(s.id));
  const stageA = stages.find((s) => s.id === selectedA);
  const stageB = stages.find((s) => s.id === selectedB);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <a
            href={`/project/${projectId}`}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-300"
          >
            <ArrowLeft className="h-4 w-4" />
            Voltar ao projeto
          </a>
        </div>
        <h1 className="text-2xl font-bold text-white">
          Comparação de Áudios
        </h1>
        <p className="mt-1 text-gray-400">
          Compare os diferentes estágios do pipeline lado a lado —{" "}
          <span className="text-gray-300">{project.name}</span>
        </p>
      </div>

      {/* Estágios disponíveis */}
      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {stages.map((stage) => {
          const available = isStageAvailable(stage.id);
          return (
            <div
              key={stage.id}
              className={`rounded-lg border p-3 ${
                available
                  ? "border-green-800 bg-green-900/10"
                  : "border-gray-800 bg-gray-900/30 opacity-50"
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={available ? "text-green-400" : "text-gray-600"}>
                  {stage.icon}
                </span>
                <span className={`text-sm font-medium ${available ? "text-white" : "text-gray-600"}`}>
                  {stage.label}
                </span>
              </div>
              <p className="text-xs text-gray-500">{stage.description}</p>
              <span className={`mt-1 inline-block text-xs ${available ? "text-green-500" : "text-gray-700"}`}>
                {available ? "Disponível" : "Pendente"}
              </span>
            </div>
          );
        })}
      </div>

      {availableStages.length < 2 ? (
        <div className="card text-center py-12">
          <p className="text-gray-400 mb-2">
            É necessário pelo menos 2 estágios concluídos para comparar.
          </p>
          <p className="text-sm text-gray-600">
            Status atual:{" "}
            <span className="text-gray-400">
              {STATUS_LABELS[project.status] || project.status}
            </span>
          </p>
        </div>
      ) : (
        <>
          {/* Seletores A/B */}
          <div className="mb-6 grid grid-cols-2 gap-6">
            <div>
              <label className="mb-2 block text-sm font-medium text-brand-400">
                Áudio A
              </label>
              <select
                className="input w-full"
                value={selectedA}
                onChange={(e) => setSelectedA(e.target.value)}
              >
                {availableStages.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-brand-400">
                Áudio B
              </label>
              <select
                className="input w-full"
                value={selectedB}
                onChange={(e) => setSelectedB(e.target.value)}
              >
                {availableStages.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Players A/B */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Player A */}
            <div className="card">
              <div className="flex items-center gap-2 mb-4">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">
                  A
                </span>
                <h3 className="text-lg font-semibold text-white">
                  {stageA?.label || "—"}
                </h3>
              </div>
              {stageA && isStageAvailable(stageA.id) ? (
                <AudioPlayer
                  projectId={projectId}
                  filename={stageA.filename}
                />
              ) : (
                <p className="text-sm text-gray-500 py-8 text-center">
                  Estágio não disponível
                </p>
              )}
              <p className="mt-3 text-xs text-gray-500">
                {stageA?.description}
              </p>
            </div>

            {/* Player B */}
            <div className="card">
              <div className="flex items-center gap-2 mb-4">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-purple-600 text-xs font-bold text-white">
                  B
                </span>
                <h3 className="text-lg font-semibold text-white">
                  {stageB?.label || "—"}
                </h3>
              </div>
              {stageB && isStageAvailable(stageB.id) ? (
                <AudioPlayer
                  projectId={projectId}
                  filename={stageB.filename}
                />
              ) : (
                <p className="text-sm text-gray-500 py-8 text-center">
                  Estágio não disponível
                </p>
              )}
              <p className="mt-3 text-xs text-gray-500">
                {stageB?.description}
              </p>
            </div>
          </div>

          {/* Dica */}
          <div className="mt-6 rounded-lg border border-gray-800 bg-gray-900/30 p-4">
            <p className="text-xs text-gray-500">
              Dica: Use os seletores acima para comparar qualquer combinação de estágios.
              Ouça as diferenças entre o vocal bruto e refinado, ou compare o
              instrumental original com a mixagem final.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
