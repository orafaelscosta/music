"use client";

import { useCallback, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, MelodyData, MelodyNote } from "@/lib/api";
import PianoRoll from "@/components/PianoRoll";
import LyricsEditor from "@/components/LyricsEditor";
import {
  ArrowLeft,
  ArrowRight,
  Download,
  Grid3X3,
  Loader2,
  Music,
  Save,
  Upload,
  Wand2,
  Type,
} from "lucide-react";

export default function MelodyPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const projectId = params.id as string;
  const [localMelody, setLocalMelody] = useState<MelodyData | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
  });

  const { data: melody, isLoading: melodyLoading } = useQuery({
    queryKey: ["melody", projectId],
    queryFn: () => api.getMelody(projectId),
    retry: false,
  });

  const currentMelody = localMelody || melody;

  // Extract melody from instrumental
  const extractMutation = useMutation({
    mutationFn: () => api.extractMelody(projectId),
    onSuccess: (data) => {
      setLocalMelody(data);
      queryClient.invalidateQueries({ queryKey: ["melody", projectId] });
    },
  });

  // Import MIDI
  const importMutation = useMutation({
    mutationFn: (file: File) => api.importMidi(projectId, file),
    onSuccess: (data) => {
      setLocalMelody(data);
      queryClient.invalidateQueries({ queryKey: ["melody", projectId] });
    },
  });

  // Save melody
  const saveMutation = useMutation({
    mutationFn: (data: MelodyData) => api.updateMelody(projectId, data),
    onSuccess: () => {
      setHasUnsavedChanges(false);
      queryClient.invalidateQueries({ queryKey: ["melody", projectId] });
    },
  });

  // Snap to grid
  const snapMutation = useMutation({
    mutationFn: (resolution: number) => api.snapMelodyToGrid(projectId, resolution),
    onSuccess: (data) => {
      setLocalMelody(data);
      queryClient.invalidateQueries({ queryKey: ["melody", projectId] });
    },
  });

  // Syllabify
  const syllabifyMutation = useMutation({
    mutationFn: () => api.syllabifyLyrics(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["melody", projectId] });
      setLocalMelody(null); // Refresh from server
    },
  });

  const handleNotesChange = useCallback(
    (notes: MelodyNote[]) => {
      if (!currentMelody) return;
      const updated: MelodyData = {
        ...currentMelody,
        notes,
        total_notes: notes.length,
      };
      setLocalMelody(updated);
      setHasUnsavedChanges(true);
    },
    [currentMelody]
  );

  const handleSave = () => {
    if (currentMelody) {
      saveMutation.mutate(currentMelody);
    }
  };

  const handleImportMidi = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".mid,.midi";
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (file) importMutation.mutate(file);
    };
    input.click();
  };

  if (projectLoading) {
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

  const isExtracting = extractMutation.isPending;
  const isImporting = importMutation.isPending;

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
          <span className="text-gray-300">Editor de Melodia</span>
        </div>
        <div className="mt-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Music className="h-6 w-6 text-brand-400" />
            Melodia
          </h1>
          <div className="flex items-center gap-2">
            {hasUnsavedChanges && (
              <span className="text-xs text-yellow-400">Alterações não salvas</span>
            )}
            <button
              onClick={handleSave}
              disabled={!hasUnsavedChanges || saveMutation.isPending}
              className="btn-primary flex items-center gap-2"
            >
              {saveMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              Salvar
            </button>
          </div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="mb-4 card flex flex-wrap items-center gap-3">
        <button
          onClick={() => extractMutation.mutate()}
          disabled={isExtracting || !project.instrumental_filename}
          className="btn-secondary flex items-center gap-2"
        >
          {isExtracting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Wand2 className="h-4 w-4" />
          )}
          Extrair do Áudio
        </button>

        <button
          onClick={handleImportMidi}
          disabled={isImporting}
          className="btn-secondary flex items-center gap-2"
        >
          {isImporting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Upload className="h-4 w-4" />
          )}
          Importar MIDI
        </button>

        <div className="h-6 w-px bg-gray-700" />

        <button
          onClick={() => snapMutation.mutate(0.25)}
          disabled={!currentMelody || snapMutation.isPending}
          className="btn-secondary flex items-center gap-2"
          title="Quantizar notas para o grid de 1/4 beat"
        >
          <Grid3X3 className="h-4 w-4" />
          Snap 1/4
        </button>

        <button
          onClick={() => snapMutation.mutate(0.125)}
          disabled={!currentMelody || snapMutation.isPending}
          className="btn-secondary flex items-center gap-2"
          title="Quantizar notas para o grid de 1/8 beat"
        >
          <Grid3X3 className="h-4 w-4" />
          Snap 1/8
        </button>

        <div className="h-6 w-px bg-gray-700" />

        <button
          onClick={() => syllabifyMutation.mutate()}
          disabled={!project.lyrics || syllabifyMutation.isPending}
          className="btn-secondary flex items-center gap-2"
          title="Segmentar letra em sílabas e atribuir às notas"
        >
          {syllabifyMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Type className="h-4 w-4" />
          )}
          Alinhar Sílabas
        </button>

        {currentMelody && (
          <a
            href={api.getAudioUrl(projectId, "melody.mid")}
            download="melody.mid"
            className="btn-secondary ml-auto flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Download MIDI
          </a>
        )}
      </div>

      {/* Error messages */}
      {extractMutation.isError && (
        <div className="mb-4 rounded-lg border border-red-800 bg-red-900/20 p-3 text-sm text-red-400">
          {extractMutation.error.message}
        </div>
      )}
      {importMutation.isError && (
        <div className="mb-4 rounded-lg border border-red-800 bg-red-900/20 p-3 text-sm text-red-400">
          {importMutation.error.message}
        </div>
      )}

      {/* Syllabify results */}
      {syllabifyMutation.isSuccess && syllabifyMutation.data && (
        <div className="mb-4 rounded-lg border border-green-800 bg-green-900/20 p-3 text-sm text-green-400">
          {syllabifyMutation.data.total} sílabas segmentadas
          {syllabifyMutation.data.assigned_to_melody && " e atribuídas às notas"}
        </div>
      )}

      {/* Main content */}
      <div className="grid gap-6 lg:grid-cols-4">
        {/* Piano Roll — main area */}
        <div className="lg:col-span-3">
          <div className="card">
            {melodyLoading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
              </div>
            ) : currentMelody ? (
              <PianoRoll
                melody={currentMelody}
                duration={project.duration_seconds || 30}
                onNotesChange={handleNotesChange}
              />
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-gray-500">
                <Music className="mb-3 h-12 w-12 text-gray-700" />
                <p className="mb-1 text-sm">Nenhuma melodia ainda</p>
                <p className="text-xs text-gray-600">
                  Extraia do instrumental ou importe um arquivo MIDI
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Info */}
          <div className="card">
            <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">
              Informações
            </h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">BPM</dt>
                <dd className="text-gray-300">{project.bpm || "—"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Tonalidade</dt>
                <dd className="text-gray-300">{project.musical_key || "—"}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Notas</dt>
                <dd className="text-gray-300">
                  {currentMelody?.total_notes || 0}
                </dd>
              </div>
              {currentMelody && currentMelody.notes.length > 0 && (
                <>
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Range</dt>
                    <dd className="text-gray-300">
                      {currentMelody.notes.reduce(
                        (min, n) => Math.min(min, n.midi_note),
                        127
                      )}{" "}
                      -{" "}
                      {currentMelody.notes.reduce(
                        (max, n) => Math.max(max, n.midi_note),
                        0
                      )}
                    </dd>
                  </div>
                </>
              )}
            </dl>
          </div>

          {/* Lyrics */}
          <div className="card">
            <h3 className="mb-3 text-sm font-semibold uppercase text-gray-500">
              Letra
            </h3>
            <LyricsEditor
              projectId={projectId}
              initialLyrics={project.lyrics || ""}
              language={project.language || "it"}
            />
          </div>

          {/* Navigation */}
          <div className="card flex gap-2">
            <a
              href={`/project/${projectId}`}
              className="btn-secondary flex-1 flex items-center justify-center gap-1"
            >
              <ArrowLeft className="h-4 w-4" />
              Projeto
            </a>
            <a
              href={`/project/${projectId}/synthesis`}
              className="btn-primary flex-1 flex items-center justify-center gap-1"
            >
              Síntese
              <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
