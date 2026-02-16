"use client";

import { useState, useEffect, useCallback } from "react";
import type { ImageRecord, ImageStatus } from "@/lib/api/types";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

// Mock data for development — replace with real API calls once backend is ready
const MOCK_IMAGES: ImageRecord[] = [
  {
    image_id: "img_001",
    user_id: "user_1",
    original_filename: "photo_landscape.png",
    status: "completed",
    protected_url: "https://placehold.co/400x300/png?text=Protected+Image",
    created_at: "2026-02-15T10:00:00Z",
    updated_at: "2026-02-15T10:05:00Z",
  },
  {
    image_id: "img_002",
    user_id: "user_1",
    original_filename: "artwork_v2.jpg",
    status: "processing",
    protected_url: null,
    created_at: "2026-02-16T08:30:00Z",
    updated_at: "2026-02-16T08:30:00Z",
  },
  {
    image_id: "img_003",
    user_id: "user_1",
    original_filename: "portrait_final.webp",
    status: "pending",
    protected_url: null,
    created_at: "2026-02-16T09:00:00Z",
    updated_at: "2026-02-16T09:00:00Z",
  },
];

function StatusBadge({ status }: { status: ImageStatus }) {
  const colors: Record<ImageStatus, string> = {
    pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    processing: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    completed: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
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

interface ImageListProps {
  refreshKey: number;
}

export function ImageList({ refreshKey }: ImageListProps) {
  const [images, setImages] = useState<ImageRecord[]>(MOCK_IMAGES);

  const fetchImages = useCallback(() => {
    // TODO: Replace with real API call
    // For now, cycle mock statuses to simulate polling updates
    setImages((prev) =>
      prev.map((img) => {
        if (img.status === "pending") {
          return { ...img, status: "processing" as const, updated_at: new Date().toISOString() };
        }
        if (img.status === "processing" && Math.random() > 0.7) {
          return {
            ...img,
            status: "completed" as const,
            protected_url: "https://placehold.co/400x300/png?text=Protected+Image",
            updated_at: new Date().toISOString(),
          };
        }
        return img;
      })
    );
  }, []);

  // Poll every 5 seconds
  useEffect(() => {
    const interval = setInterval(fetchImages, 5000);
    return () => clearInterval(interval);
  }, [fetchImages]);

  // Reset mock data when a new upload completes
  useEffect(() => {
    if (refreshKey > 0) {
      setImages(MOCK_IMAGES);
    }
  }, [refreshKey]);

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
                alt={img.original_filename}
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
                {img.original_filename}
              </p>
              <p className="text-xs text-zinc-500">
                {new Date(img.created_at).toLocaleString()}
              </p>
            </div>

            <StatusBadge status={img.status} />

            {img.status === "completed" && img.protected_url && (
              <Button variant="outline" size="sm" asChild>
                <a href={img.protected_url} download={img.original_filename}>
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
