export type ImageStatus = "pending" | "processing" | "completed" | "failed";

export interface ImageRecord {
  image_id: string;
  user_id: string;
  original_url: string;
  status: ImageStatus;
  protected_url: string | null;
  created_at: string;
  updated_at: string;
  c2pa_manifest: Record<string, unknown> | null;
}

export interface UploadResponse {
  image_id: string;
  status: ImageStatus;
}

export interface DeleteResponse {
  image_id: string;
  deleted: boolean;
}

export interface PaginatedImageList {
  images: ImageRecord[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}
