import { Play } from "lucide-react";

export default function TranscriptView({ transcriptSegments, playerRef }) {
  if (!transcriptSegments || transcriptSegments.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 text-sm">
        No transcript available for this document.
      </div>
    );
  }

  const handleSeek = (startTime) => {
    if (!playerRef?.current) return;
    playerRef.current.currentTime = startTime;
    playerRef.current.play().catch(() => {});
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="px-4 py-3 border-b font-semibold text-gray-700 text-sm shrink-0">
        Full Transcript
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {transcriptSegments.map((segment, index) => (
          <div
            key={index}
            className="group flex gap-3 p-3 hover:bg-blue-50 rounded-lg cursor-pointer transition-colors"
            onClick={() => handleSeek(segment.start_time)}
          >
            <span className="text-blue-600 font-mono text-xs whitespace-nowrap shrink-0 mt-0.5">
              {formatTime(segment.start_time)}
            </span>
            <p className="text-gray-800 text-sm leading-relaxed flex-1">
              {segment.text_content}
            </p>
            <button className="opacity-0 group-hover:opacity-100 text-blue-500 shrink-0 transition-opacity">
              <Play size={14} fill="currentColor" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
