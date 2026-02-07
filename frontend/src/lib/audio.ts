/**
 * Utilitários de áudio para o frontend.
 */

/**
 * Formata duração em segundos para mm:ss.
 */
export function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

/**
 * Formata tamanho de arquivo em bytes para representação legível.
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Valida se o arquivo é um formato de áudio suportado.
 */
export function isValidAudioFile(file: File): boolean {
  const validTypes = [
    "audio/wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/flac",
    "audio/ogg",
    "audio/x-m4a",
    "audio/mp4",
  ];
  const validExtensions = ["wav", "mp3", "flac", "ogg", "m4a"];
  const extension = file.name.split(".").pop()?.toLowerCase() || "";
  return validTypes.includes(file.type) || validExtensions.includes(extension);
}

/**
 * Retorna o nome legível da tonalidade musical.
 */
export function formatMusicalKey(key: string): string {
  return key;
}

/**
 * Mapeamento de status para labels em português.
 */
export const STATUS_LABELS: Record<string, string> = {
  created: "Criado",
  uploading: "Enviando",
  analyzing: "Analisando",
  melody_ready: "Melodia pronta",
  synthesizing: "Sintetizando",
  refining: "Refinando",
  mixing: "Mixando",
  completed: "Concluído",
  error: "Erro",
};

/**
 * Mapeamento de steps do pipeline para labels.
 */
export const STEP_LABELS: Record<string, string> = {
  upload: "Upload",
  analysis: "Análise",
  melody: "Melodia",
  synthesis: "Síntese",
  refinement: "Refinamento",
  mix: "Mixagem",
};
