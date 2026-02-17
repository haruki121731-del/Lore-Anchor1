import type { ImageStatus } from "./image";

export interface UploadResponse {
  image_id: string;
  status: ImageStatus;
}
