import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, CheckCircle, XCircle, File, Loader } from "lucide-react";

const ACCEPTED = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/plain": [".txt"],
  "audio/mpeg": [".mp3"],
  "audio/wav": [".wav"],
  "audio/x-m4a": [".m4a"],
  "audio/mp4": [".m4a"],
  "audio/webm": [".webm"],
  "video/mp4": [".mp4"],
  "video/webm": [".webm"],
};

const MAX_SIZE_MB = 50;
const MAX_FILES = 10;

export default function DocumentUpload({ onUpload, onUploadMultiple, loading }) {
  const [progress, setProgress] = useState({});
  const [uploadingFiles, setUploadingFiles] = useState([]);
  const [rejected, setRejected] = useState([]);
  const [done, setDone] = useState(false);

  const onDrop = useCallback(
    async (accepted, rejectedFiles) => {
      setRejected(rejectedFiles);
      setDone(false);
      
      if (!accepted.length) return;
      
      // Multi-file upload
      if (accepted.length > 1 && onUploadMultiple) {
        setUploadingFiles(accepted.map(f => f.name));
        setProgress({});
        
        try {
          await onUploadMultiple(accepted);
          setDone(true);
          setTimeout(() => {
            setDone(false);
            setUploadingFiles([]);
            setProgress({});
          }, 2500);
        } catch (error) {
          setUploadingFiles([]);
          setProgress({});
        }
      } 
      // Single file upload
      else {
        const file = accepted[0];
        setUploadingFiles([file.name]);
        setProgress({ [file.name]: 0 });
        
        onUpload(file, (pct) => {
          setProgress({ [file.name]: pct });
        });
      }
    },
    [onUpload, onUploadMultiple]
  );

  // When loading transitions to false, show success briefly
  if (!loading && uploadingFiles.length > 0 && !done) {
    const allComplete = Object.values(progress).every(p => p === 100) || Object.keys(progress).length === 0;
    if (allComplete) {
      setDone(true);
      setTimeout(() => {
        setDone(false);
        setProgress({});
        setUploadingFiles([]);
      }, 2500);
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: MAX_FILES,
    maxSize: MAX_SIZE_MB * 1024 * 1024,
    disabled: loading,
    multiple: true,
  });

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors select-none ${
          isDragActive
            ? "border-primary-500 bg-primary-50"
            : done
            ? "border-green-400 bg-green-50"
            : "border-gray-300 hover:border-primary-400 bg-white"
        } ${loading ? "opacity-60 cursor-not-allowed" : ""}`}
      >
        <input {...getInputProps()} />

        {done ? (
          <>
            <CheckCircle className="mx-auto mb-3 text-green-500" size={36} />
            <p className="text-green-700 font-medium text-sm">
              {uploadingFiles.length} file{uploadingFiles.length > 1 ? "s" : ""} uploaded!
            </p>
          </>
        ) : loading ? (
          <>
            <Loader className="mx-auto mb-3 text-primary-400 animate-spin" size={36} />
            <p className="text-gray-600 font-medium text-sm">
              Uploading {uploadingFiles.length} file{uploadingFiles.length > 1 ? "s" : ""}…
            </p>
            {Object.entries(progress).map(([filename, pct]) => (
              <div key={filename} className="mt-2">
                <p className="text-xs text-gray-500 mb-1">{filename}</p>
                <div className="mx-auto w-48 bg-gray-200 rounded-full h-1.5">
                  <div
                    className="bg-primary-500 h-1.5 rounded-full transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            ))}
          </>
        ) : (
          <>
            <Upload className="mx-auto mb-3 text-gray-400" size={36} />
            <p className="text-gray-700 font-medium">
              {isDragActive ? "Drop files here" : "Drag & drop or click to upload"}
            </p>
            <p className="text-xs text-gray-400 mt-2">
              PDF, DOCX, TXT, MP3, WAV, M4A, WEBM, MP4 · Max {MAX_SIZE_MB} MB per file
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Select multiple files (up to {MAX_FILES}) for batch upload
            </p>
          </>
        )}
      </div>

      {/* Rejected file errors */}
      {rejected.length > 0 && (
        <div className="space-y-1">
          {rejected.map(({ file, errors: errs }, i) => (
            <div
              key={i}
              className="flex items-start gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700"
            >
              <XCircle size={16} className="shrink-0 mt-0.5" />
              <span>
                <span className="font-medium">{file.name}</span>:{" "}
                {errs.map((e) => e.message).join(", ")}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
