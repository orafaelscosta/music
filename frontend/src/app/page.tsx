"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, Project } from "@/lib/api";
import { STATUS_LABELS, formatDuration } from "@/lib/audio";
import {
  Plus,
  Music,
  Clock,
  Trash2,
  ArrowRight,
  Loader2,
} from "lucide-react";

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newLanguage, setNewLanguage] = useState("it");

  const { data, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.listProjects(),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      api.createProject({
        name: newName,
        description: newDescription || undefined,
        language: newLanguage,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowCreate(false);
      setNewName("");
      setNewDescription("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const statusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "text-green-400 bg-green-400/10";
      case "error":
        return "text-red-400 bg-red-400/10";
      case "created":
        return "text-gray-400 bg-gray-400/10";
      default:
        return "text-brand-400 bg-brand-400/10";
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Projetos</h1>
          <p className="mt-1 text-gray-400">
            Gerencie seus projetos de vocal por IA
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Novo Projeto
        </button>
      </div>

      {/* Create Project Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="card w-full max-w-md">
            <h2 className="mb-4 text-xl font-bold text-white">
              Novo Projeto
            </h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                createMutation.mutate();
              }}
            >
              <div className="space-y-4">
                <div>
                  <label className="mb-1 block text-sm text-gray-400">
                    Nome do projeto
                  </label>
                  <input
                    type="text"
                    className="input"
                    placeholder="Ex: Minha Canzone Italiana"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    required
                    autoFocus
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-gray-400">
                    Descrição (opcional)
                  </label>
                  <textarea
                    className="input min-h-[80px] resize-none"
                    placeholder="Breve descrição do projeto..."
                    value={newDescription}
                    onChange={(e) => setNewDescription(e.target.value)}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm text-gray-400">
                    Idioma principal
                  </label>
                  <select
                    className="input"
                    value={newLanguage}
                    onChange={(e) => setNewLanguage(e.target.value)}
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
              </div>
              <div className="mt-6 flex justify-end gap-3">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowCreate(false)}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={!newName.trim() || createMutation.isPending}
                >
                  {createMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : null}
                  Criar Projeto
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Projects Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-brand-500" />
        </div>
      ) : data?.projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20">
          <Music className="mb-4 h-16 w-16 text-gray-600" />
          <h2 className="mb-2 text-xl font-semibold text-gray-400">
            Nenhum projeto ainda
          </h2>
          <p className="mb-6 text-gray-500">
            Crie seu primeiro projeto para começar a gerar vocais
          </p>
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Criar Projeto
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data?.projects.map((project: Project) => (
            <div key={project.id} className="card group relative">
              <div className="mb-3 flex items-start justify-between">
                <h3 className="text-lg font-semibold text-white">
                  {project.name}
                </h3>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusColor(
                    project.status
                  )}`}
                >
                  {STATUS_LABELS[project.status] || project.status}
                </span>
              </div>

              {project.description && (
                <p className="mb-3 text-sm text-gray-400 line-clamp-2">
                  {project.description}
                </p>
              )}

              <div className="mb-4 flex flex-wrap gap-3 text-xs text-gray-500">
                {project.bpm && (
                  <span className="flex items-center gap-1">
                    <Music className="h-3 w-3" />
                    {project.bpm} BPM
                  </span>
                )}
                {project.musical_key && (
                  <span>{project.musical_key}</span>
                )}
                {project.duration_seconds && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatDuration(project.duration_seconds)}
                  </span>
                )}
                {project.language && (
                  <span className="uppercase">{project.language}</span>
                )}
              </div>

              {/* Progress bar */}
              {project.status !== "created" &&
                project.status !== "completed" &&
                project.status !== "error" && (
                  <div className="mb-4">
                    <div className="h-1.5 w-full rounded-full bg-gray-800">
                      <div
                        className="h-full rounded-full bg-brand-500 transition-all"
                        style={{ width: `${project.progress}%` }}
                      />
                    </div>
                  </div>
                )}

              <div className="flex items-center justify-between">
                <button
                  onClick={() => deleteMutation.mutate(project.id)}
                  className="text-gray-600 opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
                  title="Excluir projeto"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
                <a
                  href={`/project/${project.id}`}
                  className="flex items-center gap-1 text-sm text-brand-400 transition-colors hover:text-brand-300"
                >
                  Abrir
                  <ArrowRight className="h-4 w-4" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
