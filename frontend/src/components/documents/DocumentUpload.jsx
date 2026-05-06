import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, CheckCircle, XCircle, File } from "lucide-react";

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

export default function DocumentUpload({ onUpload, loading }) {
  const [progress, setProgress] = useState(0);
  const [lastFile, setLastFile] = useState(null);
  const [rejected, setRejected] = useState([]);
  const [done, setDone] = useState(false);

  const onDrop = useCallback(
    (accepted, rejectedFiles) => {
      setRejected(rejectedFiles);
      setDone(false);
      if (!accepted.length) return;
      const file = accepted[0];
      setLastFile(file.name);
      setProgress(0);
      onUpload(file, (pct) => setProgress(pct));
      // Mark done after upload completes (parent sets loading=false)
    },
    [onUpload]
  );

  // When loading transitions false→true→false, show success briefly
  const prevLoading = loading;
  if (!loading && progress === 100 && lastFile && !done) {
    setDone(true);
    setTimeout(() => {
      setDone(false);
      setProgress(0);
      setLastFile(null);
    }, 2500);
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: 1,
    maxSize: MAX_SIZE_MB * 1024 * 1024,
    disabled: loading,
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
            <p className="text-green-700 font-medium text-sm">{lastFile} uploaded!</p>
          </>
        ) : loading ? (
          <>
            <File className="mx-auto mb-3 text-primary-400 animate-pulse" size={36} />
            <p className="text-gray-600 font-medium text-sm">Uploading {lastFile}…</p>
            {progress > 0 && (
              <div className="mt-3 mx-auto w-48 bg-gray-200 rounded-full h-1.5">
                <div
                  className="bg-primary-500 h-1.5 rounded-full transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            )}
          </>
        ) : (
          <>
            <Upload className="mx-auto mb-3 text-gray-400" size={36} />
            <p className="text-gray-700 font-medium">
              {isDragActive ? "Drop file here" : "Drag & drop or click to upload"}
            </p>
            <p className="text-xs text-gray-400 mt-2">
              PDF, DOCX, TXT, MP3, WAV, M4A, WEBM, MP4 · Max {MAX_SIZE_MB} MB
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
