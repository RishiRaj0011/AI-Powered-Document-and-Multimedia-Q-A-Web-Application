import { useState } from "react";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import TimestampBadge from "./TimestampBadge";

export default function SummaryPanel({ summary, topics = [], playerRef }) {
  const [open, setOpen] = useState(true);

  if (!summary && topics.length === 0) return null;

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-sm font-medium text-gray-700"
      >
        <span className="flex items-center gap-2">
          <FileText size={16} className="text-primary-500" />
          Document Summary
        </span>
        {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {open && (
        <div className="p-4 space-y-4 bg-white">
          {/* Summary text */}
          {summary && (
            <p className="text-sm text-gray-600 leading-relaxed">{summary}</p>
          )}

          {/* Topics */}
          {topics.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Key Topics
              </h4>
              <ul className="space-y-2">
                {topics.map((topic, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="mt-0.5 text-primary-400">•</span>
                    <span className="flex-1">{topic.label}</span>
                    {topic.start_time != null && (
                      <TimestampBadge
                        startTime={topic.start_time}
                        playerRef={playerRef}
                      />
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
