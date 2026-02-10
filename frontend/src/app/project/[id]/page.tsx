"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { STATUS_LABELS, STEP_LABELS, formatDuration } from "@/lib/audio";
import { PipelineWebSocket, ProgressMessage } from "@/lib/websocket";
import AudioPlayer from "@/components/AudioPlayer";
import PipelineProgress from "@/components/PipelineProgress";
import UploadZone from "@/components/UploadZone";
import LyricsEditor from "@/components/LyricsEditor";
import { showToast } from "@/components/Toast";
import {
  CheckCircle,
  Download,
  Music,
  Music2,
  FileAudio,
  Activity,
  Loader2,
  Mic,
  PenTool,
  Sliders,
  Play,
  ArrowRight,
  AlertCircle,
  Upload,
  BarChart3,
} from "lucide-react";

const PIPELINE_STEPS = [
  "upload",
  "separation",
  "analysis",
  "melody",
  "synthesis",
  "refinement",
  "mix",
] as const;

const STEP_ICONS: Record<string, React.ElementType> = {
  upload: Upload,
  separation: Activity,
  analysis: BarChart3,
  melody: PenTool,
  synthesis: Mic,
  refinement: Sliders,
  mix: Music2,
};

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
        if (msg.status === "completed" && msg.step === "completed") {
          showToast({
            type: "success",
            title: "Pipeline concluido!",
            message: "Todos os passos foram finalizados com sucesso.",
          });
        } else if (msg.status === "error") {
          showToast({
            type: "error",
            title: "Erro no pipeline",
            message: msg.message || "Ocorreu um erro durante o processamento.",
            duration: 8000,
          });
        } else if (msg.status === "completed" && msg.step) {
          showToast({
            type: "info",
            title: `${STEP_LABELS[msg.step] || msg.step} concluido`,
            duration: 3000,
          });
        }
      }
    });

    ws.connect();
    return () => ws.disconnect();
  }, [projectId, refetch]);

  const pipelineMutation = useMutation({
    mutationFn: () => api.startPipeline(projectId),
    onSuccess: () => {
      refetch();
      showToast({
        type: "info",
        title: "Pipeline iniciado",
        message: "O processamento comecou. Acompanhe o progresso acima.",
      });
    },
    onError: (err: Error) => {
      showToast({
        type: "error",
        title: "Erro ao iniciar pipeline",
        message: err.message,
      });
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
          Projeto nao encontrado
        </h2>
      </div>
    );
  }

  // Determine next action for the user
  const getNextAction = () => {
    if (!project.instrumental_filename) {
      return {
        label: "Envie um instrumental para comecar",
        step: "upload",
        icon: Upload,
      };
    }
    if (!project.bpm) {
      return {
        label: "Aguarde a analise do audio...",
        step: "analysis",
        icon: BarChart3,
        loading: true,
      };
    }
    if (!project.lyrics) {
      return {
        label: "Escreva a letra para gerar vocais",
        step: "lyrics",
        icon: PenTool,
      };
    }
    if (
      project.status === "created" ||
      project.status === "analyzing" ||
      project.status === "melody_ready"
    ) {
      return {
        label: "Inicie o pipeline para gerar vocais",
        step: "pipeline",
        icon: Play,
      };
    }
    if (project.status === "completed") {
      return {
        label: "Projeto concluido! Ouca e exporte o resultado",
        step: "completed",
        icon: CheckCircle,
      };
    }
    if (project.status === "error") {
      return {
        label: "Ocorreu um erro. Tente novamente",
        step: "error",
        icon: AlertCircle,
      };
    }
    return {
      label: "Processando...",
      step: "processing",
      icon: Loader2,
      loading: true,
    };
  };

  const nextAction = getNextAction();
  const isProcessing =
    project.status !== "created" &&
    project.status !== "completed" &&
    project.status !== "error" &&
    project.status !== "melody_ready";

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Breadcrumb */}
      <div className="mb-6 flex items-center gap-2 text-sm">
        <a href="/" className="text-gray-500 hover:text-gray-300 transition-colors">
          Projetos
        </a>
        <span className="text-gray-700">/</span>
        <span className="text-gray-300 font-medium">{project.name}</span>
      </div>

      {/* Project Header + Status */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{project.name}</h1>
          {project.description && !project.description.startsWith("{") && (
            <p className="mt-1 text-sm text-gray-500">{project.description}</p>
          )}
          {/* Metadata chips */}
          {project.bpm && (
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="inline-flex items-center gap-1 rounded-md bg-gray-800/60 px-2 py-1 text-xs text-gray-400 border border-gray-700/50">
                <Music className="h-3 w-3" />
                {project.bpm} BPM
              </span>
              {project.musical_key && (
                <span className="rounded-md bg-gray-800/60 px-2 py-1 text-xs text-gray-400 border border-gray-700/50">
                  {project.musical_key}
                </span>
              )}
              {project.duration_seconds && (
                <span className="inline-flex items-center gap-1 rounded-md bg-gray-800/60 px-2 py-1 text-xs text-gray-400 border border-gray-700/50">
                  <FileAudio className="h-3 w-3" />
                  {formatDuration(project.duration_seconds)}
                </span>
              )}
              <span className="rounded-md bg-gray-800/60 px-2 py-1 text-xs font-medium text-gray-400 uppercase border border-gray-700/50">
                {project.language || "it"}
              </span>
            </div>
          )}
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            project.status === "completed"
              ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20"
              : project.status === "error"
              ? "bg-red-500/15 text-red-400 border border-red-500/20"
              : isProcessing
              ? "bg-brand-500/15 text-brand-400 border border-brand-500/20"
              : "bg-gray-500/15 text-gray-400 border border-gray-500/20"
          }`}
        >
          {STATUS_LABELS[project.status] || project.status}
        </span>
      </div>

      {/* Next Action Banner */}
      <div
        className={`mb-6 rounded-xl border p-4 flex items-center gap-4 ${
          nextAction.step === "completed"
            ? "border-emerald-500/20 bg-emerald-500/5"
            : nextAction.step === "error"
            ? "border-red-500/20 bg-red-500/5"
            : nextAction.loading
            ? "border-brand-500/20 bg-brand-500/5"
            : "border-accent-500/20 bg-accent-500/5"
        }`}
      >
        <div
          className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full ${
            nextAction.step === "completed"
              ? "bg-emerald-500/20 text-emerald-400"
              : nextAction.step === "error"
              ? "bg-red-500/20 text-red-400"
              : nextAction.loading
              ? "bg-brand-500/20 text-brand-400"
              : "bg-accent-500/20 text-accent-400"
          }`}
        >
          {nextAction.loading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <nextAction.icon className="h-5 w-5" />
          )}
        </div>
        <div className="flex-1">
          <p
            className={`text-sm font-medium ${
              nextAction.step === "completed"
                ? "text-emerald-300"
                : nextAction.step === "error"
                ? "text-red-300"
                : "text-gray-200"
            }`}
          >
            {nextAction.loading ? "Proximo passo" : "Proximo passo"}
          </p>
          <p className="text-sm text-gray-400">{nextAction.label}</p>
        </div>
        {nextAction.step === "pipeline" && (
          <button
            className="btn-primary flex items-center gap-2 flex-shrink-0"
            onClick={() => pipelineMutation.mutate()}
            disabled={pipelineMutation.isPending}
          >
            {pipelineMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Iniciar Pipeline
          </button>
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
          wsMessage={wsProgress}
        />
      </div>

      {/* Error Message */}
      {project.error_message && (
        <div className="mb-6 flex items-start gap-3 rounded-lg border border-red-800/50 bg-red-900/10 p-4">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-400 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-300">Erro no processamento</p>
            <p className="mt-1 text-xs text-red-400/80">{project.error_message}</p>
          </div>
        </div>
      )}

      {/* Results — visible when completed */}
      {project.status === "completed" && (
        <div className="mb-8 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-6">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle className="h-6 w-6 text-emerald-400" />
            <h2 className="text-lg font-bold text-emerald-300">
              Projeto Concluido
            </h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-gray-700/50 bg-gray-900/50 p-4">
              <h3 className="mb-3 text-sm font-semibold text-white">
                Mixagem Final
              </h3>
              <AudioPlayer projectId={projectId} filename="mix_final.wav" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white mb-3">
                Downloads
              </h3>
              <div className="space-y-2">
                {["mix_final.wav", "vocals_refined.wav", "vocals_raw.wav", "melody.mid"].map(
                  (file) => (
                    <a
                      key={file}
                      href={api.getAudioUrl(projectId, file)}
                      className="flex items-center gap-2 rounded-lg border border-gray-700/50 bg-gray-900/30 p-2.5 text-xs text-gray-400 hover:border-gray-600 hover:text-gray-300 transition-colors"
                      download
                    >
                      <Download className="h-3.5 w-3.5 flex-shrink-0" />
                      <span className="truncate">{file}</span>
                    </a>
                  )
                )}
              </div>
              <a
                href={`/project/${projectId}/mix`}
                className="btn-primary w-full flex items-center justify-center gap-2 text-sm mt-3"
              >
                <Sliders className="h-4 w-4" />
                Ajustar Mix e Exportar
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="grid gap-6 lg:grid-cols-3">
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

          {/* Lyrics Editor */}
          {project.instrumental_filename && (
            <div className="card">
              <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
                <PenTool className="h-5 w-5 text-accent-400" />
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
          {/* Quick Actions */}
          {project.instrumental_filename && project.bpm && (
            <div className="card">
              <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-gray-500">
                Acoes rapidas
              </h3>
              {project.lyrics && (
                <button
                  className="btn-primary w-full flex items-center justify-center gap-2 mb-3"
                  onClick={() => pipelineMutation.mutate()}
                  disabled={
                    pipelineMutation.isPending || isProcessing
                  }
                >
                  {pipelineMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                  {isProcessing ? "Processando..." : "Iniciar Pipeline Completo"}
                </button>
              )}

              <div className="space-y-1.5">
                {[
                  { step: "melody", icon: PenTool, label: "Editor de Melodia" },
                  { step: "synthesis", icon: Mic, label: "Sintese Vocal" },
                  { step: "refinement", icon: Sliders, label: "Refinamento" },
                  { step: "mix", icon: Music2, label: "Mixagem" },
                ].map(({ step, icon: Icon, label }) => (
                  <a
                    key={step}
                    href={`/project/${projectId}/${step}`}
                    className="flex items-center gap-3 rounded-lg border border-gray-800/50 p-2.5 text-sm text-gray-400 transition-all hover:border-brand-500/30 hover:bg-brand-500/5 hover:text-gray-200"
                  >
                    <Icon className="h-4 w-4 flex-shrink-0" />
                    <span className="flex-1">{label}</span>
                    <ArrowRight className="h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-100" />
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Project Info */}
          <div className="card">
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-gray-500">
              Informacoes
            </h3>
            <dl className="space-y-2.5 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Idioma</dt>
                <dd className="text-gray-300 font-medium">
                  {{ it: "Italiano", pt: "Português", en: "Inglês", es: "Espanhol", ja: "Japonês" }[project.language || "it"] || project.language}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Engine</dt>
                <dd className="text-gray-300 font-medium">
                  {project.synthesis_engine || "DiffSinger"}
                </dd>
              </div>
              {project.voice_model && (
                <div className="flex justify-between">
                  <dt className="text-gray-500">Voz</dt>
                  <dd className="text-gray-300 font-medium">{project.voice_model}</dd>
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

          {/* Pipeline Steps Status */}
          {pipelineStatus && (
            <div className="card">
              <h3 className="mb-3 text-xs font-bold uppercase tracking-wider text-gray-500">
                Status dos Passos
              </h3>
              <div className="space-y-1.5">
                {PIPELINE_STEPS.map((step, index) => {
                  const stepStatus = (
                    pipelineStatus as Record<string, Record<string, Record<string, boolean>>>
                  ).steps?.[step];
                  const StepIcon = STEP_ICONS[step] || Music;
                  const isComplete = stepStatus?.completed;
                  const isAvailable = stepStatus?.available;
                  const isCurrent = step === project.current_step;

                  return (
                    <div
                      key={step}
                      className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                        isCurrent
                          ? "bg-brand-500/10 border border-brand-500/20"
                          : "border border-transparent"
                      }`}
                    >
                      <div
                        className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                          isComplete
                            ? "bg-emerald-500/20 text-emerald-400"
                            : isCurrent
                            ? "bg-brand-500/20 text-brand-400"
                            : "bg-gray-800 text-gray-600"
                        }`}
                      >
                        {isComplete ? (
                          <CheckCircle className="h-3.5 w-3.5" />
                        ) : isCurrent ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <span className="text-[10px] font-bold">{index + 1}</span>
                        )}
                      </div>
                      <span
                        className={`flex-1 ${
                          isComplete
                            ? "text-emerald-400"
                            : isCurrent
                            ? "text-brand-400 font-medium"
                            : isAvailable
                            ? "text-gray-300"
                            : "text-gray-600"
                        }`}
                      >
                        {STEP_LABELS[step]}
                      </span>
                      <span
                        className={`text-[10px] font-medium uppercase ${
                          isComplete
                            ? "text-emerald-500/60"
                            : isCurrent
                            ? "text-brand-400/60"
                            : isAvailable
                            ? "text-gray-500"
                            : "text-gray-700"
                        }`}
                      >
                        {isComplete
                          ? "Pronto"
                          : isCurrent
                          ? "Em progresso"
                          : isAvailable
                          ? "Disponivel"
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
