import { FileUp, Plus } from "lucide-react";
import React from "react";

type Props = {
  files: File[];
  onFiles: (files: File[]) => void;
  onInvalidFile?: (message: string) => void;
};

export function UploadDropzone({ files, onFiles, onInvalidFile }: Props) {
  const handleFiles = (fileList: FileList | null) => {
    const nextFiles = Array.from(fileList ?? []);
    if (nextFiles.length === 0) return;
    const invalidFile = nextFiles.find((next) => {
      return next.type !== "application/pdf" && !next.name.toLowerCase().endsWith(".pdf");
    });
    if (invalidFile) {
      onInvalidFile?.(`Only PDF exam papers are accepted. ${invalidFile.name} was not added.`);
      return;
    }
    onFiles(nextFiles);
  };

  return (
    <label
      className="dropzone"
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        handleFiles(event.dataTransfer.files);
      }}
    >
      <input
        type="file"
        accept="application/pdf"
        multiple
        onChange={(event) => handleFiles(event.target.files)}
      />
      <div className="plus-mark">
        <Plus size={88} strokeWidth={1.6} />
      </div>
      <div className="drop-title">Drop exam paper PDFs</div>
      <div className="drop-subtitle">
        {files.length > 0 ? `${files.length} PDF${files.length === 1 ? "" : "s"} selected` : "Only PDF exam papers are accepted"}
      </div>
      {files.length > 0 ? (
        <ul className="selected-files" aria-label="Selected files">
          {files.map((nextFile) => (
            <li key={`${nextFile.name}-${nextFile.size}`}>{nextFile.name}</li>
          ))}
        </ul>
      ) : null}
      <div className="drop-icon">
        <FileUp size={22} />
      </div>
    </label>
  );
}
