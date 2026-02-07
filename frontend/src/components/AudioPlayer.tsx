"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { formatDuration } from "@/lib/audio";
import { Play, Pause, Volume2, VolumeX } from "lucide-react";

interface AudioPlayerProps {
  projectId: string;
  filename: string;
}

export default function AudioPlayer({ projectId, filename }: AudioPlayerProps) {
  const waveformRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const [isMuted, setIsMuted] = useState(false);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (!waveformRef.current) return;

    let ws: WaveSurfer;

    const initWavesurfer = async () => {
      const WaveSurfer = (await import("wavesurfer.js")).default;

      ws = WaveSurfer.create({
        container: waveformRef.current!,
        waveColor: "#4c6ef5",
        progressColor: "#748ffc",
        cursorColor: "#91a7ff",
        barWidth: 2,
        barGap: 1,
        barRadius: 2,
        height: 80,
        normalize: true,
        backend: "WebAudio",
      });

      const audioUrl = api.getAudioUrl(projectId, filename);
      ws.load(audioUrl);

      ws.on("ready", () => {
        setDuration(ws.getDuration());
        setIsReady(true);
        ws.setVolume(volume);
      });

      ws.on("audioprocess", () => {
        setCurrentTime(ws.getCurrentTime());
      });

      ws.on("seeking", () => {
        setCurrentTime(ws.getCurrentTime());
      });

      ws.on("play", () => setIsPlaying(true));
      ws.on("pause", () => setIsPlaying(false));
      ws.on("finish", () => setIsPlaying(false));

      wavesurferRef.current = ws;
    };

    initWavesurfer();

    return () => {
      ws?.destroy();
    };
  }, [projectId, filename]);

  const togglePlay = () => {
    wavesurferRef.current?.playPause();
  };

  const toggleMute = () => {
    if (isMuted) {
      wavesurferRef.current?.setVolume(volume);
      setIsMuted(false);
    } else {
      wavesurferRef.current?.setVolume(0);
      setIsMuted(true);
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    wavesurferRef.current?.setVolume(newVolume);
    if (newVolume > 0) setIsMuted(false);
  };

  return (
    <div className="space-y-3">
      {/* Waveform */}
      <div className="waveform-container p-2">
        <div ref={waveformRef} />
      </div>

      {/* Controls */}
      <div className="flex items-center gap-4">
        <button
          onClick={togglePlay}
          disabled={!isReady}
          className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-600 text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
        >
          {isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4 ml-0.5" />
          )}
        </button>

        {/* Time */}
        <span className="min-w-[100px] text-sm text-gray-400">
          {formatDuration(currentTime)} / {formatDuration(duration)}
        </span>

        {/* Volume */}
        <div className="flex items-center gap-2">
          <button onClick={toggleMute} className="text-gray-400 hover:text-white">
            {isMuted || volume === 0 ? (
              <VolumeX className="h-4 w-4" />
            ) : (
              <Volume2 className="h-4 w-4" />
            )}
          </button>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={isMuted ? 0 : volume}
            onChange={handleVolumeChange}
            className="h-1 w-20 cursor-pointer accent-brand-500"
          />
        </div>

        {/* Filename */}
        <span className="ml-auto text-xs text-gray-600">{filename}</span>
      </div>
    </div>
  );
}

// Type declaration for dynamic import
type WaveSurfer = import("wavesurfer.js").default;
