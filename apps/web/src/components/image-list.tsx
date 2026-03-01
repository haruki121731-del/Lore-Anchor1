"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { ImageRecord, ImageStatus } from "@/lib/api/types";
import { listImages, deleteImage } from "@/lib/api/images";
import { getSupabaseClient } from "@/lib/supabase/client";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

function StatusBadge({ status }: { status: ImageStatus }) {
  const colors: Record<ImageStatus, string> = {
    pending:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    processing:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    completed:
      "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[status]}`}
    >
      {status}
    </span>
  );
}

function extractFilename(url: string): string {
  const parts = url.split("/");
  return parts[parts.length - 1] || url;
}

interface ImageListProps {
  refreshKey: number;
}

const PAGE_SIZE = 20;

export function ImageList({ refreshKey }: ImageListProps) {
  const [images, setImages] = useState<ImageRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const fetchImages = useCallback(async (targetPage: number = page) => {
    try {
      const supabase = getSupabaseClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        if (mountedRef.current) setError("Not authenticated");
        return;
      }

      const data = await listImages(session.access_token, targetPage, PAGE_SIZE);
      if (mountedRef.current) {
        setImages(data.images);
        setHasMore(data.has_more);
        setTotal(data.total);
        setError(null);
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(
          err instanceof Error ? err.message : "Failed to load images"
        );
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [page]);

  const handleDelete = useCallback(async (imageId: string) => {
    try {
      setDeletingId(imageId);
      const supabase = getSupabaseClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) return;

      await deleteImage(imageId, session.access_token);
      setImages((prev) => prev.filter((img) => img.image_id !== imageId));
      setTotal((prev) => prev - 1);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to delete image"
      );
    } finally {
      setDeletingId(null);
    }
  }, []);

  // Initial fetch + refetch on refreshKey or page change
  useEffect(() => {
    setLoading(true);
    fetchImages(page);
  }, [fetchImages, refreshKey, page]);

  // Poll every 5 seconds, stop when all images are completed or failed
  useEffect(() => {
    const allSettled =
      images.length > 0 &&
      images.every((img) => img.status === "completed" || img.status === "failed");

    if (allSettled) return;

    const interval = setInterval(() => fetchImages(page), 5000);
    return () => clearInterval(interval);
  }, [fetchImages, images, page]);

  // Cleanup ref on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  if (loading && images.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-zinc-500">Loading...</p>
    );
  }

  if (error) {
    return (
      <div className="py-8 text-center">
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        <Button
          variant="outline"
          size="sm"
          className="mt-2"
          onClick={() => {
            setError(null);
            setLoading(true);
            fetchImages(page);
          }}
        >
          Retry
        </Button>
      </div>
    );
  }

  if (images.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-zinc-500">
        No images yet. Upload one above!
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {images.map((img) => (
        <Card key={img.image_id}>
          <CardContent className="flex items-center gap-4 py-4">
            {img.status === "completed" && img.protected_url ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={img.protected_url}
                alt={extractFilename(img.original_url)}
                className="h-16 w-16 rounded object-cover"
              />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded bg-zinc-100 dark:bg-zinc-800">
                <svg
                  className="h-6 w-6 text-zinc-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M4 16l4.586-4.586a2 2 0 0 1 2.828 0L16 16m-2-2 1.586-1.586a2 2 0 0 1 2.828 0L20 14m-6-6h.01M6 20h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2z"
                  />
                </svg>
              </div>
            )}

            <div className="flex-1 min-w-0">
              <p className="truncate text-sm font-medium">
                {extractFilename(img.original_url)}
              </p>
              <p className="text-xs text-zinc-500">
                {new Date(img.created_at).toLocaleString()}
              </p>
            </div>

            <StatusBadge status={img.status} />

            {img.status === "completed" && img.protected_url && (
              <>
                <Button variant="outline" size="sm" asChild>
                  <a
                    href={img.protected_url}
                    download={extractFilename(img.original_url)}
                  >
                    Download
                  </a>
                </Button>
                <a
                  href={`https://twitter.com/intent/tweet?text=${encodeURIComponent("この作品は #LoreAnchor で保護されています。AIによる無断学習から大切なイラストを守ろう！\n")}&url=${encodeURIComponent(typeof window !== "undefined" ? window.location.origin : "")}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Button variant="ghost" size="sm" title="Xで共有">
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                    </svg>
                  </Button>
                </a>
              </>
            )}

            <Button
              variant="ghost"
              size="sm"
              disabled={deletingId === img.image_id}
              onClick={() => handleDelete(img.image_id)}
              className="text-red-500 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
            >
              {deletingId === img.image_id ? (
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="m19 7-.867 12.142A2 2 0 0 1 16.138 21H7.862a2 2 0 0 1-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v3M4 7h16"
                  />
                </svg>
              )}
            </Button>
          </CardContent>
        </Card>
      ))}

      {/* Pagination controls */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between pt-4">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </Button>
          <span className="text-sm text-zinc-500">
            Page {page} of {Math.ceil(total / PAGE_SIZE)}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={!hasMore}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
