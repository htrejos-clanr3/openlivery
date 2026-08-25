"use client";

import {
  DragEvent,
  ReactNode,
  forwardRef,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { firstMatchingFile } from "@/lib/file-drop";

export type FileDropzoneHandle = { open: () => void };

type FileDropzoneProps = {
  onFile: (file: File) => void;
  accept?: string;
  disabled?: boolean;
  multiple?: boolean;
  className?: string;
  children: ReactNode;
  /** When true, clicking the zone opens the file picker (default true). */
  clickable?: boolean;
};

export const FileDropzone = forwardRef<FileDropzoneHandle, FileDropzoneProps>(function FileDropzone(
  { onFile, accept, disabled = false, multiple = false, className = "", children, clickable = true },
  ref,
) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  useImperativeHandle(ref, () => ({
    open: () => {
      if (!disabled) inputRef.current?.click();
    },
  }));

  function pick(files: FileList | null | undefined) {
    if (disabled) return;
    const file = firstMatchingFile(files, accept);
    if (file) onFile(file);
  }

  function onDragEnter(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    if (!disabled) setDragging(true);
  }

  function onDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    if (!disabled) setDragging(true);
  }

  function onDragLeave(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    if (event.currentTarget.contains(event.relatedTarget as Node | null)) return;
    setDragging(false);
  }

  function onDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    setDragging(false);
    pick(event.dataTransfer.files);
  }

  function openPicker() {
    if (clickable && !disabled) inputRef.current?.click();
  }

  return (
    <>
      <div
        className={`file-dropzone ${dragging ? "dragging" : ""} ${className}`.trim()}
        onClick={openPicker}
        onDragEnter={onDragEnter}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        role={clickable ? "button" : undefined}
        tabIndex={clickable && !disabled ? 0 : undefined}
        onKeyDown={(event) => {
          if (!clickable || disabled) return;
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openPicker();
          }
        }}
        aria-disabled={disabled || undefined}
      >
        {children}
      </div>
      <input
        ref={inputRef}
        type="file"
        hidden
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        onChange={(event) => {
          pick(event.target.files);
          event.target.value = "";
        }}
      />
    </>
  );
});

type UseFileDropOptions = {
  onFile: (file: File) => void;
  accept?: string;
  disabled?: boolean;
};

export function useFileDrop({ onFile, accept, disabled = false }: UseFileDropOptions) {
  const [dragging, setDragging] = useState(false);

  function pick(files: FileList | null | undefined) {
    if (disabled) return;
    const file = firstMatchingFile(files, accept);
    if (file) onFile(file);
  }

  function onDragEnter(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    if (!disabled) setDragging(true);
  }

  function onDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    if (!disabled) setDragging(true);
  }

  function onDragLeave(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    if (event.currentTarget.contains(event.relatedTarget as Node | null)) return;
    setDragging(false);
  }

  function onDrop(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    setDragging(false);
    pick(event.dataTransfer.files);
  }

  return {
    dragging,
    handlers: disabled
      ? {}
      : { onDragEnter, onDragOver, onDragLeave, onDrop },
  };
}
