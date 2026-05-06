import { MessageSquare, Plus } from "lucide-react";

export default function SessionList({
  sessions,
  currentId,
  onSelect,
  onNew,
  hideNewButton = false,
}) {
  return (
    <div className="flex-1 overflow-y-auto">
      {!hideNewButton && (
        <div className="p-3 border-b border-gray-200">
          <button
            onClick={onNew}
            className="btn-primary w-full flex items-center justify-center gap-2 text-sm py-1.5"
          >
            <Plus size={15} /> New Chat
          </button>
        </div>
      )}

      <div className="p-2 space-y-0.5">
        {sessions.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4 px-2">
            No sessions yet
          </p>
        )}
        {sessions.map((s) => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={`w-full text-left px-3 py-2 rounded-lg text-xs flex items-center gap-2 transition-colors ${
              s.id === currentId
                ? "bg-primary-50 text-primary-700 font-medium"
                : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            <MessageSquare size={13} className="shrink-0" />
            <span className="truncate">
              {s.title || `Session ${s.id}`}
            </span>
            {s.message_count > 0 && (
              <span className="ml-auto text-gray-400 shrink-0">
                {s.message_count}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
