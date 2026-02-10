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
  Copy,
  ArrowRight,
  Loader2,
  Zap,
  Sparkles,
} from "lucide-react";

interface ProjectTemplate {
  id: string;
  name: string;
  description: string;
  language: string;
  synthesis_engine: string;
  mix_preset: string;
  icon: string;
}

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newLanguage, setNewLanguage] = useState("it");
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);

  const { data: templatesData } = useQuery({
    queryKey: ["templates"],
    queryFn: () => api.listTemplates(),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => api.listProjects(),
  });

  const createMutation = useMutation({
    mutationFn: () => {
      const template = templatesData?.templates?.find(
        (t: ProjectTemplate) => t.id === selectedTemplate
      );
      return api.createProject({
        name: newName,
        description: newDescription || undefined,
        language: template?.language || newLanguage,
        template_id: selectedTemplate || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowCreate(false);
      setNewName("");
      setNewDescription("");
      setSelectedTemplate(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const duplicateMutation = useMutation({
    mutationFn: (id: string) => api.duplicateProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const statusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20";
      case "error":
        return "text-red-400 bg-red-500/10 border border-red-500/20";
      case "created":
        return "text-gray-400 bg-gray-500/10 border border-gray-500/20";
      default:
        return "text-brand-400 bg-brand-500/10 border border-brand-500/20";
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Header with gradient accent */}
      <div className="mb-10 flex items-end justify-between animate-slide-down">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Seus Projetos
          </h1>
          <p className="mt-1.5 text-sm text-gray-500">
            {data?.projects.length
              ? `${data.projects.length} projeto${data.projects.length > 1 ? "s" : ""}`
              : "Crie seu primeiro projeto para gerar vocais com IA"}
          </p>
        </div>
        <div className="flex gap-3">
          <a href="/quick-start" className="btn-secondary flex items-center gap-2">
            <Zap className="h-4 w-4 text-brand-400" />
            Quick Start
          </a>
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Novo Projeto
          </button>
        </div>
      </div>

      {/* Create Project Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md animate-fade-in">
          <div className="card w-full max-w-md animate-scale-in">
            <h2 className="mb-5 text-xl font-bold tracking-tight text-white">
              Novo Projeto
            </h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                createMutation.mutate();
              }}
            >
              <div className="space-y-4">
                {/* Template selector */}
                {templatesData?.templates && templatesData.templates.length > 0 && (
                  <div>
                    <label className="mb-2 block text-xs font-medium uppercase tracking-wider text-gray-500">
                      Template (opcional)
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      {templatesData.templates.map((t: ProjectTemplate) => (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => {
                            if (selectedTemplate === t.id) {
                              setSelectedTemplate(null);
                            } else {
                              setSelectedTemplate(t.id);
                              setNewLanguage(t.language);
                              if (!newName) setNewName(t.name);
                            }
                          }}
                          className={`rounded-lg border p-2.5 text-left text-xs transition-all duration-200 ${
                            selectedTemplate === t.id
                              ? "border-brand-500/50 bg-brand-500/10 text-brand-400 shadow-sm shadow-brand-500/10"
                              : "border-gray-700/50 text-gray-400 hover:border-gray-600 hover:bg-gray-800/50"
                          }`}
                        >
                          <span className="font-medium">{t.name}</span>
                          <br />
                          <span className="text-gray-600">{t.description}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                <div>
                  <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-gray-500">
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
                  <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-gray-500">
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
                  <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-gray-500">
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
        <div className="flex flex-col items-center justify-center py-20 animate-fade-in">
          <div className="relative mb-6">
            <div className="absolute -inset-4 rounded-full bg-brand-500/10 animate-glow-pulse" />
            <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl border border-gray-800 bg-gray-900/80">
              <Sparkles className="h-10 w-10 text-gray-600" />
            </div>
          </div>
          <h2 className="mb-2 text-xl font-semibold tracking-tight text-gray-300">
            Nenhum projeto ainda
          </h2>
          <p className="mb-8 max-w-sm text-center text-sm text-gray-500">
            Crie um projeto manualmente ou use o Quick Start para gerar vocais em um clique
          </p>
          <div className="flex gap-3">
            <a href="/quick-start" className="btn-secondary flex items-center gap-2">
              <Zap className="h-4 w-4 text-brand-400" />
              Quick Start
            </a>
            <button
              onClick={() => setShowCreate(true)}
              className="btn-primary flex items-center gap-2"
            >
              <Plus className="h-4 w-4" />
              Criar Projeto
            </button>
          </div>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data?.projects.map((project: Project, index: number) => (
            <div
              key={project.id}
              className={`card-hover group relative animate-slide-up stagger-${Math.min(index + 1, 8)}`}
            >
              {/* Subtle glow on active projects */}
              {project.status !== "created" && project.status !== "completed" && project.status !== "error" && (
                <div className="absolute -inset-px rounded-xl bg-gradient-to-r from-brand-500/20 to-accent-500/20 opacity-0 transition-opacity group-hover:opacity-100" />
              )}

              <div className="relative">
                <div className="mb-3 flex items-start justify-between">
                  <h3 className="text-base font-semibold tracking-tight text-white group-hover:text-brand-100 transition-colors">
                    {project.name}
                  </h3>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${statusColor(
                      project.status
                    )}`}
                  >
                    {STATUS_LABELS[project.status] || project.status}
                  </span>
                </div>

                {project.description && (
                  <p className="mb-3 text-xs text-gray-500 line-clamp-2">
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
                    <span className="rounded bg-gray-800/60 px-1.5 py-0.5 text-[10px] font-medium">
                      {project.musical_key}
                    </span>
                  )}
                  {project.duration_seconds && (
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDuration(project.duration_seconds)}
                    </span>
                  )}
                  {project.language && (
                    <span className="rounded bg-gray-800/60 px-1.5 py-0.5 text-[10px] font-medium uppercase">
                      {project.language}
                    </span>
                  )}
                </div>

                {/* Progress bar */}
                {project.status !== "created" &&
                  project.status !== "completed" &&
                  project.status !== "error" && (
                    <div className="mb-4">
                      <div className="h-1 w-full rounded-full bg-gray-800/80">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-brand-500 to-accent-500 transition-all duration-500"
                          style={{ width: `${project.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                <div className="flex items-center justify-between">
                  <div className="flex gap-1">
                    <button
                      onClick={() => duplicateMutation.mutate(project.id)}
                      className="rounded-md p-1.5 text-gray-600 opacity-0 transition-all hover:bg-white/[0.05] hover:text-brand-400 group-hover:opacity-100"
                      title="Duplicar projeto"
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => deleteMutation.mutate(project.id)}
                      className="rounded-md p-1.5 text-gray-600 opacity-0 transition-all hover:bg-red-500/10 hover:text-red-400 group-hover:opacity-100"
                      title="Excluir projeto"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <a
                    href={`/project/${project.id}`}
                    className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-brand-400 transition-all hover:bg-brand-500/10 hover:text-brand-300"
                  >
                    Abrir
                    <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                  </a>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
