import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "react-query";
import { documentsAPI, chatAPI } from "../services/api";
import ChatMessage from "../components/chat/ChatMessage";
import ChatInput from "../components/chat/ChatInput";
import SessionList from "../components/chat/SessionList";
import MediaPlayer from "../components/MediaPlayer";
import SummaryPanel from "../components/SummaryPanel";
import TranscriptView from "../components/TranscriptView";
import {
  FileText,
  Music,
  Video,
  ArrowLeft,
  ChevronRight,
  ChevronLeft,
  MessageSquare,
  FileType,
} from "lucide-react";
import toast from "react-hot-toast";

const MEDIA_TYPES = new Set(["audio", "video"]);

function FileTypeIcon({ fileType, size = 20 }) {
  if (fileType === "audio") return <Music size={size} className="text-purple-500" />;
  if (fileType === "video") return <Video size={size} className="text-blue-500" />;
  return <FileText size={size} className="text-primary-500" />;
}

export default function ChatPage() {
  const { docId } = useParams();
  const navigate = useNavigate();
  const playerRef = useRef(null);
  const bottomRef = useRef(null);
  const eventSourceRef = useRef(null);

  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [summaryData, setSummaryData] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [activeTab, setActiveTab] = useState("chat");
  const [searchAllDocs, setSearchAllDocs] = useState(false);
  const [transcript, setTranscript] = useState(null);

  // Fetch document metadata
  const { data: doc, isLoading: docLoading } = useQuery(
    ["document", docId],
    () => documentsAPI.get(docId),
    { enabled: !!docId, retry: false }
  );

  const isMedia = doc && MEDIA_TYPES.has(doc.file_type);

  // Load sessions for this document on mount
  useEffect(() => {
    if (!docId) return;
    chatAPI.getSessions().then((all) => {
      const forDoc = all.filter((s) => String(s.document_id) === String(docId));
      setSessions(forDoc);
    }).catch(() => {});
  }, [docId]);

  // Load messages when session changes
  useEffect(() => {
    if (!currentSessionId) return;
    chatAPI.getSession(currentSessionId).then((s) => {
      setMessages(s.messages ?? []);
    }).catch(() => {});
  }, [currentSessionId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamBuffer]);

  // Cleanup SSE on unmount
  useEffect(() => () => eventSourceRef.current?.close(), []);

  // Load transcript for media files
  useEffect(() => {
    if (!isMedia || !docId) return;
    documentsAPI.getTranscript(docId)
      .then(setTranscript)
      .catch(() => {});
  }, [isMedia, docId]);

  // ------------------------------------------------------------------
  // Ensure a session exists before sending
  // ------------------------------------------------------------------
  const ensureSession = useCallback(async () => {
    if (currentSessionId) return currentSessionId;
    const session = await chatAPI.createSession(Number(docId));
    setSessions((prev) => [session, ...prev]);
    setCurrentSessionId(session.id);
    return session.id;
  }, [currentSessionId, docId]);

  // ------------------------------------------------------------------
  // Send message via SSE streaming
  // ------------------------------------------------------------------
  const handleSend = useCallback(async (question) => {
    if (streaming) return;

    // Optimistically add user message
    setMessages((prev) => [...prev, { role: "user", content: question }]);

    let sessionId;
    try {
      sessionId = await ensureSession();
    } catch {
      toast.error("Could not create chat session");
      return;
    }

    setStreaming(true);
    setStreamBuffer("");

    // Close any existing SSE connection
    eventSourceRef.current?.close();

    const url = chatAPI.getStreamUrl(sessionId, question, searchAllDocs);
    // Attach auth header via fetch + ReadableStream (EventSource doesn't support headers)
    const accessToken = localStorage.getItem("access_token");

    try {
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      if (!response.ok) {
        throw new Error(`Stream error: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6);
          if (payload === "[DONE]") {
            // Commit the streamed message
            setMessages((prev) => [
              ...prev,
              { role: "assistant", content: accumulated, sources: [], timestamp_references: [] },
            ]);
            setStreamBuffer("");
            setStreaming(false);
            return;
          }
          if (payload.startsWith("[ERROR]")) {
            toast.error(payload.replace("[ERROR]", "").trim() || "Stream error");
            setStreaming(false);
            setStreamBuffer("");
            return;
          }
          // Unescape newlines encoded by the server
          const decodedToken = payload.replace(/\\n/g, "\n");
          accumulated += decodedToken;
          setStreamBuffer(accumulated);
        }
      }
    } catch (err) {
      toast.error("Streaming failed — " + (err.message || "unknown error"));
    } finally {
      setStreaming(false);
      setStreamBuffer("");
    }
  }, [streaming, ensureSession]);

  // ------------------------------------------------------------------
  // Load summary on first open
  // ------------------------------------------------------------------
  const handleSummaryToggle = async () => {
    setSummaryOpen((o) => !o);
    if (!summaryData && !summaryLoading) {
      setSummaryLoading(true);
      try {
        const data = await documentsAPI.getSummary(docId);
        setSummaryData(data);
      } catch {
        toast.error("Could not load summary");
      } finally {
        setSummaryLoading(false);
      }
    }
  };

  // ------------------------------------------------------------------
  // Select session from sidebar
  // ------------------------------------------------------------------
  const handleSelectSession = (id) => {
    setCurrentSessionId(id);
    setStreamBuffer("");
  };

  const handleNewSession = async () => {
    try {
      const session = await chatAPI.createSession(Number(docId));
      setSessions((prev) => [session, ...prev]);
      setCurrentSessionId(session.id);
      setMessages([]);
    } catch {
      toast.error("Could not create session");
    }
  };

  if (docLoading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        Loading document…
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <p className="text-gray-500">Document not found</p>
        <button className="btn-primary" onClick={() => navigate("/dashboard")}>
          Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-0px)] overflow-hidden">
      {/* ---------------------------------------------------------------- */}
      {/* Session sidebar                                                   */}
      {/* ---------------------------------------------------------------- */}
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col shrink-0">
        <div className="p-3 border-b border-gray-200">
          <button
            onClick={() => navigate("/dashboard")}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-800 mb-3 transition-colors"
          >
            <ArrowLeft size={14} /> Dashboard
          </button>
          <button
            onClick={handleNewSession}
            className="btn-primary w-full text-sm py-1.5"
          >
            + New Chat
          </button>
        </div>
        <SessionList
          sessions={sessions}
          currentId={currentSessionId}
          onSelect={handleSelectSession}
          onNew={handleNewSession}
          hideNewButton
        />
      </aside>

      {/* ---------------------------------------------------------------- */}
      {/* Main chat area                                                    */}
      {/* ---------------------------------------------------------------- */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Document info bar */}
        <div className="flex items-center gap-3 px-4 py-3 bg-white border-b border-gray-200 shrink-0">
          <FileTypeIcon fileType={doc.file_type} />
          <div className="flex-1 min-w-0">
            <p className="font-medium text-gray-900 truncate text-sm">
              {doc.filename}
            </p>
            <p className="text-xs text-gray-400 capitalize">
              {doc.file_type} · {doc.status}
            </p>
          </div>
          {isMedia && (
            <div className="flex gap-2 shrink-0">
              <button
                onClick={() => setActiveTab("chat")}
                className={`px-3 py-1 text-xs rounded transition-colors ${
                  activeTab === "chat"
                    ? "bg-primary-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                <MessageSquare size={12} className="inline mr-1" />
                Chat
              </button>
              <button
                onClick={() => setActiveTab("transcript")}
                className={`px-3 py-1 text-xs rounded transition-colors ${
                  activeTab === "transcript"
                    ? "bg-primary-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                <FileType size={12} className="inline mr-1" />
                Transcript
              </button>
            </div>
          )}
          <button
            onClick={handleSummaryToggle}
            className="text-xs text-primary-600 hover:underline shrink-0"
          >
            {summaryOpen ? "Hide summary" : "Show summary"}
          </button>
        </div>

        {/* Summary panel */}
        {summaryOpen && (
          <div className="px-4 pt-3 shrink-0">
            {summaryLoading ? (
              <div className="text-sm text-gray-400 py-2">Loading summary…</div>
            ) : (
              <SummaryPanel
                summary={summaryData?.summary}
                topics={summaryData?.topics ?? []}
                playerRef={playerRef}
              />
            )}
          </div>
        )}

        {/* Content area - Chat or Transcript */}
        {activeTab === "chat" ? (
          <>
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
              {messages.length === 0 && !streaming && (
                <div className="text-center text-gray-400 mt-20">
                  <FileTypeIcon fileType={doc.file_type} size={40} />
                  <p className="mt-3 text-base font-medium text-gray-500">
                    Ask anything about this {doc.file_type}
                  </p>
                  <p className="text-sm text-gray-400 mt-1">
                    {doc.status === "ready"
                      ? "Document is ready — start chatting"
                      : "Document is still processing…"}
                  </p>
                  <label className="inline-flex items-center gap-2 mt-4 text-xs text-gray-600 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={searchAllDocs}
                      onChange={(e) => setSearchAllDocs(e.target.checked)}
                      className="rounded"
                    />
                    Search across all my documents
                  </label>
                </div>
              )}

              {messages.map((msg, i) => (
                <ChatMessage key={i} message={msg} playerRef={playerRef} />
              ))}

              {streaming && streamBuffer && (
                <ChatMessage
                  message={{ role: "assistant", content: streamBuffer }}
                  playerRef={playerRef}
                  isStreaming
                />
              )}

              {streaming && !streamBuffer && (
                <div className="flex items-center gap-2 text-gray-400 text-sm">
                  <span className="inline-flex gap-1">
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
                  </span>
                  Thinking…
                </div>
              )}

              <div ref={bottomRef} />
            </div>

            <div className="px-4 pb-2 shrink-0">
              <label className="inline-flex items-center gap-2 text-xs text-gray-600 cursor-pointer mb-2">
                <input
                  type="checkbox"
                  checked={searchAllDocs}
                  onChange={(e) => setSearchAllDocs(e.target.checked)}
                  className="rounded"
                />
                Search across all my documents
              </label>
            </div>

            <ChatInput
              onSend={handleSend}
              disabled={streaming || doc.status !== "ready"}
              placeholder={
                doc.status !== "ready"
                  ? "Document is processing…"
                  : "Ask a question…"
              }
            />
          </>
        ) : (
          <TranscriptView
            transcriptSegments={transcript?.chunks}
            playerRef={playerRef}
          />
        )}
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* Right panel — MediaPlayer (audio/video only)                     */}
      {/* ---------------------------------------------------------------- */}
      {isMedia && (
        <div
          className={`shrink-0 bg-gray-900 border-l border-gray-700 flex flex-col transition-all duration-200 ${
            rightPanelOpen ? "w-80" : "w-10"
          }`}
        >
          <button
            onClick={() => setRightPanelOpen((o) => !o)}
            className="flex items-center justify-center h-10 text-gray-400 hover:text-white transition-colors border-b border-gray-700"
            title={rightPanelOpen ? "Collapse player" : "Expand player"}
          >
            {rightPanelOpen ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>

          {rightPanelOpen && (
            <div className="p-3 flex-1 overflow-y-auto">
              <p className="text-xs text-gray-400 mb-3 uppercase tracking-wide">
                Media Player
              </p>
              <MediaPlayer
                ref={playerRef}
                src={`/api/v1/documents/${docId}/file`}
                type={doc.file_type}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
