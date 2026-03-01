"use client";

import { useEffect, useState } from "react";
import type { JSX } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ImageDown, ImagePlus, Music2, ShieldCheck, X } from "lucide-react";

type Status = "idle" | "processing" | "success";

const STATUS_ORDER: Status[] = ["idle", "processing", "success"];
const MOCK_IMAGE_URL =
  "https://images.unsplash.com/photo-1513364776144-60967b0f800f?auto=format&fit=crop&w=1200&q=80";

function nextStatus(current: Status): Status {
  const index = STATUS_ORDER.indexOf(current);
  return STATUS_ORDER[(index + 1) % STATUS_ORDER.length];
}

export default function MagicUpload(): JSX.Element {
  const [status, setStatus] = useState<Status>("idle");

  useEffect(() => {
    const timer = window.setInterval(() => {
      setStatus((prev) => nextStatus(prev));
    }, 2000);

    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="flex min-h-[100dvh] w-full items-center justify-center bg-[#f6f6f3] p-4 sm:p-8">
      <div className="w-full max-w-[1120px]">
        <div className="relative aspect-[16/9] overflow-hidden rounded-[36px] bg-white shadow-[0_20px_70px_rgba(17,43,76,0.24)]">
          <AnimatePresence mode="wait">
            {status === "idle" && (
              <motion.div
                key="idle"
                initial={{ opacity: 0, scale: 0.985 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.99 }}
                transition={{ duration: 0.22, ease: "easeOut" }}
                className="absolute inset-0 flex items-center justify-center"
              >
                <div className="absolute inset-2 rounded-[30px] border border-dashed border-[#d5d5d5]" />
                <div className="relative z-10 flex flex-col items-center gap-6 text-center">
                  <ImagePlus className="h-20 w-20 text-[#595959]" strokeWidth={1.7} />
                  <p className="text-3xl font-medium tracking-[-0.02em] text-[#222] sm:text-5xl">
                    Protect your art. Tap or drop.
                  </p>
                </div>
              </motion.div>
            )}

            {(status === "processing" || status === "success") && (
              <motion.div
                key={status}
                initial={{ opacity: 0, scale: 0.99 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.99 }}
                transition={{ duration: 0.2 }}
                className={`absolute inset-0 flex items-center justify-center ${
                  status === "processing" ? "bg-[#031229]" : "bg-white"
                }`}
              >
                <div className="relative h-[88%] w-[42%] min-w-[260px] max-w-[470px] overflow-hidden rounded-[24px] shadow-[0_18px_55px_rgba(8,18,37,0.35)]">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={MOCK_IMAGE_URL}
                    alt=""
                    className="h-full w-full object-cover"
                    draggable={false}
                  />

                  {status === "success" && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: [0, 1.2, 1] }}
                      transition={{ type: "spring", stiffness: 280, damping: 16 }}
                      className="absolute right-3 top-3 flex h-12 w-12 items-center justify-center rounded-full bg-[#2f8dff] shadow-[0_8px_20px_rgba(46,141,255,0.55)]"
                    >
                      <ShieldCheck className="h-6 w-6 text-white" strokeWidth={2.5} />
                    </motion.div>
                  )}
                </div>

                {status === "processing" && (
                  <div className="pointer-events-none absolute inset-0 overflow-hidden">
                    <motion.div
                      className="absolute inset-0"
                      animate={{ y: ["0%", "100%"] }}
                      transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                    >
                      <div
                        className="h-[2px] w-full bg-[#6ae2ff]"
                        style={{
                          boxShadow:
                            "0 0 12px #3dd5ff, 0 0 28px #3dd5ff, 0 0 42px rgba(61,213,255,0.95)",
                        }}
                      />
                    </motion.div>
                  </div>
                )}

                {status === "success" && (
                  <motion.div
                    initial={{ y: "100%" }}
                    animate={{ y: 0 }}
                    transition={{ duration: 0.35, ease: [0.22, 0.61, 0.36, 1] }}
                    className="absolute inset-x-0 bottom-0 mx-auto w-[min(640px,92%)] rounded-t-[30px] bg-white px-6 pb-7 pt-6 shadow-[0_-14px_34px_rgba(24,33,51,0.15)]"
                  >
                    <button className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2 rounded-full bg-black px-10 py-3 text-lg font-medium text-white shadow-[0_10px_22px_rgba(0,0,0,0.35)]">
                      Save Photo
                    </button>

                    <div className="mt-8 flex items-center justify-center gap-5 sm:gap-8">
                      <button
                        aria-label="TikTok"
                        className="flex h-14 w-14 items-center justify-center rounded-full bg-black text-white shadow-[0_8px_18px_rgba(0,0,0,0.28)]"
                      >
                        <Music2 className="h-6 w-6" />
                      </button>

                      <button
                        aria-label="X"
                        className="flex h-14 w-14 items-center justify-center rounded-full bg-black text-white shadow-[0_8px_18px_rgba(0,0,0,0.28)]"
                      >
                        <X className="h-6 w-6" />
                      </button>

                      <button
                        aria-label="Save to Photos"
                        className="flex h-14 w-14 items-center justify-center rounded-full bg-black text-white shadow-[0_8px_18px_rgba(0,0,0,0.28)]"
                      >
                        <ImageDown className="h-6 w-6" />
                      </button>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
