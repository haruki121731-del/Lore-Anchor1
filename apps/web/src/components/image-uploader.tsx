"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { useDropzone } from "react-dropzone";
import { uploadImage } from "@/lib/api/images";
import type { UploadResponse } from "@/lib/api/types";
import { normalizeUiError, type UiError } from "@/lib/errors/ui";
import { withAccessTokenRetry } from "@/lib/supabase/client";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface ImageUploaderProps {
  onUploadComplete: (result: UploadResponse) => void;
}

export function ImageUploader({ onUploadComplete }: ImageUploaderProps) {
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<UiError | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      setError(null);
      setResult(null);
      setProgress(0);
      setSelectedFileName(file.name);

      try {
        const uploadResult = await withAccessTokenRetry((accessToken) =>
          uploadImage(file, accessToken, setProgress)
        );
        setResult(uploadResult);
        onUploadComplete(uploadResult);
      } catch (err) {
        const uiError = normalizeUiError(err, "upload");
        setError(uiError);
        console.error("[ImageUploader] upload failed", err);
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
      <div className="rounded-xl border border-cyan-400/30 bg-cyan-500/10 p-4 text-sm text-cyan-950 dark:text-cyan-100">
        <p className="font-semibold">アップロード条件</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          <li>対応形式: PNG / JPEG / WebP</li>
          <li>最大サイズ: 20MB</li>
          <li>推奨解像度: 1024px 以上</li>
        </ul>
      </div>

      <Card
        {...getRootProps()}
        className={`cursor-pointer border-2 border-dashed bg-slate-950/40 transition-colors ${
          isDragActive
            ? "border-cyan-300 bg-cyan-400/10"
            : "border-slate-600 hover:border-cyan-300/60"
        }`}
      >
        <CardContent className="flex flex-col items-center justify-center py-12">
          <input {...getInputProps()} />
          <svg
            className="mb-4 h-10 w-10 text-cyan-200/80"
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
            <p className="text-sm text-cyan-200">ここに画像をドロップしてください</p>
          ) : (
            <p className="text-sm text-slate-300">画像をドラッグ＆ドロップ、またはクリックで選択</p>
          )}
          {selectedFileName && (
            <p className="mt-3 text-xs text-slate-300/80">選択中: {selectedFileName}</p>
          )}
        </CardContent>
      </Card>

      {progress !== null && (
        <div className="space-y-2">
          <Progress value={progress} />
          <p className="text-center text-sm text-slate-300">
            アップロード中... {progress}%
          </p>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-rose-300/30 bg-rose-500/10 p-3 text-center text-sm text-rose-200">
          <p>{error.message}</p>
          {error.category === "auth" && (
            <Link className="mt-2 inline-block text-xs underline" href="/login?next=/dashboard">
              ログイン画面へ
            </Link>
          )}
          {error.detail && (
            <details className="mt-2 text-left text-xs text-rose-100/80">
              <summary className="cursor-pointer text-center">くわしい情報</summary>
              <p className="mt-1 break-words">{error.detail}</p>
            </details>
          )}
        </div>
      )}

      {result && (
        <Card className="border-emerald-300/30 bg-emerald-500/10">
          <CardContent className="py-4">
            <p className="text-sm text-emerald-100">
              <span className="font-medium">受付ID:</span> {result.image_id}
            </p>
            <p className="text-sm text-emerald-100">
              <span className="font-medium">現在状態:</span> {result.status}
            </p>
            <p className="mt-2 text-xs text-emerald-100/80">
              保護処理はバックグラウンドで継続中です。ジョブ状況カードで進捗を確認してください。
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
