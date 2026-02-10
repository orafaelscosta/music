"use client";

import { STEP_LABELS } from "@/lib/audio";
import { ProgressMessage } from "@/lib/websocket";
import {
  Check,
  Loader2,
  Upload,
  BarChart3,
  Music,
  Mic,
  Sliders,
  Disc3,
  Clock,
  Timer,
} from "lucide-react";

interface PipelineProgressProps {
  steps: string[];
  currentStep: string | null;
  progress: number;
  status?: Record<string, unknown>;
  projectStatus: string;
  wsMessage?: ProgressMessage | null;
}

const STEP_ICONS: Record<string, React.ElementType> = {
  upload: Upload,
  analysis: BarChart3,
  melody: Music,
  synthesis: Mic,
  refinement: Sliders,
  mix: Disc3,
};

const STEP_PROCESSING: Record<string, string> = {
  upload: "Enviando arquivo...",
  analysis: "Analisando audio...",
  melody: "Gerando melodia...",
  synthesis: "Sintetizando vocal...",
  refinement: "Refinando timbre...",
  mix: "Mixando faixas...",
};

function formatTime(seconds: number): string {
  if (seconds < 0) return "--:--";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  if (m > 0) {
    return `${m}m ${s.toString().padStart(2, "0")}s`;
  }
  return `${s}s`;
}

export default function PipelineProgress({
  steps,
  currentStep,
  progress,
  status,
  projectStatus,
  wsMessage,
}: PipelineProgressProps) {
  const stepsStatus = (status?.steps ?? {}) as Record<
    string,
    { completed: boolean; available: boolean }
  >;

  const getStepState = (step: string) => {
    if (stepsStatus[step]?.completed) return "completed";
    if (step === currentStep) return "active";
    if (stepsStatus[step]?.available) return "available";
    return "pending";
  };

  const isProcessing =
    projectStatus !== "created" &&
    projectStatus !== "completed" &&
    projectStatus !== "error";

  // Calculate overall progress percentage
  const completedCount = steps.filter(
    (s) => stepsStatus[s]?.completed
  ).length;
  const overallProgress = isProcessing
    ? Math.round(((completedCount + (progress / 100)) / steps.length) * 100)
    : projectStatus === "completed"
    ? 100
    : Math.round((completedCount / steps.length) * 100);

  // ETA from WebSocket
  const etaSeconds = wsMessage?.eta_seconds;
  const elapsedSeconds = wsMessage?.elapsed_seconds;
  const wsStatusMessage = wsMessage?.message;

  return (
    <div className="card p-0 overflow-hidden">
      {/* Header with overall progress */}
      <div className="flex items-center justify-between px-6 pt-5 pb-3">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-bold uppercase tracking-wider text-gray-400">
            Pipeline
          </h3>
          {projectStatus === "completed" && (
            <span className="rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-400 border border-emerald-500/20">
              Concluido
            </span>
          )}
          {projectStatus === "error" && (
            <span className="rounded-full bg-red-500/15 px-2.5 py-0.5 text-xs font-semibold text-red-400 border border-red-500/20">
              Erro
            </span>
          )}
          {isProcessing && (
            <span className="flex items-center gap-1.5 rounded-full bg-brand-500/15 px-2.5 py-0.5 text-xs font-semibold text-brand-400 border border-brand-500/20">
              <Loader2 className="h-3 w-3 animate-spin" />
              Processando
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          {/* ETA counter */}
          {isProcessing && etaSeconds != null && etaSeconds > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <Timer className="h-3.5 w-3.5 text-accent-400" />
              <span className="text-accent-300 font-semibold tabular-nums">
                ~{formatTime(etaSeconds)}
              </span>
              <span className="text-gray-600">restante</span>
            </div>
          )}
          {/* Elapsed time */}
          {isProcessing && elapsedSeconds != null && elapsedSeconds > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <Clock className="h-3 w-3" />
              <span className="tabular-nums">{formatTime(elapsedSeconds)}</span>
            </div>
          )}
          <span className="text-sm font-bold tabular-nums text-gray-300">
            {overallProgress}%
          </span>
        </div>
      </div>

      {/* Status message from backend */}
      {isProcessing && wsStatusMessage && (
        <div className="mx-6 mb-2 text-xs text-brand-400/80 truncate">
          {wsStatusMessage}
        </div>
      )}

      {/* Overall progress bar */}
      <div className="mx-6 mb-5 h-1.5 rounded-full bg-gray-800/80 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${
            projectStatus === "completed"
              ? "bg-emerald-500"
              : projectStatus === "error"
              ? "bg-red-500"
              : "bg-gradient-to-r from-brand-500 to-accent-500"
          } ${isProcessing ? "animate-progress-stripe" : ""}`}
          style={{ width: `${overallProgress}%` }}
        />
      </div>

      {/* Steps */}
      <div className="px-4 pb-4">
        <div className="grid grid-cols-6 gap-1">
          {steps.map((step, index) => {
            const state = getStepState(step);
            const Icon = STEP_ICONS[step] || Music;
            const isActive = state === "active";
            const isCompleted = state === "completed";
            const isAvailable = state === "available";

            return (
              <div
                key={step}
                className={`relative rounded-lg px-2 py-3 text-center transition-all duration-300 ${
                  isActive
                    ? "bg-brand-500/10 ring-1 ring-brand-500/30"
                    : isCompleted
                    ? "bg-emerald-500/5"
                    : isAvailable
                    ? "bg-gray-800/30"
                    : "opacity-40"
                }`}
              >
                {/* Step number */}
                <div className="mb-1.5 text-[10px] font-bold tabular-nums text-gray-600">
                  {index + 1}/{steps.length}
                </div>

                {/* Icon circle */}
                <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full transition-all">
                  {isCompleted ? (
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
                      <Check className="h-5 w-5" />
                    </div>
                  ) : isActive ? (
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-500/20 text-brand-400 ring-2 ring-brand-500/30">
                      <Loader2 className="h-5 w-5 animate-spin" />
                    </div>
                  ) : isAvailable ? (
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-800 text-gray-400 border border-gray-700">
                      <Icon className="h-5 w-5" />
                    </div>
                  ) : (
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-900 text-gray-700 border border-gray-800">
                      <Icon className="h-5 w-5" />
                    </div>
                  )}
                </div>

                {/* Label */}
                <div
                  className={`text-xs font-semibold ${
                    isCompleted
                      ? "text-emerald-400"
                      : isActive
                      ? "text-brand-400"
                      : isAvailable
                      ? "text-gray-300"
                      : "text-gray-600"
                  }`}
                >
                  {STEP_LABELS[step] || step}
                </div>

                {/* Status text */}
                <div
                  className={`mt-0.5 text-[10px] leading-tight ${
                    isCompleted
                      ? "text-emerald-500/60"
                      : isActive
                      ? "text-brand-400/70"
                      : "text-gray-700"
                  }`}
                >
                  {isCompleted
                    ? "Pronto"
                    : isActive
                    ? STEP_PROCESSING[step]
                    : isAvailable
                    ? "Aguardando"
                    : "Pendente"}
                </div>

                {/* Active step progress */}
                {isActive && (
                  <div className="mt-2 mx-1">
                    <div className="h-0.5 rounded-full bg-gray-800 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-brand-500 transition-all duration-500"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                    <div className="mt-0.5 text-[9px] tabular-nums text-brand-500/70">
                      {progress}%
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
