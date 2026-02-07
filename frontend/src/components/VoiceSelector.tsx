"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Mic } from "lucide-react";

interface VoiceSelectorProps {
  engine: string;
  selectedVoice: string | null;
  onSelect: (voice: string) => void;
}

interface Voice {
  name: string;
  language?: string;
  path: string;
}

export default function VoiceSelector({
  engine,
  selectedVoice,
  onSelect,
}: VoiceSelectorProps) {
  const { data: voices, isLoading } = useQuery({
    queryKey: ["voices"],
    queryFn: () => api.listVoices(),
  });

  const engineVoices = (
    (voices as Record<string, Voice[]>)?.[engine] || []
  ) as Voice[];

  if (isLoading) {
    return <p className="text-sm text-gray-500">Carregando vozes...</p>;
  }

  if (engineVoices.length === 0) {
    return (
      <div className="rounded-lg border border-gray-700 p-4 text-center">
        <Mic className="mx-auto mb-2 h-8 w-8 text-gray-600" />
        <p className="text-sm text-gray-400">Nenhuma voz disponível</p>
        <p className="text-xs text-gray-600">
          Instale voicebanks em engines/voicebanks/
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {engineVoices.map((voice) => (
        <button
          key={voice.path}
          onClick={() => onSelect(voice.name)}
          className={`flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-colors ${
            selectedVoice === voice.name
              ? "border-brand-500 bg-brand-500/10"
              : "border-gray-700 hover:border-gray-600"
          }`}
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-800">
            <Mic className="h-4 w-4 text-gray-400" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-200">{voice.name}</p>
            {voice.language && (
              <p className="text-xs uppercase text-gray-500">
                {voice.language}
              </p>
            )}
          </div>
        </button>
      ))}
    </div>
  );
}
