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

  // Audio download URL
  getAudioUrl(projectId: string, filename: string): string {
    return `${this.baseUrl}/api/audio/${projectId}/${filename}`;
  }
}

export const api = new ApiClient();
