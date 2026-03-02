import type {
  DownloadTrackedResponse,
  DeleteResponse,
  ImageRecord,
  PaginatedImageList,
  RetryResponse,
  TaskStatus,
  UploadResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function getApiError(res: Response): Promise<string> {
  let detail = res.statusText;
  try {
    const body = await res.json();
    if (body.detail) detail = body.detail;
  } catch {
    // use statusText
  }
  return detail;
}

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
        let detail = xhr.statusText;
        try {
          const body = JSON.parse(xhr.responseText);
          if (body.detail) detail = body.detail;
        } catch {
          // use statusText
        }
        reject(new Error(`Upload failed (${xhr.status}): ${detail}`));
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
    cache: "no-store",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const detail = await getApiError(res);
    throw new Error(`Failed to fetch image (${res.status}): ${detail}`);
  }
  return res.json() as Promise<ImageRecord>;
}

export async function listImages(
  token: string,
  page: number = 1,
  pageSize: number = 20
): Promise<PaginatedImageList> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  const res = await fetch(`${API_BASE}/api/v1/images/?${params}`, {
    cache: "no-store",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const detail = await getApiError(res);
    throw new Error(`Failed to fetch images (${res.status}): ${detail}`);
  }
  return res.json() as Promise<PaginatedImageList>;
}

export async function deleteImage(
  imageId: string,
  token: string
): Promise<DeleteResponse> {
  const res = await fetch(`${API_BASE}/api/v1/images/${imageId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const detail = await getApiError(res);
    throw new Error(`Failed to delete image (${res.status}): ${detail}`);
  }
  return res.json() as Promise<DeleteResponse>;
}

export async function getTaskStatus(
  imageId: string,
  token: string
): Promise<TaskStatus> {
  const res = await fetch(`${API_BASE}/api/v1/tasks/${imageId}/status`, {
    cache: "no-store",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const detail = await getApiError(res);
    throw new Error(`Failed to fetch task status (${res.status}): ${detail}`);
  }
  return res.json() as Promise<TaskStatus>;
}

export async function retryTask(
  imageId: string,
  token: string
): Promise<RetryResponse> {
  const res = await fetch(`${API_BASE}/api/v1/tasks/${imageId}/retry`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const detail = await getApiError(res);
    throw new Error(`Failed to retry task (${res.status}): ${detail}`);
  }
  return res.json() as Promise<RetryResponse>;
}

export async function trackDownload(
  imageId: string,
  token: string
): Promise<DownloadTrackedResponse> {
  const res = await fetch(`${API_BASE}/api/v1/images/${imageId}/downloaded`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const detail = await getApiError(res);
    throw new Error(`Failed to track download (${res.status}): ${detail}`);
  }
  return res.json() as Promise<DownloadTrackedResponse>;
}
