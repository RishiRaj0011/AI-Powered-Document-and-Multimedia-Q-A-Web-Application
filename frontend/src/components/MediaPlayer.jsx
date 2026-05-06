import { useRef, useState, useImperativeHandle, forwardRef } from "react";
import { Play, Pause, Volume2, VolumeX } from "lucide-react";

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

const SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2];

const MediaPlayer = forwardRef(function MediaPlayer({ src, type = "audio" }, ref) {
  const mediaRef = useRef(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [volume, setVolume] = useState(1);

  useImperativeHandle(ref, () => ({
    seekTo(seconds) {
      if (mediaRef.current) {
        mediaRef.current.currentTime = seconds;
        mediaRef.current.play();
        setPlaying(true);
      }
    },
  }));

  const togglePlay = () => {
    if (!mediaRef.current) return;
    if (playing) {
      mediaRef.current.pause();
    } else {
      mediaRef.current.play();
    }
    setPlaying(!playing);
  };

  const toggleMute = () => {
    if (!mediaRef.current) return;
    mediaRef.current.muted = !muted;
    setMuted(!muted);
  };

  const handleSeek = (e) => {
    const t = Number(e.target.value);
    if (mediaRef.current) mediaRef.current.currentTime = t;
    setCurrentTime(t);
  };

  const handleVolume = (e) => {
    const v = Number(e.target.value);
    if (mediaRef.current) mediaRef.current.volume = v;
    setVolume(v);
    setMuted(v === 0);
  };

  const handleSpeed = (e) => {
    const s = Number(e.target.value);
    if (mediaRef.current) mediaRef.current.playbackRate = s;
    setSpeed(s);
  };

  const MediaTag = type === "video" ? "video" : "audio";

  return (
    <div className="bg-gray-900 rounded-xl p-4 space-y-3">
      {type === "video" && (
        <MediaTag
          ref={mediaRef}
          src={src}
          className="w-full rounded-lg max-h-64 bg-black"
          onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}
          onLoadedMetadata={(e) => setDuration(e.target.duration)}
          onEnded={() => setPlaying(false)}
        />
      )}
      {type === "audio" && (
        <MediaTag
          ref={mediaRef}
          src={src}
          onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}
          onLoadedMetadata={(e) => setDuration(e.target.duration)}
          onEnded={() => setPlaying(false)}
        />
      )}

      {/* Seekbar */}
      <input
        type="range"
        min={0}
        max={duration || 0}
        step={0.1}
        value={currentTime}
        onChange={handleSeek}
        className="w-full h-1.5 accent-primary-500 cursor-pointer"
      />

      <div className="flex items-center gap-3">
        {/* Play / Pause */}
        <button
          onClick={togglePlay}
          className="text-white hover:text-primary-400 transition-colors"
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? <Pause size={22} /> : <Play size={22} />}
        </button>

        {/* Time */}
        <span className="text-xs text-gray-400 tabular-nums w-24 shrink-0">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>

        {/* Volume */}
        <button onClick={toggleMute} className="text-gray-400 hover:text-white transition-colors">
          {muted || volume === 0 ? <VolumeX size={18} /> : <Volume2 size={18} />}
        </button>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={muted ? 0 : volume}
          onChange={handleVolume}
          className="w-20 h-1.5 accent-primary-500 cursor-pointer"
          aria-label="Volume"
        />

        {/* Speed */}
        <select
          value={speed}
          onChange={handleSpeed}
          className="ml-auto bg-gray-800 text-gray-300 text-xs rounded px-1.5 py-1 border border-gray-700 cursor-pointer"
          aria-label="Playback speed"
        >
          {SPEEDS.map((s) => (
            <option key={s} value={s}>{s}×</option>
          ))}
        </select>
      </div>
    </div>
  );
});

export default MediaPlayer;
