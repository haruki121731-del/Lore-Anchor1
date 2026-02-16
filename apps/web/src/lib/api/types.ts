export type ImageStatus = "pending" | "processing" | "completed" | "failed";

export interface ImageRecord {
  image_id: string;
  user_id: string;
  original_url: string;
  status: ImageStatus;
  protected_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface UploadResponse {
  image_id: string;
  status: ImageStatus;
}
