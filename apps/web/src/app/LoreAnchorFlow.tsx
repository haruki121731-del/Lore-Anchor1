"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import type { JSX } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, ImagePlus, Share, ShieldCheck, Twitter } from "lucide-react";

export type AppState = "landing" | "idle" | "processing" | "success";

const MOCK_IMAGE_SRC =
  "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1200";

export default function LoreAnchorFlow(): JSX.Element {
  const [appState, setAppState] = useState<AppState>("landing");

  useEffect(() => {
    if (appState !== "processing") {
      return;
    }

    const timerId = window.setTimeout(() => {
      setAppState("success");
    }, 4000);

    return () => {
      window.clearTimeout(timerId);
    };
  }, [appState]);

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 md:p-8 relative bg-gradient-to-b from-blue-50/40 to-white">
      <AnimatePresence mode="wait">
        {appState === "landing" && (
          <motion.div
            key="landing"
            initial={{ opacity: 0, y: 24, filter: "blur(6px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -20, filter: "blur(10px)" }}
            transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
            className="w-full max-w-4xl text-center"
          >
            <p className="text-xs font-bold tracking-[0.2em] text-blue-600 mb-6">PRIVATE BETA</p>
            <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-gray-900 mb-6">
              画像を守る。権利を証明する。
            </h1>
            <p className="text-gray-500 max-w-xl mx-auto mb-10 text-base md:text-lg">
              複雑な技術はすべて裏側へ。あなたの作品をワンクリックでAIの無断学習から保護します。
            </p>
            <motion.button
              type="button"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="bg-black text-white px-8 py-4 rounded-full font-bold text-lg shadow-2xl flex items-center gap-2 mx-auto"
              onClick={() => setAppState("idle")}
            >
              <span>今すぐ保護をはじめる</span>
              <ArrowRight className="h-5 w-5" />
            </motion.button>
          </motion.div>
        )}

        {appState === "idle" && (
          <motion.div
            key="idle"
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.98 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="w-full max-w-3xl"
          >
            <button
              type="button"
              className="w-full max-w-3xl aspect-[4/3] md:aspect-[16/10] bg-white/80 backdrop-blur-sm rounded-3xl border-4 border-dashed border-gray-200 hover:border-blue-400/50 transition-colors flex flex-col items-center justify-center cursor-pointer relative overflow-hidden"
              onClick={() => setAppState("processing")}
            >
              <ImagePlus size={48} className="text-gray-400" />
              <p className="text-gray-500 font-medium mt-4">Tap or drop your art here.</p>
            </button>
          </motion.div>
        )}

        {(appState === "processing" || appState === "success") && (
          <motion.div
            key={appState}
            initial={{ opacity: 0, y: 18, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.99 }}
            transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
            className="w-full max-w-3xl"
          >
            <div className="w-full max-w-3xl aspect-[4/3] md:aspect-[16/10] border-none shadow-2xl overflow-hidden relative rounded-3xl">
              <Image
                src={MOCK_IMAGE_SRC}
                alt="Protected artwork preview"
                fill
                className="object-cover"
                priority
              />

              {appState === "processing" && (
                <motion.div
                  className="absolute left-0 right-0 h-[4px] bg-blue-500 z-10"
                  style={{ boxShadow: "0 0 30px 8px rgba(59, 130, 246, 0.8)" }}
                  initial={{ top: "-10%" }}
                  animate={{ top: "110%" }}
                  transition={{ duration: 2, ease: "linear", repeat: Infinity }}
                />
              )}

              {appState === "success" && (
                <div className="absolute top-4 right-4 md:top-6 md:right-6 z-20">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", bounce: 0.5 }}
                    className="w-12 h-12 bg-blue-500 rounded-full shadow-xl flex items-center justify-center text-white"
                  >
                    <ShieldCheck className="h-6 w-6" />
                  </motion.div>
                </div>
              )}
            </div>

            {appState === "success" && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="flex flex-wrap items-center justify-center gap-4 mt-8"
              >
                <button
                  type="button"
                  className="bg-black text-white px-8 py-4 rounded-full font-bold shadow-lg hover:bg-gray-800"
                >
                  Download Protected Image
                </button>
                <button
                  type="button"
                  aria-label="Share"
                  className="w-14 h-14 bg-black text-white rounded-full flex items-center justify-center hover:bg-gray-800"
                >
                  <Share className="h-6 w-6" />
                </button>
                <button
                  type="button"
                  aria-label="Twitter"
                  className="w-14 h-14 bg-black text-white rounded-full flex items-center justify-center hover:bg-gray-800"
                >
                  <Twitter className="h-6 w-6" />
                </button>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
