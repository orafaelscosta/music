"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { showToast } from "@/components/Toast";
import {
  ArrowLeft,
  Cpu,
  FolderOpen,
  HardDrive,
  Loader2,
  RefreshCw,
  Settings,
} from "lucide-react";

export default function SettingsPage() {
  const [testingEngine, setTestingEngine] = useState<string | null>(null);

  const { data: engines, isLoading: enginesLoading } = useQuery({
    queryKey: ["engines"],
    queryFn: () => api.listEngines(),
  });

  const { data: voices } = useQuery({
    queryKey: ["voices"],
    queryFn: () => api.listVoices(),
  });

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.healthCheck(),
  });

  const testEngineMutation = useMutation({
    mutationFn: async (engine: string) => {
      setTestingEngine(engine);
      return api.testEngine(engine);
    },
    onSuccess: (data, engine) => {
      setTestingEngine(null);
      showToast({
        type: data.available ? "success" : "warning",
        title: `${engine}`,
        message: data.available
          ? "Engine disponível e funcionando"
          : "Engine não disponível",
      });
    },
    onError: (_, engine) => {
      setTestingEngine(null);
      showToast({
        type: "error",
        title: `${engine}`,
        message: "Erro ao testar engine",
      });
    },
  });

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 text-sm">
          <a href="/" className="text-gray-500 hover:text-gray-300">
            <ArrowLeft className="inline h-4 w-4 mr-1" />
            Projetos
          </a>
          <span className="text-gray-600">/</span>
          <span className="text-gray-300">Configurações</span>
        </div>
        <h1 className="mt-4 text-2xl font-bold text-white flex items-center gap-2">
          <Settings className="h-6 w-6 text-brand-400" />
          Configurações
        </h1>
      </div>

      <div className="space-y-6">
        {/* System Status */}
        <div className="card">
          <h2 className="mb-4 text-lg font-semibold text-white flex items-center gap-2">
            <HardDrive className="h-5 w-5 text-brand-400" />
            Status do Sistema
          </h2>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-gray-700 p-4">
              <p className="text-xs font-medium text-gray-500 uppercase">
                API Backend
              </p>
              <p
                className={`mt-1 text-lg font-semibold ${
                  health ? "text-green-400" : "text-red-400"
                }`}
              >
                {health ? "Online" : "Offline"}
              </p>
              {health && (
                <p className="text-xs text-gray-500">
                  v{(health as Record<string, string>).version}
                </p>
              )}
            </div>
            <div className="rounded-lg border border-gray-700 p-4">
              <p className="text-xs font-medium text-gray-500 uppercase">
                Engines AI
              </p>
              <p className="mt-1 text-lg font-semibold text-white">
                {enginesLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  `${
                    Object.values(
                      (engines as Record<string, Record<string, boolean>>) || {}
                    ).filter((e) => e?.available).length
                  } disponíveis`
                )}
              </p>
            </div>
            <div className="rounded-lg border border-gray-700 p-4">
              <p className="text-xs font-medium text-gray-500 uppercase">
                Voicebanks
              </p>
              <p className="mt-1 text-lg font-semibold text-white">
                {(voices as Record<string, unknown[]>)?.voicebanks?.length || 0}{" "}
                instalados
              </p>
            </div>
          </div>
        </div>

        {/* AI Engines */}
        <div className="card">
          <h2 className="mb-4 text-lg font-semibold text-white flex items-center gap-2">
            <Cpu className="h-5 w-5 text-brand-400" />
            Engines de IA
          </h2>
          <div className="space-y-3">
            {[
              {
                name: "DiffSinger",
                key: "diffsinger",
                description:
                  "Motor principal de síntese vocal. Requer voicebanks em engines/voicebanks/",
              },
              {
                name: "ACE-Step",
                key: "acestep",
                description:
                  "Geração rápida de vocal com Lyric2Vocal. Modelo baixado via download_models.sh",
              },
              {
                name: "Applio/RVC",
                key: "applio",
                description:
                  "Conversão de timbre vocal. Fork em engines/applio/",
              },
              {
                name: "Pedalboard",
                key: "pedalboard",
                description:
                  "Cadeia de efeitos para mixagem (EQ, compressor, reverb, limiter)",
              },
            ].map((engine) => {
              const engineData =
                engines &&
                (engines as Record<string, Record<string, boolean>>)[
                  engine.key
                ];
              return (
                <div
                  key={engine.key}
                  className="flex items-center justify-between rounded-lg border border-gray-700 p-4"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-white">{engine.name}</h3>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          engineData?.available
                            ? "bg-green-400/10 text-green-400"
                            : "bg-gray-400/10 text-gray-500"
                        }`}
                      >
                        {engineData?.available
                          ? "Disponível"
                          : "Não instalado"}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-gray-500">
                      {engine.description}
                    </p>
                  </div>
                  <button
                    onClick={() => testEngineMutation.mutate(engine.key)}
                    disabled={testingEngine === engine.key}
                    className="btn-secondary ml-4 flex items-center gap-1 text-sm"
                  >
                    {testingEngine === engine.key ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <RefreshCw className="h-3 w-3" />
                    )}
                    Testar
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Directory Paths */}
        <div className="card">
          <h2 className="mb-4 text-lg font-semibold text-white flex items-center gap-2">
            <FolderOpen className="h-5 w-5 text-brand-400" />
            Diretórios
          </h2>
          <div className="space-y-2 text-sm">
            {[
              { label: "Projetos", path: "storage/projects/" },
              { label: "DiffSinger", path: "engines/diffsinger/" },
              { label: "Voicebanks", path: "engines/voicebanks/" },
              { label: "ACE-Step", path: "engines/ace-step/" },
              { label: "Applio/RVC", path: "engines/applio/" },
              { label: "Modelos RVC", path: "engines/applio/models/" },
            ].map((dir) => (
              <div
                key={dir.label}
                className="flex items-center justify-between rounded-lg border border-gray-700 p-3"
              >
                <span className="text-gray-400">{dir.label}</span>
                <code className="text-xs text-gray-500">{dir.path}</code>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
