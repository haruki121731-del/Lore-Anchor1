"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import type { ImageRecord, ImageStatus, TaskStatus } from "@/lib/api/types";
import {
  deleteImage,
  getTaskStatus,
  listImages,
  retryTask,
  trackDownload,
} from "@/lib/api/images";
import { normalizeUiError, type UiError } from "@/lib/errors/ui";
import { withAccessTokenRetry } from "@/lib/supabase/client";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

function StatusBadge({ status }: { status: ImageStatus }) {
  const classes: Record<ImageStatus, string> = {
    pending: "bg-amber-400/15 text-amber-200 border border-amber-300/30",
    processing: "bg-cyan-400/15 text-cyan-200 border border-cyan-300/30",
    completed: "bg-emerald-400/15 text-emerald-200 border border-emerald-300/30",
    failed: "bg-rose-400/15 text-rose-200 border border-rose-300/30",
  };

  const labels: Record<ImageStatus, string> = {
    pending: "pending",
    processing: "processing",
    completed: "completed",
    failed: "failed",
  };

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${classes[status]}`}>
      {labels[status]}
    </span>
  );
}

function extractFilename(url: string): string {
  const parts = url.split("/");
  return parts[parts.length - 1] || url;
}

function statusProgress(status: ImageStatus): number {
  if (status === "pending") return 20;
  if (status === "processing") return 65;
  return 100;
}

function summarizeError(errorLog?: string | null): string {
  if (!errorLog) return "保護処理に失敗しました。再試行してください。";
  const compact = errorLog.replace(/\s+/g, " ");
  if (compact.includes("Watermark destroyed")) {
    return "透かし検証に失敗しました。別の解像度・形式で再試行してください。";
  }
  if (compact.includes("FileNotFoundError") || compact.includes("NoSuchKey")) {
    return "原本画像が取得できませんでした。再アップロードまたは再試行してください。";
  }
  return "処理に失敗しました。再試行してください。";
}

interface ImageListProps {
  refreshKey: number;
}

const PAGE_SIZE = 20;

export function ImageList({ refreshKey }: ImageListProps) {
  const [images, setImages] = useState<ImageRecord[]>([]);
  const [taskStatusMap, setTaskStatusMap] = useState<Record<string, TaskStatus>>({});
  const [error, setError] = useState<UiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const fetchTaskStatuses = useCallback(async (records: ImageRecord[]) => {
    const targetIds = records
      .filter((img) => img.status === "failed" || img.status === "pending" || img.status === "processing")
      .map((img) => img.image_id);

    if (targetIds.length === 0) {
      if (mountedRef.current) setTaskStatusMap({});
      return;
    }

    const pairs = await Promise.all(
      targetIds.map(async (imageId) => {
        try {
          const status = await withAccessTokenRetry((accessToken) =>
            getTaskStatus(imageId, accessToken)
          );
          return [imageId, status] as const;
        } catch (fetchError) {
          console.error("[ImageList] task status fetch failed", fetchError);
          return [imageId, null] as const;
        }
      })
    );

    if (!mountedRef.current) return;

    const next: Record<string, TaskStatus> = {};
    for (const [imageId, status] of pairs) {
      if (status) next[imageId] = status;
    }
    setTaskStatusMap(next);
  }, []);

  const fetchImages = useCallback(async (targetPage: number = page) => {
    try {
      const data = await withAccessTokenRetry((accessToken) =>
        listImages(accessToken, targetPage, PAGE_SIZE)
      );
      if (mountedRef.current) {
        setImages(data.images);
        setHasMore(data.has_more);
        setTotal(data.total);
        setError(null);
      }
      await fetchTaskStatuses(data.images);
    } catch (err) {
      if (mountedRef.current) {
        const uiError = normalizeUiError(err, "dashboard");
        setError(uiError);
        console.error("[ImageList] list fetch failed", err);
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [fetchTaskStatuses, page]);

  const handleDelete = useCallback(async (imageId: string) => {
    try {
      setDeletingId(imageId);
      await withAccessTokenRetry((accessToken) => deleteImage(imageId, accessToken));
      setImages((prev) => prev.filter((img) => img.image_id !== imageId));
      setTotal((prev) => Math.max(prev - 1, 0));
      setTaskStatusMap((prev) => {
        const next = { ...prev };
        delete next[imageId];
        return next;
      });
    } catch (err) {
      const uiError = normalizeUiError(err, "dashboard");
      setError(uiError);
      console.error("[ImageList] delete failed", err);
    } finally {
      setDeletingId(null);
    }
  }, []);

  const handleRetry = useCallback(async (imageId: string) => {
    try {
      setRetryingId(imageId);
      await withAccessTokenRetry((accessToken) => retryTask(imageId, accessToken));
      setError(null);
      await fetchImages(page);
    } catch (err) {
      const uiError = normalizeUiError(err, "dashboard");
      setError(uiError);
      console.error("[ImageList] retry failed", err);
    } finally {
      setRetryingId(null);
    }
  }, [fetchImages, page]);

  const handleDownload = useCallback(async (img: ImageRecord) => {
    if (!img.protected_url) return;

    try {
      setDownloadingId(img.image_id);
      const tracked = await withAccessTokenRetry((accessToken) =>
        trackDownload(img.image_id, accessToken)
      );
      setImages((prev) =>
        prev.map((item) =>
          item.image_id === img.image_id
            ? { ...item, download_count: tracked.download_count }
            : item
        )
      );
    } catch (err) {
      const uiError = normalizeUiError(err, "dashboard");
      setError(uiError);
      console.error("[ImageList] download track failed", err);
    } finally {
      const a = document.createElement("a");
      a.href = img.protected_url;
      a.download = extractFilename(img.original_url);
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.click();
      setDownloadingId(null);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    void fetchImages(page);
  }, [fetchImages, refreshKey, page]);

  useEffect(() => {
    const hasInFlight = images.some((img) => img.status === "pending" || img.status === "processing");
    if (!hasInFlight) return;

    const interval = setInterval(() => {
      void fetchImages(page);
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchImages, images, page]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  if (loading && images.length === 0) {
    return (
      <div className="space-y-3 pt-4">
        <Card className="border-white/10 bg-slate-950/50"><CardContent className="h-20 animate-pulse" /></Card>
        <Card className="border-white/10 bg-slate-950/50"><CardContent className="h-20 animate-pulse" /></Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-8 text-center">
        <div className="rounded-lg border border-rose-300/30 bg-rose-500/10 p-3 text-sm text-rose-200">
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
        <Button
          variant="outline"
          size="sm"
          className="mt-3"
          onClick={() => {
            setError(null);
            setLoading(true);
            void fetchImages(page);
          }}
        >
          再読み込み
        </Button>
      </div>
    );
  }

  if (images.length === 0) {
    return (
      <Card className="mt-4 border-white/10 bg-slate-950/30">
        <CardContent className="py-10 text-center text-sm text-slate-300">
          まだ画像がありません。最初の1枚をアップロードして保護処理を開始してください。
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3 pt-4">
      {images.map((img) => {
        const taskStatus = taskStatusMap[img.image_id];
        const showProgress = img.status === "pending" || img.status === "processing";

        return (
          <Card key={img.image_id} className="border-white/10 bg-slate-950/40">
            <CardContent className="space-y-3 py-4">
              <div className="flex items-start gap-4">
                {img.status === "completed" && img.protected_url ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={img.protected_url}
                    alt={extractFilename(img.original_url)}
                    className="h-16 w-16 rounded-md object-cover ring-1 ring-white/10"
                  />
                ) : (
                  <div className="flex h-16 w-16 items-center justify-center rounded-md bg-slate-800 text-slate-300">
                    <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M4 16l4.586-4.586a2 2 0 0 1 2.828 0L16 16m-2-2 1.586-1.586a2 2 0 0 1 2.828 0L20 14m-6-6h.01M6 20h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2z"
                      />
                    </svg>
                  </div>
                )}

                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-white">{extractFilename(img.original_url)}</p>
                  <p className="text-xs text-slate-300/80">{new Date(img.created_at).toLocaleString()}</p>
                  {img.status === "failed" && (
                    <p className="mt-2 rounded-md border border-rose-300/20 bg-rose-500/10 px-2 py-1 text-xs text-rose-100">
                      {summarizeError(taskStatus?.error_log)}
                    </p>
                  )}
                </div>

                <StatusBadge status={img.status} />
              </div>

              {showProgress && (
                <div className="space-y-1">
                  <Progress value={statusProgress(img.status)} />
                  <p className="text-xs text-slate-300">
                    {img.status === "pending"
                      ? "キュー待機中です。まもなく処理が開始されます。"
                      : "保護処理中です。通常30秒〜数分で完了します。"}
                  </p>
                </div>
              )}

              <div className="flex flex-wrap items-center gap-2">
                {img.status === "completed" && img.protected_url && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={downloadingId === img.image_id}
                      onClick={() => void handleDownload(img)}
                    >
                      {downloadingId === img.image_id ? "記録中..." : "ダウンロード"}
                    </Button>
                    <span className="text-xs text-slate-300/80">download: {img.download_count ?? 0}</span>
                  </>
                )}

                {img.status === "failed" && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={retryingId === img.image_id}
                    onClick={() => void handleRetry(img.image_id)}
                  >
                    {retryingId === img.image_id ? "再投入中..." : "Retry"}
                  </Button>
                )}

                <Button
                  variant="ghost"
                  size="sm"
                  disabled={deletingId === img.image_id}
                  onClick={() => void handleDelete(img.image_id)}
                  className="text-rose-300 hover:bg-rose-500/15 hover:text-rose-100"
                >
                  {deletingId === img.image_id ? "削除中..." : "削除"}
                </Button>
              </div>
            </CardContent>
          </Card>
        );
      })}

      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between pt-4">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            前へ
          </Button>
          <span className="text-sm text-slate-300">
            Page {page} / {Math.ceil(total / PAGE_SIZE)}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={!hasMore}
            onClick={() => setPage((p) => p + 1)}
          >
            次へ
          </Button>
        </div>
      )}
    </div>
  );
}
