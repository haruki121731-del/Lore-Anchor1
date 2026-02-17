export type ImageStatus = "pending" | "processing" | "completed" | "failed";

export interface ImageRecord {
  id: string;
  user_id: string;
  original_url: string;
  protected_url: string | null;
  watermark_id: string | null;
  status: ImageStatus;
  created_at: string;
}
