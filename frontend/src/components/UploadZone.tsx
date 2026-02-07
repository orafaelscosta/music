"use client";

import { useCallback, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { isValidAudioFile, formatFileSize } from "@/lib/audio";
import { Upload, FileAudio, X, Loader2, AlertCircle } from "lucide-react";

interface UploadZoneProps {
  projectId: string;
  onUploadComplete: () => void;
}

export default function UploadZone({
  projectId,
  onUploadComplete,
}: UploadZoneProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploadInstrumental(projectId, file),
    onSuccess: () => {
      setSelectedFile(null);
      onUploadComplete();
    },
  });

  const handleFile = useCallback(
    (file: File) => {
      if (!isValidAudioFile(file)) {
        return;
      }
      setSelectedFile(file);
      uploadMutation.mutate(file);
    },
    [uploadMutation]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragActive(false);
  }, []);

  return (
    <div>
      {/* Drop Zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
          dragActive
            ? "border-brand-500 bg-brand-500/5"
            : "border-gray-700 hover:border-gray-600"
        }`}
      >
        {uploadMutation.isPending ? (
          <div className="flex flex-col items-center">
            <Loader2 className="mb-3 h-10 w-10 animate-spin text-brand-500" />
            <p className="text-sm text-gray-400">
              Enviando e analisando...
            </p>
            {selectedFile && (
              <p className="mt-1 text-xs text-gray-600">
                {selectedFile.name} ({formatFileSize(selectedFile.size)})
              </p>
            )}
          </div>
        ) : (
          <>
            <Upload
              className={`mb-3 h-10 w-10 ${
                dragActive ? "text-brand-400" : "text-gray-600"
              }`}
            />
            <p className="mb-1 text-sm text-gray-300">
              Arraste o instrumental aqui
            </p>
            <p className="text-xs text-gray-500">
              WAV, MP3, FLAC, OGG ou M4A (max 500MB)
            </p>
            <label className="btn-secondary mt-4 cursor-pointer">
              <FileAudio className="mr-2 h-4 w-4" />
              Selecionar arquivo
              <input
                type="file"
                accept=".wav,.mp3,.flac,.ogg,.m4a,audio/*"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFile(file);
                }}
              />
            </label>
          </>
        )}
      </div>

      {/* Error */}
      {uploadMutation.isError && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-red-900/20 p-3 text-sm text-red-400">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span>{uploadMutation.error.message}</span>
          <button
            onClick={() => {
              uploadMutation.reset();
              setSelectedFile(null);
            }}
            className="ml-auto"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Success */}
      {uploadMutation.isSuccess && uploadMutation.data && (
        <div className="mt-3 rounded-lg bg-green-900/20 p-3 text-sm text-green-400">
          <p>Instrumental analisado com sucesso:</p>
          <div className="mt-1 flex flex-wrap gap-3 text-xs">
            <span>{uploadMutation.data.bpm} BPM</span>
            <span>{uploadMutation.data.musical_key}</span>
            <span>
              {Math.floor(uploadMutation.data.duration_seconds / 60)}:
              {Math.floor(uploadMutation.data.duration_seconds % 60)
                .toString()
                .padStart(2, "0")}
            </span>
            <span>{uploadMutation.data.sample_rate} Hz</span>
          </div>
        </div>
      )}
    </div>
  );
}
