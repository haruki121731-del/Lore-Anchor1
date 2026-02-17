"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { ImageRecord, ImageStatus } from "@/lib/api/types";
import { listImages } from "@/lib/api/images";
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

export function ImageList({ refreshKey }: ImageListProps) {
  const [images, setImages] = useState<ImageRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const mountedRef = useRef(true);

  const fetchImages = useCallback(async () => {
    try {
      const supabase = getSupabaseClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        if (mountedRef.current) setError("Not authenticated");
        return;
      }

      const data = await listImages(session.access_token);
      if (mountedRef.current) {
        setImages(data);
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
  }, []);

  // Initial fetch + refetch on refreshKey change
  useEffect(() => {
    setLoading(true);
    fetchImages();
  }, [fetchImages, refreshKey]);

  // Poll every 5 seconds, stop when all images are completed or failed
  useEffect(() => {
    const allSettled =
      images.length > 0 &&
      images.every((img) => img.status === "completed" || img.status === "failed");

    if (allSettled) return;

    const interval = setInterval(fetchImages, 5000);
    return () => clearInterval(interval);
  }, [fetchImages, images]);

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
            fetchImages();
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
              <Button variant="outline" size="sm" asChild>
                <a
                  href={img.protected_url}
                  download={extractFilename(img.original_url)}
                >
                  Download
                </a>
              </Button>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
