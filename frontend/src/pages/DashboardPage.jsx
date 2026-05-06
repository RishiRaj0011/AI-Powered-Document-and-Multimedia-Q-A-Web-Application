import { useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "react-query";
import { useNavigate } from "react-router-dom";
import { documentsAPI } from "../services/api";
import DocumentUpload from "../components/documents/DocumentUpload";
import DocumentList from "../components/documents/DocumentList";
import toast from "react-hot-toast";

const POLL_INTERVAL = 3000;

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const pollRef = useRef(null);

  const { data, isLoading, refetch } = useQuery(
    "documents",
    () => documentsAPI.list(),
    { refetchOnWindowFocus: false }
  );

  const documents = data?.documents ?? [];

  // Poll every 3 s while any document is still PROCESSING or PENDING
  useEffect(() => {
    const hasProcessing = documents.some(
      (d) => d.status === "processing" || d.status === "pending"
    );

    if (hasProcessing && !pollRef.current) {
      pollRef.current = setInterval(() => {
        refetch();
      }, POLL_INTERVAL);
    }

    if (!hasProcessing && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [documents, refetch]);

  const uploadMutation = useMutation(
    ({ file, onProgress }) => documentsAPI.upload(file, onProgress),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("documents");
        toast.success("File uploaded — processing started");
      },
      onError: (err) =>
        toast.error(err.response?.data?.detail || "Upload failed"),
    }
  );

  const deleteMutation = useMutation((id) => documentsAPI.delete(id), {
    onSuccess: () => {
      queryClient.invalidateQueries("documents");
      toast.success("Document deleted");
    },
    onError: () => toast.error("Delete failed"),
  });

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">My Documents</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Upload documents or media files, then ask questions about them
        </p>
      </div>

      <DocumentUpload
        onUpload={(file, onProgress) =>
          uploadMutation.mutate({ file, onProgress })
        }
        loading={uploadMutation.isLoading}
      />

      <DocumentList
        documents={documents}
        loading={isLoading}
        onOpen={(doc) => navigate(`/documents/${doc.id}`)}
        onDelete={(id) => {
          if (window.confirm("Delete this document?")) {
            deleteMutation.mutate(id);
          }
        }}
      />
    </div>
  );
}
