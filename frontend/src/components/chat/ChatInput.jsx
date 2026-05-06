import { useState, useRef } from "react";
import { Send } from "lucide-react";

const MAX_CHARS = 2000;

export default function ChatInput({ onSend, disabled, placeholder = "Ask a question…" }) {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    // Reset textarea height
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleChange = (e) => {
    setValue(e.target.value.slice(0, MAX_CHARS));
    // Auto-grow
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const remaining = MAX_CHARS - value.length;

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">
      <div className="flex items-end gap-3">
        <textarea
          ref={textareaRef}
          className="input-field flex-1 resize-none min-h-[42px] max-h-40 leading-relaxed"
          placeholder={placeholder}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
        />
        <button
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="btn-primary flex items-center justify-center w-10 h-10 p-0 shrink-0"
          aria-label="Send"
        >
          <Send size={16} />
        </button>
      </div>
      <div className="flex justify-between mt-1 px-0.5">
        <p className="text-xs text-gray-400">Shift+Enter for new line</p>
        {remaining < 200 && (
          <p className={`text-xs ${remaining < 50 ? "text-red-500" : "text-gray-400"}`}>
            {remaining} left
          </p>
        )}
      </div>
    </div>
  );
}
