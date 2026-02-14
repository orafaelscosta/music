"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Play, Square, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

// Singleton: apenas um áudio toca por vez
let currentAudio: HTMLAudioElement | null = null;
let currentStopCallback: (() => void) | null = null;

interface VoicePreviewButtonProps {
  presetId: string;
  size?: "sm" | "md";
}

export default function VoicePreviewButton({
  presetId,
  size = "sm",
}: VoicePreviewButtonProps) {
  const [state, setState] = useState<"idle" | "loading" | "playing">("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.oncanplaythrough = null;
      audioRef.current.onended = null;
      audioRef.current.onerror = null;
      audioRef.current.currentTime = 0;
    }
    setState("idle");
  }, []);

  // Cleanup ao desmontar
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (currentStopCallback === stop) {
        currentStopCallback = null;
        currentAudio = null;
      }
    };
  }, [stop]);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();

    if (state === "playing" || state === "loading") {
      stop();
      if (currentAudio === audioRef.current) {
        currentAudio = null;
        currentStopCallback = null;
      }
      return;
    }

    // Parar qualquer outro preview tocando
    if (currentStopCallback) {
      currentStopCallback();
    }

    const url = api.getVoicePreviewUrl(presetId);

    if (!audioRef.current) {
      audioRef.current = new Audio();
    }

    const audio = audioRef.current;
    audio.src = url;

    currentAudio = audio;
    currentStopCallback = stop;

    setState("loading");

    audio.onended = () => {
      setState("idle");
      currentAudio = null;
      currentStopCallback = null;
    };

    audio.onerror = () => {
      setState("idle");
      currentAudio = null;
      currentStopCallback = null;
    };

    audio.load();
    audio.play()
      .then(() => setState("playing"))
      .catch(() => {
        setState("idle");
        currentAudio = null;
        currentStopCallback = null;
      });
  };

  const sizeClasses = size === "sm" ? "h-6 w-6" : "h-8 w-8";
  const iconSize = size === "sm" ? "h-3 w-3" : "h-4 w-4";

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`flex items-center justify-center rounded-full transition-all ${sizeClasses} ${
        state === "playing"
          ? "bg-brand-500 text-white shadow-md shadow-brand-500/30"
          : state === "loading"
            ? "bg-gray-700 text-gray-300"
            : "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white"
      }`}
      title={state === "playing" ? "Parar preview" : "Ouvir preview"}
    >
      {state === "loading" ? (
        <Loader2 className={`${iconSize} animate-spin`} />
      ) : state === "playing" ? (
        <Square className={iconSize} />
      ) : (
        <Play className={`${iconSize} ml-[1px]`} />
      )}
    </button>
  );
}
