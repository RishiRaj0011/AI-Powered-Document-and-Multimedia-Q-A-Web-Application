import { usePlayer } from "../contexts/PlayerContext";

function formatTimestamp(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function TimestampBadge({ startTime, label }) {
  const playerRef = usePlayer();

  const handleClick = () => {
    playerRef?.current?.seekTo(startTime);
  };

  return (
    <button
      onClick={handleClick}
      title={`Jump to ${formatTimestamp(startTime)}`}
      className="inline-flex items-center gap-1 bg-primary-100 hover:bg-primary-200 text-primary-700 text-xs font-mono font-medium px-2 py-0.5 rounded-full transition-colors cursor-pointer"
    >
      ▶ [{formatTimestamp(startTime)}]
      {label && <span className="font-sans font-normal ml-1">{label}</span>}
    </button>
  );
}
