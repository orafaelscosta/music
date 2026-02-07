"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Save, Loader2 } from "lucide-react";

interface LyricsEditorProps {
  projectId: string;
  initialLyrics: string;
  language: string;
}

export default function LyricsEditor({
  projectId,
  initialLyrics,
  language,
}: LyricsEditorProps) {
  const [lyrics, setLyrics] = useState(initialLyrics);
  const [hasChanges, setHasChanges] = useState(false);

  const saveMutation = useMutation({
    mutationFn: () => api.updateProject(projectId, { lyrics }),
    onSuccess: () => setHasChanges(false),
  });

  const handleChange = (value: string) => {
    setLyrics(value);
    setHasChanges(value !== initialLyrics);
  };

  const languageHints: Record<string, string> = {
    it: "Scrivi i testi in italiano...",
    pt: "Escreva a letra em português...",
    en: "Write lyrics in English...",
    es: "Escribe la letra en español...",
    fr: "Écrivez les paroles en français...",
    de: "Schreiben Sie den Text auf Deutsch...",
    ja: "日本語で歌詞を入力...",
  };

  return (
    <div>
      <textarea
        className="input min-h-[200px] resize-y font-mono text-sm leading-relaxed"
        placeholder={languageHints[language] || "Escreva a letra..."}
        value={lyrics}
        onChange={(e) => handleChange(e.target.value)}
        spellCheck={false}
      />

      <div className="mt-3 flex items-center justify-between">
        <span className="text-xs text-gray-600">
          {lyrics.split("\n").filter((l) => l.trim()).length} linhas
          {" | "}
          {lyrics.length} caracteres
        </span>

        <button
          onClick={() => saveMutation.mutate()}
          disabled={!hasChanges || saveMutation.isPending}
          className="btn-primary flex items-center gap-2"
        >
          {saveMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          Salvar Letra
        </button>
      </div>

      {saveMutation.isSuccess && !hasChanges && (
        <p className="mt-2 text-xs text-green-400">Letra salva com sucesso</p>
      )}
    </div>
  );
}
