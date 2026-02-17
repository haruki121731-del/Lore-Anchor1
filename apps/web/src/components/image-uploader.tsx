"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { getSupabaseClient } from "@/lib/supabase/client";
import { uploadImage } from "@/lib/api/images";
import type { UploadResponse } from "@/lib/api/types";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface ImageUploaderProps {
  onUploadComplete: (result: UploadResponse) => void;
}

export function ImageUploader({ onUploadComplete }: ImageUploaderProps) {
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      setError(null);
      setResult(null);
      setProgress(0);

      try {
        const supabase = getSupabaseClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (!session) {
          setError("Not authenticated");
          setProgress(null);
          return;
        }

        const uploadResult = await uploadImage(
          file,
          session.access_token,
          setProgress
        );
        setResult(uploadResult);
        onUploadComplete(uploadResult);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setProgress(null);
      }
    },
    [onUploadComplete]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [".png", ".jpg", ".jpeg", ".webp"] },
    maxFiles: 1,
    multiple: false,
  });

  return (
    <div className="space-y-4">
      <Card
        {...getRootProps()}
        className={`cursor-pointer border-2 border-dashed transition-colors ${
          isDragActive
            ? "border-primary bg-primary/5"
            : "border-zinc-300 hover:border-zinc-400 dark:border-zinc-700"
        }`}
      >
        <CardContent className="flex flex-col items-center justify-center py-12">
          <input {...getInputProps()} />
          <svg
            className="mb-4 h-10 w-10 text-zinc-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 0 1-.88-7.903A5 5 0 1 1 15.9 6h.1a5 5 0 0 1 1 9.9M15 13l-3-3m0 0-3 3m3-3v12"
            />
          </svg>
          {isDragActive ? (
            <p className="text-sm text-primary">Drop the image here...</p>
          ) : (
            <p className="text-sm text-zinc-500">
              Drag & drop an image, or click to select
            </p>
          )}
        </CardContent>
      </Card>

      {progress !== null && (
        <div className="space-y-2">
          <Progress value={progress} />
          <p className="text-center text-sm text-zinc-500">
            Uploading... {progress}%
          </p>
        </div>
      )}

      {error && (
        <p className="text-center text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}

      {result && (
        <Card>
          <CardContent className="py-4">
            <p className="text-sm">
              <span className="font-medium">Image ID:</span> {result.image_id}
            </p>
            <p className="text-sm">
              <span className="font-medium">Status:</span> {result.status}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
