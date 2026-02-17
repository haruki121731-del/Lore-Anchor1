export type ImageStatus = "pending" | "processing" | "completed" | "failed";

export interface ImageRecord {
  image_id: string;
  user_id: string;
  original_url: string;
  protected_url: string | null;
  watermark_id: string | null;
  c2pa_manifest: Record<string, unknown> | null;
  status: ImageStatus;
  created_at: string;
  updated_at: string;
}
