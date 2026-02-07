"use client";

import { STEP_LABELS } from "@/lib/audio";
import { Check, Loader2, Circle } from "lucide-react";

interface PipelineProgressProps {
  steps: string[];
  currentStep: string | null;
  progress: number;
  status?: Record<string, unknown>;
  projectStatus: string;
}

export default function PipelineProgress({
  steps,
  currentStep,
  progress,
  status,
  projectStatus,
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

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold uppercase text-gray-500">
          Pipeline
        </h3>
        {currentStep && projectStatus !== "completed" && projectStatus !== "error" && (
          <span className="text-xs text-brand-400">
            {STEP_LABELS[currentStep]} — {progress}%
          </span>
        )}
      </div>

      {/* Progress Bar (overall) */}
      {currentStep && projectStatus !== "completed" && projectStatus !== "error" && (
        <div className="mb-4 h-1 w-full rounded-full bg-gray-800">
          <div
            className="h-full rounded-full bg-brand-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Steps */}
      <div className="flex items-center justify-between">
        {steps.map((step, index) => {
          const state = getStepState(step);
          return (
            <div key={step} className="flex items-center">
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full border-2 transition-all ${
                    state === "completed"
                      ? "border-green-500 bg-green-500/20 text-green-400"
                      : state === "active"
                      ? "border-brand-500 bg-brand-500/20 text-brand-400"
                      : state === "available"
                      ? "border-gray-600 bg-gray-800 text-gray-400"
                      : "border-gray-700 bg-gray-900 text-gray-600"
                  }`}
                >
                  {state === "completed" ? (
                    <Check className="h-4 w-4" />
                  ) : state === "active" ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Circle className="h-3 w-3" />
                  )}
                </div>
                <span
                  className={`mt-1.5 text-xs ${
                    state === "completed"
                      ? "text-green-400"
                      : state === "active"
                      ? "text-brand-400"
                      : "text-gray-600"
                  }`}
                >
                  {STEP_LABELS[step] || step}
                </span>
              </div>
              {/* Connector line */}
              {index < steps.length - 1 && (
                <div
                  className={`mx-2 h-0.5 w-8 sm:w-12 lg:w-16 ${
                    stepsStatus[steps[index + 1]]?.completed ||
                    steps[index + 1] === currentStep
                      ? "bg-brand-500/50"
                      : "bg-gray-800"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
