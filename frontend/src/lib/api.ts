/**
 * Cliente API para comunicação com o backend FastAPI.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: string;
  current_step: string | null;
  instrumental_filename: string | null;
  audio_format: string | null;
  duration_seconds: number | null;
  sample_rate: number | null;
  bpm: number | null;
  musical_key: string | null;
  lyrics: string | null;
  language: string | null;
  synthesis_engine: string | null;
  voice_model: string | null;
  progress: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface AudioAnalysis {
  duration_seconds: number;
  sample_rate: number;
  bpm: number;
  musical_key: string;
  audio_format: string;
  waveform_peaks: number[];
}

export interface ProjectListResponse {
  projects: Project[];
  total: number;
}

export interface MelodyNote {
  start_time: number;
  end_time: number;
  duration: number;
  midi_note: number;
  note_name: string;
  velocity: number;
  lyric: string;
}

export interface MelodyData {
  notes: MelodyNote[];
  bpm: number;
  time_signature: number[];
  total_notes: number;
}

export interface SynthesisParams {
  engine: "diffsinger" | "acestep";
  voicebank: string;
  language?: string;
  breathiness?: number;
  tension?: number;
  energy?: number;
  voicing?: number;
  pitch_deviation?: number;
  gender?: number;
  guidance_scale?: number;
  num_inference_steps?: number;
  seed?: number;
  preview_seconds?: number;
}

export interface SynthesisResponse {
  status: string;
  engine: string;
  output_file: string;
  duration_seconds: number | null;
  download_url: string;
}

export interface VariationsResponse {
  project_id: string;
  engine: string;
  variations: { index: number; file: string; download_url: string }[];
  total: number;
}

export interface SyllabifyResponse {
  syllables: string[];
  lines: string[][];
  total: number;
  assigned_to_melody: boolean;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        error: "Erro desconhecido",
        detail: response.statusText,
      }));
      throw new Error(error.detail || error.error || "Erro na requisição");
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // Projetos
  async createProject(data: {
    name: string;
    description?: string;
    language?: string;
    synthesis_engine?: string;
    template_id?: string;
  }): Promise<Project> {
    return this.request("/api/projects", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async listProjects(): Promise<ProjectListResponse> {
    return this.request("/api/projects");
  }

  async getProject(id: string): Promise<Project> {
    return this.request(`/api/projects/${id}`);
  }

  async updateProject(
    id: string,
    data: Partial<Project>
  ): Promise<Project> {
    return this.request(`/api/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteProject(id: string): Promise<void> {
    return this.request(`/api/projects/${id}`, { method: "DELETE" });
  }

  async duplicateProject(id: string): Promise<Project> {
    return this.request(`/api/projects/${id}/duplicate`, { method: "POST" });
  }

  // Upload de áudio
  async uploadInstrumental(
    projectId: string,
    file: File
  ): Promise<AudioAnalysis> {
    const formData = new FormData();
    formData.append("file", file);

    const url = `${this.baseUrl}/api/audio/${projectId}/upload`;
    const response = await fetch(url, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: "Erro no upload",
      }));
      throw new Error(error.detail);
    }

    return response.json();
  }

  // Waveform
  async getWaveform(
    projectId: string
  ): Promise<{ peaks: number[]; duration: number }> {
    return this.request(`/api/audio/${projectId}/waveform`);
  }

  // Pipeline
  async startPipeline(projectId: string): Promise<Project> {
    return this.request(`/api/pipeline/${projectId}/start`, {
      method: "POST",
    });
  }

  async getPipelineStatus(projectId: string): Promise<Record<string, unknown>> {
    return this.request(`/api/pipeline/${projectId}/status`);
  }

  // Voices
  async listVoices(): Promise<Record<string, unknown>> {
    return this.request("/api/voices");
  }

  async listEngines(): Promise<Record<string, unknown>> {
    return this.request("/api/voices/engines");
  }

  // Melody
  async extractMelody(projectId: string): Promise<MelodyData> {
    return this.request(`/api/melody/${projectId}/extract`, {
      method: "POST",
    });
  }

  async importMidi(projectId: string, file: File): Promise<MelodyData> {
    const formData = new FormData();
    formData.append("file", file);

    const url = `${this.baseUrl}/api/melody/${projectId}/import`;
    const response = await fetch(url, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: "Erro na importação MIDI",
      }));
      throw new Error(error.detail);
    }

    return response.json();
  }

  async getMelody(projectId: string): Promise<MelodyData> {
    return this.request(`/api/melody/${projectId}`);
  }

  async updateMelody(
    projectId: string,
    data: MelodyData
  ): Promise<MelodyData> {
    return this.request(`/api/melody/${projectId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async snapMelodyToGrid(
    projectId: string,
    gridResolution: number = 0.125
  ): Promise<MelodyData> {
    return this.request(
      `/api/melody/${projectId}/snap-to-grid?grid_resolution=${gridResolution}`,
      { method: "POST" }
    );
  }

  async syllabifyLyrics(projectId: string): Promise<SyllabifyResponse> {
    return this.request(`/api/melody/${projectId}/syllabify`, {
      method: "POST",
    });
  }

  // Synthesis
  async renderVocal(
    projectId: string,
    params: SynthesisParams
  ): Promise<SynthesisResponse> {
    return this.request(`/api/synthesis/${projectId}/render`, {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async previewVocal(
    projectId: string,
    params: SynthesisParams
  ): Promise<SynthesisResponse> {
    return this.request(`/api/synthesis/${projectId}/preview`, {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async generateVariations(
    projectId: string,
    params: SynthesisParams,
    count: number = 3
  ): Promise<VariationsResponse> {
    return this.request(
      `/api/synthesis/${projectId}/variations?count=${count}`,
      {
        method: "POST",
        body: JSON.stringify(params),
      }
    );
  }

  async getSynthesisStatus(
    projectId: string
  ): Promise<Record<string, unknown>> {
    return this.request(`/api/synthesis/${projectId}/status`);
  }

  // Refinement
  async refineVocal(
    projectId: string,
    params: {
      model_name: string;
      pitch_shift: number;
      index_rate: number;
      filter_radius: number;
      rms_mix_rate: number;
      protect: number;
      f0_method: string;
    }
  ): Promise<{ status: string; output_file: string; download_url: string }> {
    return this.request(`/api/refinement/${projectId}/convert`, {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async bypassRefinement(
    projectId: string
  ): Promise<{ status: string; output_file: string }> {
    return this.request(`/api/refinement/${projectId}/bypass`, {
      method: "POST",
    });
  }

  async getRefinementComparison(
    projectId: string
  ): Promise<{
    before: { file: string; download_url: string } | null;
    after: { file: string; download_url: string } | null;
  }> {
    return this.request(`/api/refinement/${projectId}/compare`);
  }

  async listRVCModels(
    projectId: string
  ): Promise<{ models: { name: string; has_index: boolean }[]; total: number }> {
    return this.request(`/api/refinement/${projectId}/models`);
  }

  // Mix
  async renderMix(
    projectId: string,
    params: {
      vocal_gain_db: number;
      instrumental_gain_db: number;
      eq_low_gain_db: number;
      eq_mid_gain_db: number;
      eq_high_gain_db: number;
      compressor_threshold_db: number;
      compressor_ratio: number;
      reverb_room_size: number;
      reverb_wet_level: number;
      limiter_threshold_db: number;
      preset: string | null;
    }
  ): Promise<{ status: string; output_file: string; download_url: string; preset: string | null }> {
    return this.request(`/api/mix/${projectId}/render`, {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async exportMix(
    projectId: string,
    format: string = "wav"
  ): Promise<{ status: string; format: string; output_file: string; download_url: string }> {
    return this.request(`/api/mix/${projectId}/export`, {
      method: "POST",
      body: JSON.stringify({ format }),
    });
  }

  async getMixStatus(
    projectId: string
  ): Promise<{
    has_vocal: boolean;
    has_instrumental: boolean;
    has_mix: boolean;
    exports: { file: string; format: string; download_url: string }[];
  }> {
    return this.request(`/api/mix/${projectId}/status`);
  }

  async getMixPresets(
    projectId: string
  ): Promise<{ presets: { name: string; params: Record<string, number> }[] }> {
    return this.request(`/api/mix/${projectId}/presets`);
  }

  // System
  async healthCheck(): Promise<Record<string, string>> {
    return this.request("/api/health");
  }

  async testEngine(
    engine: string
  ): Promise<{ engine: string; available: boolean }> {
    return this.request(`/api/voices/engines/${engine}/test`, {
      method: "POST",
    });
  }

  // Templates
  async listTemplates(): Promise<{
    templates: {
      id: string;
      name: string;
      description: string;
      language: string;
      synthesis_engine: string;
      mix_preset: string;
      icon: string;
    }[];
    total: number;
  }> {
    return this.request("/api/templates");
  }

  // Batch
  async batchStartPipeline(
    projectIds: string[]
  ): Promise<{ started: string[]; skipped: string[]; errors: { project_id: string; error: string }[] }> {
    return this.request("/api/batch/start", {
      method: "POST",
      body: JSON.stringify({ project_ids: projectIds }),
    });
  }

  async batchStatus(): Promise<{
    total: number;
    by_status: Record<string, number>;
    processing: { id: string; name: string; status: string; step: string | null; progress: number }[];
  }> {
    return this.request("/api/batch/status");
  }

  // Audio download URL
  getAudioUrl(projectId: string, filename: string): string {
    return `${this.baseUrl}/api/audio/${projectId}/${filename}`;
  }
}

export const api = new ApiClient();
