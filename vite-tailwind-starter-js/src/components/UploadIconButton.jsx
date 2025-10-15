import { useRef, useState } from "react";

export default function UploadIconButton({ onFileText }) {
  const inputRef = useRef(null);
  const [fileName, setFileName] = useState("");

  async function handleFiles(files) {
    if (!files || !files.length) return;
    const file = files[0];
    setFileName(file.name);
    const text = await file.text();
    onFileText(text);
  }

  return (
    <div className="flex items-center gap-3 ml-2">
      {/* Upload icon button first */}
      <button
        className="p-2 rounded-xl border border-slate-700 bg-slate-900 hover:bg-slate-800"
        title="Upload .cir"
        onClick={() => inputRef.current?.click()}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          className="text-slate-200"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="1.8"
            d="M12 16V4m0 0l-4 4m4-4l4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2"
          />
        </svg>
      </button>

      {/* Filename now on the right */}
      {fileName && (
        <span
          className="text-xs text-slate-400 truncate max-w-[16rem]"
          title={fileName}
        >
          {fileName}
        </span>
      )}

      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        accept=".cir,.sp,.spi,.spice,.txt"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}
