"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { MelodyNote, MelodyData } from "@/lib/api";

interface PianoRollProps {
  melody: MelodyData;
  duration: number;
  onNotesChange: (notes: MelodyNote[]) => void;
}

// Piano roll constants
const NOTE_HEIGHT = 12;
const MIN_MIDI = 36; // C2
const MAX_MIDI = 84; // C6
const TOTAL_NOTES = MAX_MIDI - MIN_MIDI;
const PIANO_KEY_WIDTH = 48;
const PIXELS_PER_SECOND = 80;
const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

function isBlackKey(midi: number): boolean {
  const note = midi % 12;
  return [1, 3, 6, 8, 10].includes(note);
}

function midiToName(midi: number): string {
  const octave = Math.floor(midi / 12) - 1;
  return `${NOTE_NAMES[midi % 12]}${octave}`;
}

type DragMode = "move" | "resize-end" | null;

export default function PianoRoll({
  melody,
  duration,
  onNotesChange,
}: PianoRollProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedNote, setSelectedNote] = useState<number | null>(null);
  const [dragMode, setDragMode] = useState<DragMode>(null);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [scrollX, setScrollX] = useState(0);

  const canvasWidth = Math.max(duration * PIXELS_PER_SECOND + PIANO_KEY_WIDTH + 100, 800);
  const canvasHeight = TOTAL_NOTES * NOTE_HEIGHT;

  // Time-to-pixel conversion
  const timeToX = useCallback(
    (time: number) => PIANO_KEY_WIDTH + time * PIXELS_PER_SECOND - scrollX,
    [scrollX]
  );
  const xToTime = useCallback(
    (x: number) => (x + scrollX - PIANO_KEY_WIDTH) / PIXELS_PER_SECOND,
    [scrollX]
  );
  const midiToY = (midi: number) => (MAX_MIDI - midi) * NOTE_HEIGHT;
  const yToMidi = (y: number) => MAX_MIDI - Math.floor(y / NOTE_HEIGHT);

  // Draw the piano roll
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    // Clear
    ctx.fillStyle = "#111827";
    ctx.fillRect(0, 0, width, height);

    // Draw piano key rows
    for (let midi = MIN_MIDI; midi <= MAX_MIDI; midi++) {
      const y = midiToY(midi);
      const black = isBlackKey(midi);

      // Row background
      ctx.fillStyle = black ? "#0f172a" : "#1e293b";
      ctx.fillRect(PIANO_KEY_WIDTH, y, width - PIANO_KEY_WIDTH, NOTE_HEIGHT);

      // Row border
      ctx.strokeStyle = "#334155";
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(PIANO_KEY_WIDTH, y + NOTE_HEIGHT);
      ctx.lineTo(width, y + NOTE_HEIGHT);
      ctx.stroke();

      // Piano keys
      ctx.fillStyle = black ? "#1e293b" : "#e2e8f0";
      ctx.fillRect(0, y, PIANO_KEY_WIDTH - 2, NOTE_HEIGHT);
      ctx.strokeStyle = "#475569";
      ctx.strokeRect(0, y, PIANO_KEY_WIDTH - 2, NOTE_HEIGHT);

      // Key labels (only C notes)
      if (midi % 12 === 0) {
        ctx.fillStyle = black ? "#94a3b8" : "#334155";
        ctx.font = "9px monospace";
        ctx.fillText(midiToName(midi), 4, y + NOTE_HEIGHT - 2);
      }
    }

    // Draw beat grid lines
    if (melody.bpm > 0) {
      const beatDuration = 60 / melody.bpm;
      for (let beat = 0; beat * beatDuration < duration; beat++) {
        const x = timeToX(beat * beatDuration);
        if (x < PIANO_KEY_WIDTH) continue;

        ctx.strokeStyle = beat % 4 === 0 ? "#475569" : "#1e293b";
        ctx.lineWidth = beat % 4 === 0 ? 1 : 0.5;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();

        // Beat numbers on bar lines
        if (beat % 4 === 0) {
          ctx.fillStyle = "#64748b";
          ctx.font = "10px monospace";
          ctx.fillText(`${Math.floor(beat / 4) + 1}`, x + 2, 10);
        }
      }
    }

    // Draw notes
    melody.notes.forEach((note, index) => {
      const x = timeToX(note.start_time);
      const y = midiToY(note.midi_note);
      const w = (note.end_time - note.start_time) * PIXELS_PER_SECOND;

      const isSelected = index === selectedNote;

      // Note body
      ctx.fillStyle = isSelected ? "#818cf8" : "#4c6ef5";
      ctx.beginPath();
      ctx.roundRect(x, y + 1, Math.max(w, 4), NOTE_HEIGHT - 2, 2);
      ctx.fill();

      // Note border
      ctx.strokeStyle = isSelected ? "#c7d2fe" : "#748ffc";
      ctx.lineWidth = isSelected ? 2 : 1;
      ctx.beginPath();
      ctx.roundRect(x, y + 1, Math.max(w, 4), NOTE_HEIGHT - 2, 2);
      ctx.stroke();

      // Resize handle
      if (w > 10) {
        ctx.fillStyle = isSelected ? "#e0e7ff" : "#91a7ff";
        ctx.fillRect(x + w - 4, y + 3, 3, NOTE_HEIGHT - 6);
      }

      // Lyric text
      if (note.lyric && w > 20) {
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 9px sans-serif";
        ctx.fillText(note.lyric, x + 3, y + NOTE_HEIGHT - 3, w - 8);
      }
    });
  }, [melody, duration, selectedNote, timeToX, scrollX]);

  // Redraw on changes
  useEffect(() => {
    draw();
  }, [draw]);

  // Handle canvas resize
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.width = containerRef.current?.clientWidth || 800;
    canvas.height = canvasHeight;
    draw();
  }, [canvasHeight, draw]);

  // Find note at position
  const findNoteAt = useCallback(
    (x: number, y: number): { index: number; resize: boolean } | null => {
      for (let i = melody.notes.length - 1; i >= 0; i--) {
        const note = melody.notes[i];
        const nx = timeToX(note.start_time);
        const ny = midiToY(note.midi_note);
        const nw = (note.end_time - note.start_time) * PIXELS_PER_SECOND;

        if (x >= nx && x <= nx + nw && y >= ny && y <= ny + NOTE_HEIGHT) {
          const resize = x >= nx + nw - 6;
          return { index: i, resize };
        }
      }
      return null;
    },
    [melody.notes, timeToX]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      if (x < PIANO_KEY_WIDTH) return;

      const hit = findNoteAt(x, y);

      if (hit) {
        setSelectedNote(hit.index);
        setDragMode(hit.resize ? "resize-end" : "move");
        setDragStart({ x, y });
      } else {
        // Create new note on double-click handled separately
        setSelectedNote(null);
        setDragMode(null);
      }
    },
    [findNoteAt]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (dragMode === null || selectedNote === null || !dragStart) return;

      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const dx = x - dragStart.x;
      const dy = y - dragStart.y;

      const notes = [...melody.notes];
      const note = { ...notes[selectedNote] };

      if (dragMode === "move") {
        const timeDelta = dx / PIXELS_PER_SECOND;
        const noteDelta = -Math.round(dy / NOTE_HEIGHT);

        const dur = note.end_time - note.start_time;
        note.start_time = Math.max(0, melody.notes[selectedNote].start_time + timeDelta);
        note.end_time = note.start_time + dur;
        note.midi_note = Math.max(
          MIN_MIDI,
          Math.min(MAX_MIDI, melody.notes[selectedNote].midi_note + noteDelta)
        );
      } else if (dragMode === "resize-end") {
        const timeDelta = dx / PIXELS_PER_SECOND;
        note.end_time = Math.max(
          note.start_time + 0.05,
          melody.notes[selectedNote].end_time + timeDelta
        );
      }

      note.duration = note.end_time - note.start_time;
      note.note_name = midiToName(note.midi_note);
      notes[selectedNote] = note;
      onNotesChange(notes);
    },
    [dragMode, selectedNote, dragStart, melody.notes, onNotesChange]
  );

  const handleMouseUp = useCallback(() => {
    setDragMode(null);
    setDragStart(null);
  }, []);

  // Double-click to create new note
  const handleDoubleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      if (x < PIANO_KEY_WIDTH) return;

      const time = xToTime(x);
      const midi = yToMidi(y);

      if (midi < MIN_MIDI || midi > MAX_MIDI) return;

      const beatDuration = melody.bpm > 0 ? 60 / melody.bpm : 0.5;

      const newNote: MelodyNote = {
        start_time: Math.max(0, time),
        end_time: Math.max(0, time) + beatDuration / 2,
        duration: beatDuration / 2,
        midi_note: midi,
        note_name: midiToName(midi),
        velocity: 100,
        lyric: "",
      };

      onNotesChange([...melody.notes, newNote].sort((a, b) => a.start_time - b.start_time));
    },
    [melody.notes, melody.bpm, onNotesChange, xToTime]
  );

  // Delete selected note
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.key === "Delete" || e.key === "Backspace") && selectedNote !== null) {
        const notes = melody.notes.filter((_, i) => i !== selectedNote);
        onNotesChange(notes);
        setSelectedNote(null);
      }
    },
    [selectedNote, melody.notes, onNotesChange]
  );

  // Scroll
  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (e.shiftKey) {
      setScrollX((prev) => Math.max(0, prev + e.deltaY));
    }
  }, []);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span>Duplo-clique para criar nota</span>
        <span>|</span>
        <span>Delete para remover</span>
        <span>|</span>
        <span>Arrastar para mover/redimensionar</span>
        <span>|</span>
        <span>Shift+scroll para navegar</span>
      </div>
      <div
        ref={containerRef}
        className="overflow-x-auto overflow-y-auto rounded-lg border border-gray-700"
        style={{ maxHeight: "400px" }}
      >
        <canvas
          ref={canvasRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onDoubleClick={handleDoubleClick}
          onKeyDown={handleKeyDown}
          onWheel={handleWheel}
          tabIndex={0}
          className="cursor-crosshair outline-none"
          style={{
            width: `${canvasWidth}px`,
            height: `${canvasHeight}px`,
          }}
        />
      </div>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{melody.notes.length} notas</span>
        <span>{melody.bpm} BPM</span>
      </div>
    </div>
  );
}
