import type { ImageRecord, UploadResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function uploadImage(
  file: File,
  token: string,
  onProgress?: (percent: number) => void
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/v1/images/upload`);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as UploadResponse);
      } else {
        reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error")));

    const formData = new FormData();
    formData.append("file", file);
    xhr.send(formData);
  });
}

export async function getImage(
  imageId: string,
  token: string
): Promise<ImageRecord> {
  const res = await fetch(`${API_BASE}/api/v1/images/${imageId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to fetch image: ${res.status}`);
  return res.json() as Promise<ImageRecord>;
}

export async function listImages(
  token: string
): Promise<ImageRecord[]> {
  const res = await fetch(`${API_BASE}/api/v1/images/`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to fetch images: ${res.status}`);
  const data = (await res.json()) as { images: ImageRecord[] };
  return data.images;
}
