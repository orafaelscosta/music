"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { STATUS_LABELS, STEP_LABELS, formatDuration } from "@/lib/audio";
import { PipelineWebSocket, ProgressMessage } from "@/lib/websocket";
import AudioPlayer from "@/components/AudioPlayer";
import PipelineProgress from "@/components/PipelineProgress";
import UploadZone from "@/components/UploadZone";
import LyricsEditor from "@/components/LyricsEditor";
import {
  Music,
  FileAudio,
  Activity,
  Settings,
  Loader2,
  PenTool,
} from "lucide-react";

const PIPELINE_STEPS = [
  "upload",
  "analysis",
  "melody",
  "synthesis",
  "refinement",
  "mix",
] as const;

export default function ProjectPage() {
  const params = useParams();
  const projectId = params.id as string;
  const [wsProgress, setWsProgress] = useState<ProgressMessage | null>(null);

  const {
    data: project,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
    refetchInterval: 5000,
  });

  const { data: pipelineStatus } = useQuery({
    queryKey: ["pipeline-status", projectId],
    queryFn: () => api.getPipelineStatus(projectId),
    refetchInterval: 3000,
  });

  // WebSocket para progresso em tempo real
  useEffect(() => {
    const ws = new PipelineWebSocket(projectId);

    ws.onProgress((msg) => {
      if (msg.type === "progress") {
        setWsProgress(msg);
        refetch();
      }
    });

    ws.connect();
    return () => ws.disconnect();
  }, [projectId, refetch]);

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
      {/* Project Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <a
            href="/"
            className="text-sm text-gray-500 hover:text-gray-300"
          >
            Projetos
          </a>
          <span className="text-gray-600">/</span>
          <span className="text-sm text-gray-300">{project.name}</span>
        </div>
        <div className="mt-4 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">{project.name}</h1>
            {project.description && (
              <p className="mt-1 text-gray-400">{project.description}</p>
            )}
          </div>
          <span
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              project.status === "completed"
                ? "bg-green-400/10 text-green-400"
                : project.status === "error"
                ? "bg-red-400/10 text-red-400"
                : "bg-brand-400/10 text-brand-400"
            }`}
          >
            {STATUS_LABELS[project.status] || project.status}
          </span>
        </div>

        {/* Metadata */}
        {project.bpm && (
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-gray-400">
            <span className="flex items-center gap-1">
              <Music className="h-4 w-4" />
              {project.bpm} BPM
            </span>
            {project.musical_key && <span>{project.musical_key}</span>}
            {project.duration_seconds && (
              <span className="flex items-center gap-1">
                <FileAudio className="h-4 w-4" />
                {formatDuration(project.duration_seconds)}
              </span>
            )}
            {project.sample_rate && <span>{project.sample_rate} Hz</span>}
            <span className="uppercase">{project.language || "it"}</span>
          </div>
        )}
      </div>

      {/* Pipeline Progress */}
      <div className="mb-8">
        <PipelineProgress
          steps={PIPELINE_STEPS as unknown as string[]}
          currentStep={project.current_step}
          progress={wsProgress?.progress ?? project.progress}
          status={pipelineStatus as Record<string, unknown> | undefined}
          projectStatus={project.status}
        />
      </div>

      {/* Error Message */}
      {project.error_message && (
        <div className="mb-8 rounded-lg border border-red-800 bg-red-900/20 p-4">
          <p className="text-sm text-red-400">{project.error_message}</p>
        </div>
      )}

      {/* Main Content - Step-based */}
      <div className="grid gap-8 lg:grid-cols-3">
        {/* Left: Main area */}
        <div className="lg:col-span-2 space-y-6">
          {/* Upload Section */}
          {!project.instrumental_filename && (
            <div className="card">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                <FileAudio className="h-5 w-5 text-brand-400" />
                Upload do Instrumental
              </h2>
              <UploadZone projectId={projectId} onUploadComplete={refetch} />
            </div>
          )}

          {/* Audio Player */}
          {project.instrumental_filename && (
            <div className="card">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                <Activity className="h-5 w-5 text-brand-400" />
                Instrumental
              </h2>
              <AudioPlayer
                projectId={projectId}
                filename={`instrumental.${project.audio_format}`}
              />
            </div>
          )}

          {/* Melody Editor Link */}
          {project.instrumental_filename && project.bpm && (
            <div className="card">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                <PenTool className="h-5 w-5 text-brand-400" />
                Melodia
              </h2>
              <p className="mb-4 text-sm text-gray-400">
                Crie ou edite a melodia vocal no piano roll. Extraia do
                instrumental, importe MIDI ou desenhe manualmente.
              </p>
              <a
                href={`/project/${projectId}/melody`}
                className="btn-primary inline-flex items-center gap-2"
              >
                <Music className="h-4 w-4" />
                Abrir Editor de Melodia
              </a>
            </div>
          )}

          {/* Lyrics Editor */}
          {project.instrumental_filename && (
            <div className="card">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                <Settings className="h-5 w-5 text-brand-400" />
                Letra
              </h2>
              <LyricsEditor
                projectId={projectId}
                initialLyrics={project.lyrics || ""}
                language={project.language || "it"}
              />
            </div>
          )}
        </div>

        {/* Right: Sidebar */}
        <div className="space-y-6">
          {/* Project Info */}
          <div className="card">
            <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">
              Informações
            </h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Idioma</dt>
                <dd className="text-gray-300 uppercase">
                  {project.language || "it"}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Engine</dt>
                <dd className="text-gray-300">
                  {project.synthesis_engine || "DiffSinger"}
                </dd>
              </div>
              {project.voice_model && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Voz</dt>
                  <dd className="text-gray-300">{project.voice_model}</dd>
                </div>
              )}
              <div className="flex justify-between">
                <dt className="text-gray-500">Criado</dt>
                <dd className="text-gray-300">
                  {new Date(project.created_at).toLocaleDateString("pt-BR")}
                </dd>
              </div>
            </dl>
          </div>

          {/* Actions */}
          {project.instrumental_filename && project.lyrics && (
            <div className="card">
              <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">
                Ações
              </h3>
              <button
                className="btn-primary w-full"
                onClick={() => api.startPipeline(projectId).then(() => refetch())}
                disabled={
                  project.status === "synthesizing" ||
                  project.status === "refining" ||
                  project.status === "mixing"
                }
              >
                Iniciar Pipeline Completo
              </button>
            </div>
          )}

          {/* Step Status */}
          {pipelineStatus && (
            <div className="card">
              <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">
                Steps do Pipeline
              </h3>
              <div className="space-y-2">
                {PIPELINE_STEPS.map((step) => {
                  const stepStatus = (
                    pipelineStatus as Record<string, Record<string, Record<string, boolean>>>
                  ).steps?.[step];
                  return (
                    <div
                      key={step}
                      className="flex items-center justify-between text-sm"
                    >
                      <span className="text-gray-400">
                        {STEP_LABELS[step]}
                      </span>
                      <span
                        className={
                          stepStatus?.completed
                            ? "text-green-400"
                            : stepStatus?.available
                            ? "text-yellow-400"
                            : "text-gray-600"
                        }
                      >
                        {stepStatus?.completed
                          ? "Concluído"
                          : stepStatus?.available
                          ? "Disponível"
                          : "Pendente"}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
