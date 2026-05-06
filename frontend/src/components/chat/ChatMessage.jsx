import Markdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import TimestampBadge from "../TimestampBadge";
import { Bot } from "lucide-react";

export default function ChatMessage({ message, playerRef, isStreaming = false }) {
  const isUser = message.role === "user";
  const tsRefs = message.timestamp_references ?? [];
  const sources = message.sources ?? [];

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-primary-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start gap-2.5">
      {/* Avatar */}
      <div className="shrink-0 w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center mt-1">
        <Bot size={14} className="text-gray-600" />
      </div>

      <div className="max-w-[80%] space-y-2">
        {/* Message bubble */}
        <div
          className={`bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-800 leading-relaxed ${
            isStreaming ? "border-primary-200" : ""
          }`}
        >
          <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0">
            <Markdown rehypePlugins={[rehypeSanitize]}>
              {message.content}
            </Markdown>
          </div>
          {isStreaming && (
            <span className="inline-block w-1.5 h-4 bg-primary-500 animate-pulse ml-0.5 align-middle" />
          )}
        </div>

        {/* Timestamp references */}
        {tsRefs.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {tsRefs.map((ref, i) => (
              <TimestampBadge
                key={i}
                startTime={ref.start_time}
                label={ref.text ? ref.text.slice(0, 40) : undefined}
              />
            ))}
          </div>
        )}

        {/* Source citations */}
        {sources.length > 0 && (
          <details className="px-1">
            <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600 select-none">
              {sources.length} source{sources.length > 1 ? "s" : ""}
            </summary>
            <ul className="mt-1.5 space-y-1">
              {sources.map((s, i) => (
                <li
                  key={i}
                  className="text-xs text-gray-500 bg-gray-50 border border-gray-100 rounded-lg px-3 py-2 line-clamp-2"
                >
                  <span className="font-medium text-gray-600">[{i + 1}]</span>{" "}
                  {s.text}
                  {s.score != null && (
                    <span className="ml-1 text-gray-400">
                      ({(s.score * 100).toFixed(0)}%)
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  );
}
