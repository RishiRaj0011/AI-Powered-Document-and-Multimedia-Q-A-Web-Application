import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  Music,
  Video,
  Trash2,
  Loader,
  CheckCircle,
  XCircle,
  Clock,
  MessageSquare,
} from "lucide-react";
import ConfirmDialog from "../ui/ConfirmDialog";

function FileIcon({ fileType }) {
  if (fileType === "audio") return <Music size={22} className="text-purple-500 shrink-0" />;
  if (fileType === "video") return <Video size={22} className="text-blue-500 shrink-0" />;
  return <FileText size={22} className="text-primary-500 shrink-0" />;
}

function StatusBadge({ status, errorMessage }) {
  if (status === "processing") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-yellow-700 bg-yellow-100 px-2.5 py-1 rounded-full">
        <Loader size={11} className="animate-spin" />
        Processing
      </span>
    );
  }
  if (status === "ready") {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs font-medium text-green-700 bg-green-100 px-2.5 py-1 rounded-full">
        <CheckCircle size={11} />
        Ready
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span
        className="inline-flex items-center gap-1.5 text-xs font-medium text-red-700 bg-red-100 px-2.5 py-1 rounded-full cursor-help"
        title={errorMessage || "Processing failed"}
      >
        <XCircle size={11} />
        Failed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-600 bg-gray-100 px-2.5 py-1 rounded-full">
      <Clock size={11} />
      Pending
    </span>
  );
}

function formatSize(bytes) {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function DocumentList({ documents, loading, onOpen, onDelete }) {
  const navigate = useNavigate();
  const [confirmDialog, setConfirmDialog] = useState({ isOpen: false, docId: null, docName: "" });

  const handleDeleteClick = (e, doc) => {
    e.stopPropagation();
    setConfirmDialog({
      isOpen: true,
      docId: doc.id,
      docName: doc.filename
    });
  };

  const handleConfirmDelete = () => {
    if (confirmDialog.docId) {
      onDelete(confirmDialog.docId);
    }
  };

  const handleCloseDialog = () => {
    setConfirmDialog({ isOpen: false, docId: null, docName: "" });
  };

  if (loading) {
    return (
      <div className="text-center py-12 text-gray-400">
        <Loader className="animate-spin mx-auto mb-2" size={24} />
        <p className="text-sm">Loading documents…</p>
      </div>
    );
  }

  if (!documents.length) {
    return (
      <div className="text-center py-12 text-gray-400">
        <FileText size={40} className="mx-auto mb-3 opacity-40" />
        <p className="font-medium text-gray-500">No documents yet</p>
        <p className="text-sm mt-1">Upload a file above to get started</p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-3">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="card flex items-center gap-4 cursor-pointer hover:shadow-md transition-shadow"
            onClick={() => navigate(`/documents/${doc.id}`)}
          >
            <FileIcon fileType={doc.file_type} />

            <div className="flex-1 min-w-0">
              <p className="font-medium text-gray-900 truncate text-sm">
                {doc.filename}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                {formatSize(doc.file_size)} · {doc.file_type?.toUpperCase()} ·{" "}
                {formatDate(doc.created_at)}
              </p>
            </div>

            <StatusBadge status={doc.status} errorMessage={doc.error_message} />

            {/* Chat button — only when ready */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                navigate(`/documents/${doc.id}`);
              }}
              disabled={doc.status !== "ready"}
              className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg disabled:opacity-30 transition-colors"
              title="Open chat"
            >
              <MessageSquare size={17} />
            </button>

            {/* Delete button */}
            <button
              onClick={(e) => handleDeleteClick(e, doc)}
              className="p-2 text-red-400 hover:bg-red-50 hover:text-red-600 rounded-lg transition-colors"
              title="Delete document"
            >
              <Trash2 size={17} />
            </button>
          </div>
        ))}
      </div>

      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        onClose={handleCloseDialog}
        onConfirm={handleConfirmDelete}
        title="Delete Document"
        message={`Are you sure you want to delete "${confirmDialog.docName}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
      />
    </>
  );
}
