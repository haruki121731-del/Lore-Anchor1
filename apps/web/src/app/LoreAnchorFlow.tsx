"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from "react";
import type { JSX } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, ImagePlus, Share2, ShieldCheck, Twitter } from "lucide-react";
import { getSupabaseClient } from "@/lib/supabase/client";
import { getImage, getTaskStatus, trackDownload, uploadImage } from "@/lib/api/images";

export type AppState = "landing" | "idle" | "processing" | "success";

const ALLOWED_CONTENT_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);
const MAX_FILE_BYTES = 20 * 1024 * 1024;
const POLLING_INTERVAL_MS = 2000;
const PROCESSING_TIMEOUT_MS = 120000;

type NavigatorWithCanShare = Navigator & {
  canShare?: (data?: ShareData) => boolean;
};

export default function LoreAnchorFlow(): JSX.Element {
  const router = useRouter();

  const [appState, setAppState] = useState<AppState>("landing");
  const [downloadLabel, setDownloadLabel] = useState("Download Protected Image");
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedPreviewUrl, setSelectedPreviewUrl] = useState<string | null>(null);
  const [protectedImageUrl, setProtectedImageUrl] = useState<string | null>(null);
  const [protectedPreviewUrl, setProtectedPreviewUrl] = useState<string | null>(null);
  const [protectedImageBlob, setProtectedImageBlob] = useState<Blob | null>(null);
  const [currentImageId, setCurrentImageId] = useState<string | null>(null);
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [processingError, setProcessingError] = useState<string | null>(null);
  const [originalFileName, setOriginalFileName] = useState("my_art");
  const [isDragActive, setIsDragActive] = useState(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const toastTimerRef = useRef<number | null>(null);
  const downloadLabelTimerRef = useRef<number | null>(null);
  const pollingIntervalRef = useRef<number | null>(null);
  const processingTimeoutRef = useRef<number | null>(null);
  const selectedPreviewUrlRef = useRef<string | null>(null);
  const protectedPreviewUrlRef = useRef<string | null>(null);
  const processingRunRef = useRef(0);

  const showToast = useCallback((message: string, durationMs: number): void => {
    setToastMessage(message);

    if (toastTimerRef.current !== null) {
      window.clearTimeout(toastTimerRef.current);
    }

    toastTimerRef.current = window.setTimeout(() => {
      setToastMessage(null);
      toastTimerRef.current = null;
    }, durationMs);
  }, []);

  const clearPollingMonitors = useCallback((): void => {
    if (pollingIntervalRef.current !== null) {
      window.clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    if (processingTimeoutRef.current !== null) {
      window.clearTimeout(processingTimeoutRef.current);
      processingTimeoutRef.current = null;
    }
  }, []);

  const clearDownloadLabelTimer = useCallback((): void => {
    if (downloadLabelTimerRef.current !== null) {
      window.clearTimeout(downloadLabelTimerRef.current);
      downloadLabelTimerRef.current = null;
    }
  }, []);

  const replaceSelectedPreviewUrl = useCallback((nextUrl: string | null): void => {
    setSelectedPreviewUrl((prevUrl) => {
      if (prevUrl && prevUrl.startsWith("blob:")) {
        URL.revokeObjectURL(prevUrl);
      }
      return nextUrl;
    });
  }, []);

  const replaceProtectedPreviewUrl = useCallback((nextUrl: string | null): void => {
    setProtectedPreviewUrl((prevUrl) => {
      if (prevUrl && prevUrl.startsWith("blob:")) {
        URL.revokeObjectURL(prevUrl);
      }
      return nextUrl;
    });
  }, []);

  const resetToIdleWithError = useCallback(
    (message: string): void => {
      processingRunRef.current += 1;
      clearPollingMonitors();
      clearDownloadLabelTimer();

      setAppState("idle");
      setDownloadLabel("Download Protected Image");
      setCurrentImageId(null);
      setProtectedImageUrl(null);
      replaceProtectedPreviewUrl(null);
      setProtectedImageBlob(null);
      setProcessingError(message);

      showToast(message, 3000);
    },
    [clearDownloadLabelTimer, clearPollingMonitors, replaceProtectedPreviewUrl, showToast]
  );

  const getProtectedBlobOrNotify = useCallback((): Blob | null => {
    if (!protectedImageBlob) {
      showToast("保護画像の準備が完了していません。", 3000);
      return null;
    }
    return protectedImageBlob;
  }, [protectedImageBlob, showToast]);

  const copyImageToClipboard = useCallback(async (blob: Blob): Promise<void> => {
    if (typeof ClipboardItem === "undefined" || !navigator.clipboard?.write) {
      throw new Error("Clipboard API is unavailable");
    }

    const item = new ClipboardItem({ "image/png": blob });
    await navigator.clipboard.write([item]);
  }, []);

  const startStatusPolling = useCallback(
    (imageId: string, token: string, fallbackBlob: Blob, runId: number): void => {
      clearPollingMonitors();
      let inFlight = false;

      const pollStatus = async (): Promise<void> => {
        if (inFlight || runId !== processingRunRef.current) {
          return;
        }

        inFlight = true;
        try {
          const task = await getTaskStatus(imageId, token);
          if (runId !== processingRunRef.current) {
            return;
          }

          if (task.status === "failed") {
            const message = task.error_log
              ? `画像の保護処理に失敗しました: ${task.error_log}`
              : "画像の保護処理に失敗しました。再度アップロードしてください。";
            resetToIdleWithError(message);
            return;
          }

          if (task.status !== "completed") {
            return;
          }

          clearPollingMonitors();

          const image = await getImage(imageId, token);
          if (runId !== processingRunRef.current) {
            return;
          }

          setProtectedImageUrl(image.protected_url ?? null);

          let finalBlob = fallbackBlob;
          if (image.protected_url) {
            try {
              const response = await fetch(image.protected_url, { cache: "no-store" });
              if (response.ok) {
                finalBlob = await response.blob();
              } else {
                showToast("保護済み画像の取得に失敗したため元画像を表示します。", 3000);
              }
            } catch {
              showToast("保護済み画像の取得に失敗したため元画像を表示します。", 3000);
            }
          }

          if (runId !== processingRunRef.current) {
            return;
          }

          const previewUrl = URL.createObjectURL(finalBlob);
          replaceProtectedPreviewUrl(previewUrl);
          setProtectedImageBlob(finalBlob);
          setProcessingError(null);
          setAppState("success");
        } catch {
          if (runId !== processingRunRef.current) {
            return;
          }
          resetToIdleWithError("処理状況の取得に失敗しました。再度アップロードしてください。");
        } finally {
          inFlight = false;
        }
      };

      pollingIntervalRef.current = window.setInterval(() => {
        void pollStatus();
      }, POLLING_INTERVAL_MS);

      processingTimeoutRef.current = window.setTimeout(() => {
        if (runId !== processingRunRef.current) {
          return;
        }
        resetToIdleWithError("処理がタイムアウトしました。再度アップロードしてください。");
      }, PROCESSING_TIMEOUT_MS);

      void pollStatus();
    },
    [clearPollingMonitors, replaceProtectedPreviewUrl, resetToIdleWithError, showToast]
  );

  const ensureSessionToken = useCallback(async (): Promise<string | null> => {
    try {
      const supabase = getSupabaseClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session?.access_token) {
        showToast("ログインが必要です。ログイン画面へ移動します。", 2200);
        window.setTimeout(() => {
          router.push("/login");
        }, 250);
        return null;
      }

      return session.access_token;
    } catch {
      showToast("ログイン状態を確認できませんでした。", 2200);
      window.setTimeout(() => {
        router.push("/login");
      }, 250);
      return null;
    }
  }, [router, showToast]);

  const handleSelectedFile = useCallback(
    async (file: File): Promise<void> => {
      if (!ALLOWED_CONTENT_TYPES.has(file.type)) {
        showToast("対応形式は PNG / JPEG / WebP のみです。", 3000);
        return;
      }

      if (file.size > MAX_FILE_BYTES) {
        showToast("ファイルサイズは20MB以下にしてください。", 3000);
        return;
      }

      const token = await ensureSessionToken();
      if (!token) {
        return;
      }

      const runId = processingRunRef.current + 1;
      processingRunRef.current = runId;

      clearPollingMonitors();
      clearDownloadLabelTimer();
      replaceProtectedPreviewUrl(null);

      const previewUrl = URL.createObjectURL(file);
      replaceSelectedPreviewUrl(previewUrl);

      const baseName = file.name.replace(/\.[^/.]+$/, "").trim();

      setSelectedFile(file);
      setSessionToken(token);
      setOriginalFileName(baseName || "my_art");
      setDownloadLabel("Download Protected Image");
      setCurrentImageId(null);
      setProtectedImageUrl(null);
      setProtectedImageBlob(file);
      setProcessingError(null);
      setAppState("processing");

      try {
        const uploadResult = await uploadImage(file, token);
        if (runId !== processingRunRef.current) {
          return;
        }

        setCurrentImageId(uploadResult.image_id);
        startStatusPolling(uploadResult.image_id, token, file, runId);
      } catch {
        if (runId !== processingRunRef.current) {
          return;
        }
        resetToIdleWithError("アップロードに失敗しました。再度アップロードしてください。");
      }
    },
    [
      clearDownloadLabelTimer,
      clearPollingMonitors,
      ensureSessionToken,
      replaceProtectedPreviewUrl,
      replaceSelectedPreviewUrl,
      resetToIdleWithError,
      showToast,
      startStatusPolling,
    ]
  );

  const handleFileInputChange = useCallback(
    (event: ChangeEvent<HTMLInputElement>): void => {
      const file = event.target.files?.[0];
      if (file) {
        void handleSelectedFile(file);
      }
      event.target.value = "";
    },
    [handleSelectedFile]
  );

  const handleDropzoneClick = useCallback((): void => {
    fileInputRef.current?.click();
  }, []);

  const handleDragOver = useCallback((event: DragEvent<HTMLDivElement>): void => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((event: DragEvent<HTMLDivElement>): void => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragActive(false);
  }, []);

  const handleDrop = useCallback(
    (event: DragEvent<HTMLDivElement>): void => {
      event.preventDefault();
      event.stopPropagation();
      setIsDragActive(false);

      const file = event.dataTransfer.files?.[0];
      if (file) {
        void handleSelectedFile(file);
      }
    },
    [handleSelectedFile]
  );

  const handleDownload = useCallback(async (): Promise<void> => {
    try {
      const blob = getProtectedBlobOrNotify();
      if (!blob) {
        return;
      }

      const objectUrl = URL.createObjectURL(blob);
      try {
        const anchor = document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = `${originalFileName}_protected.png`;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
      } finally {
        URL.revokeObjectURL(objectUrl);
      }

      setDownloadLabel("✓ Downloaded");
      clearDownloadLabelTimer();
      downloadLabelTimerRef.current = window.setTimeout(() => {
        setDownloadLabel("Download Protected Image");
        downloadLabelTimerRef.current = null;
      }, 1500);

      if (currentImageId && sessionToken) {
        try {
          await trackDownload(currentImageId, sessionToken);
        } catch {
          showToast("ダウンロード記録の送信に失敗しました。", 3000);
        }
      }
    } catch {
      showToast("ダウンロードに失敗しました。", 3000);
    }
  }, [
    clearDownloadLabelTimer,
    currentImageId,
    getProtectedBlobOrNotify,
    originalFileName,
    sessionToken,
    showToast,
  ]);

  const handleShare = useCallback(async (): Promise<void> => {
    try {
      const blob = getProtectedBlobOrNotify();
      if (!blob) {
        return;
      }

      const imageFile = new File([blob], `${originalFileName}_protected.png`, {
        type: "image/png",
      });
      const navigatorWithCanShare = navigator as NavigatorWithCanShare;

      if (navigatorWithCanShare.canShare && navigatorWithCanShare.canShare({ files: [imageFile] })) {
        try {
          await navigator.share({ files: [imageFile], title: "Lore-Anchor Protected" });
          return;
        } catch {
          await copyImageToClipboard(blob);
          showToast("✓ 画像をコピーしました（Cmd+V / Ctrl+V で貼り付けできます）", 3000);
          return;
        }
      }

      await copyImageToClipboard(blob);
      showToast("✓ 画像をコピーしました（Cmd+V / Ctrl+V で貼り付けできます）", 3000);
    } catch {
      showToast("共有に失敗しました。", 3000);
    }
  }, [copyImageToClipboard, getProtectedBlobOrNotify, originalFileName, showToast]);

  const handleTwitterShare = useCallback(async (): Promise<void> => {
    try {
      const blob = getProtectedBlobOrNotify();
      if (!blob) {
        return;
      }

      await copyImageToClipboard(blob);
      const tweetText = encodeURIComponent("この作品はLore-Anchorで保護されています\n#LoreAnchor\n");
      const twitterUrl = `https://twitter.com/intent/tweet?text=${tweetText}`;
      window.open(twitterUrl, "_blank", "noopener,noreferrer");
      showToast(
        "✓ 画像をコピーしました。開いたXの画面でペースト（Cmd+V / Ctrl+V）して添付してください",
        4000
      );
    } catch {
      showToast("X共有の準備に失敗しました。", 4000);
    }
  }, [copyImageToClipboard, getProtectedBlobOrNotify, showToast]);

  useEffect(() => {
    selectedPreviewUrlRef.current = selectedPreviewUrl;
  }, [selectedPreviewUrl]);

  useEffect(() => {
    protectedPreviewUrlRef.current = protectedPreviewUrl;
  }, [protectedPreviewUrl]);

  useEffect(() => {
    return () => {
      processingRunRef.current += 1;
      clearPollingMonitors();
      clearDownloadLabelTimer();

      if (toastTimerRef.current !== null) {
        window.clearTimeout(toastTimerRef.current);
      }

      const selectedUrl = selectedPreviewUrlRef.current;
      if (selectedUrl && selectedUrl.startsWith("blob:")) {
        URL.revokeObjectURL(selectedUrl);
      }

      const protectedUrl = protectedPreviewUrlRef.current;
      if (protectedUrl && protectedUrl.startsWith("blob:")) {
        URL.revokeObjectURL(protectedUrl);
      }
    };
  }, [clearDownloadLabelTimer, clearPollingMonitors]);

  const processingImageSrc = selectedPreviewUrl;
  const successImageSrc = protectedPreviewUrl ?? selectedPreviewUrl;

  return (
    <main className="flex flex-col items-center justify-center min-h-screen w-full px-[16px] overflow-hidden relative bg-gradient-to-b from-[#F8FAFC] to-[#FFFFFF] font-sans">
      <AnimatePresence mode="wait">
        {appState === "landing" && (
          <motion.div
            key="landing"
            className="flex flex-col items-center justify-center w-full max-w-[800px] text-center"
            exit={{ opacity: 0, y: -24, filter: "blur(8px)" }}
            transition={{ duration: 0.4, ease: [0.32, 0.72, 0, 1] }}
          >
            <span className="text-[11px] font-bold tracking-[0.25em] text-[#0D9488] mb-[24px]">
              PRIVATE BETA
            </span>
            <h1 className="text-[40px] md:text-[64px] font-[800] leading-[1.1] tracking-[-0.02em] text-[#111827] mb-[24px]">
              画像を守る。権利を証明する。
            </h1>
            <p className="text-[16px] md:text-[18px] font-normal leading-[1.6] text-[#6B7280] max-w-[540px] mb-[40px]">
              複雑な技術はすべて裏側へ。あなたの作品をワンクリックでAIの無断学習から保護します。
            </p>
            <motion.button
              type="button"
              whileHover={{ scale: 1.04, boxShadow: "0 12px 32px rgba(0,0,0,0.16)" }}
              whileTap={{ scale: 0.96 }}
              className="h-[64px] px-[40px] rounded-[32px] bg-[#000000] text-[#FFFFFF] shadow-[0_8px_24px_rgba(0,0,0,0.12)] flex items-center justify-center gap-[12px]"
              onClick={() => setAppState("idle")}
            >
              <span className="text-[18px] font-bold tracking-[-0.01em]">今すぐ保護をはじめる</span>
              <ArrowRight size={24} strokeWidth={2.5} color="#FFFFFF" />
            </motion.button>
          </motion.div>
        )}

        {appState === "idle" && (
          <motion.div
            key="idle"
            initial={{ opacity: 0, y: 32, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className="w-full max-w-[720px] aspect-[4/3] md:aspect-[16/10]"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={handleFileInputChange}
            />
            <div
              className={`w-full h-full rounded-[24px] bg-[rgba(255,255,255,0.7)] backdrop-blur-[12px] border-[3px] border-dashed border-[#E5E7EB] hover:border-[#60A5FA] hover:bg-[rgba(239,246,255,0.4)] transition-all duration-300 ease-out flex flex-col items-center justify-center cursor-pointer group ${
                isDragActive ? "border-[#60A5FA] bg-[rgba(239,246,255,0.4)]" : ""
              }`}
              onClick={handleDropzoneClick}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <ImagePlus
                size={48}
                strokeWidth={1.5}
                className="text-[#9CA3AF] group-hover:text-[#60A5FA] transition-colors duration-300"
              />
              <span className="text-[16px] font-medium text-[#6B7280] mt-[20px] group-hover:text-[#3B82F6] transition-colors duration-300">
                Tap or drop your art here.
              </span>
            </div>
          </motion.div>
        )}

        {appState === "processing" && (
          <motion.div key="processing" className="w-full flex flex-col items-center">
            <div className="w-full max-w-[720px] aspect-[4/3] md:aspect-[16/10]">
              <div className="w-full h-full rounded-[24px] bg-[#000000] overflow-hidden shadow-[0_24px_48px_rgba(0,0,0,0.2)] relative flex flex-col items-center justify-center">
                {processingImageSrc && (
                  <Image
                    src={processingImageSrc}
                    alt="preview"
                    layout="fill"
                    objectFit="cover"
                    style={{ opacity: 0.8 }}
                    unoptimized
                  />
                )}
                <motion.div
                  className="absolute left-0 right-0 z-10 h-[3px] bg-[#3B82F6]"
                  style={{ boxShadow: "0 0 24px 6px rgba(59, 130, 246, 0.9)" }}
                  initial={{ top: "-5%" }}
                  animate={{ top: "105%" }}
                  transition={{ duration: 1.8, ease: "linear", repeat: Infinity }}
                />
              </div>
            </div>
          </motion.div>
        )}

        {appState === "success" && (
          <motion.div key="success" className="w-full flex flex-col items-center">
            <div className="w-full max-w-[720px] aspect-[4/3] md:aspect-[16/10]">
              <div className="w-full h-full rounded-[24px] bg-[#000000] overflow-hidden shadow-[0_24px_48px_rgba(0,0,0,0.2)] relative flex flex-col items-center justify-center">
                {successImageSrc && (
                  <Image
                    src={successImageSrc}
                    alt="preview"
                    layout="fill"
                    objectFit="cover"
                    style={{ opacity: 1.0 }}
                    unoptimized
                  />
                )}
                <motion.div
                  className="absolute top-[24px] right-[24px] z-20 w-[48px] h-[48px] rounded-full bg-[#3B82F6] shadow-[0_8px_16px_rgba(59,130,246,0.3)] flex items-center justify-center"
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ type: "spring", stiffness: 400, damping: 25, delay: 0.1 }}
                >
                  <ShieldCheck size={24} strokeWidth={2.5} color="#FFFFFF" />
                </motion.div>
              </div>
            </div>

            <motion.div
              className="mt-[32px] flex flex-col sm:flex-row items-center justify-center gap-[16px] w-full max-w-[720px]"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay: 0.4 }}
            >
              <button
                type="button"
                className="w-full sm:w-auto flex-1 h-[64px] rounded-[32px] bg-[#111827] hover:bg-[#000000] text-[#FFFFFF] text-[18px] font-bold transition-colors duration-200"
                onClick={() => {
                  void handleDownload();
                }}
              >
                {downloadLabel}
              </button>
              <button
                type="button"
                className="w-[64px] h-[64px] shrink-0 rounded-full bg-[#111827] hover:bg-[#000000] text-[#FFFFFF] flex items-center justify-center transition-colors duration-200"
                onClick={() => {
                  void handleShare();
                }}
              >
                <Share2 size={24} />
              </button>
              <button
                type="button"
                className="w-[64px] h-[64px] shrink-0 rounded-full bg-[#111827] hover:bg-[#000000] text-[#FFFFFF] flex items-center justify-center transition-colors duration-200"
                onClick={() => {
                  void handleTwitterShare();
                }}
              >
                <Twitter size={24} />
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <span className="sr-only" aria-live="polite">
        {processingError ?? ""}
      </span>
      <span className="sr-only">
        {selectedFile?.name ?? ""}
      </span>
      <span className="sr-only">
        {protectedImageUrl ?? ""}
      </span>

      <AnimatePresence>
        {toastMessage && (
          <motion.div
            key={toastMessage}
            className="fixed bottom-[24px] left-1/2 -translate-x-1/2 z-50 px-[20px] py-[12px] rounded-[999px] bg-[#111827] text-[#FFFFFF] text-[14px] leading-[1.4] shadow-[0_12px_24px_rgba(0,0,0,0.2)]"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          >
            {toastMessage}
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}
