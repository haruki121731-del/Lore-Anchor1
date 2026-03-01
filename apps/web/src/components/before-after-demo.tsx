"use client";

import { useState } from "react";

/**
 * Static Before/After comparison demo.
 *
 * Shows sample artwork with a slider to compare the original (unprotected)
 * version vs the Lore-Anchor-protected version. Uses CSS-only noise overlay
 * to simulate the protective perturbation effect — no real API call required.
 */

const SAMPLES = [
  {
    id: "landscape",
    label: "風景イラスト",
    description:
      "Mist v2 の敵対的摂動は人間の目にはほぼ判別できませんが、AI の学習を妨害します。",
  },
  {
    id: "character",
    label: "キャラクター",
    description:
      "PixelSeal の不可視透かしが埋め込まれ、いつでも所有権を検証できます。",
  },
  {
    id: "pattern",
    label: "パターン/テクスチャ",
    description:
      "C2PA メタデータにより「AI学習禁止」が暗号学的に記録されます。",
  },
] as const;

function DemoCanvas({
  label,
  isProtected,
}: {
  label: string;
  isProtected: boolean;
}) {
  return (
    <div className="relative overflow-hidden rounded-lg border bg-gradient-to-br from-indigo-100 via-purple-50 to-pink-100 dark:from-indigo-950 dark:via-purple-950 dark:to-pink-950">
      <div className="aspect-square w-full">
        {/* Simulated artwork using CSS gradients */}
        <div className="absolute inset-0 bg-gradient-to-tr from-blue-200/60 via-transparent to-rose-200/60 dark:from-blue-800/40 dark:to-rose-800/40" />
        <div className="absolute inset-[20%] rounded-full bg-gradient-to-br from-violet-300/50 to-amber-200/50 blur-sm dark:from-violet-700/40 dark:to-amber-700/40" />
        <div className="absolute bottom-[15%] left-[10%] h-[30%] w-[25%] rounded-lg bg-gradient-to-t from-emerald-300/40 to-teal-200/40 dark:from-emerald-800/30 dark:to-teal-700/30" />

        {/* Protection overlay — subtle noise visible only on protected version */}
        {isProtected && (
          <div
            className="absolute inset-0 opacity-[0.03]"
            style={{
              backgroundImage:
                "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
              backgroundSize: "128px 128px",
            }}
          />
        )}

        {/* Watermark indicator */}
        {isProtected && (
          <div className="absolute bottom-3 right-3 flex items-center gap-1.5 rounded-full bg-green-600/90 px-2.5 py-1 text-[10px] font-medium text-white">
            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
            Protected
          </div>
        )}
      </div>

      {/* Label */}
      <div className="absolute left-3 top-3 rounded-full bg-black/60 px-2.5 py-1 text-[10px] font-medium text-white">
        {label}
      </div>
    </div>
  );
}

export function BeforeAfterDemo() {
  const [activeIdx, setActiveIdx] = useState(0);
  const sample = SAMPLES[activeIdx];

  return (
    <div className="space-y-6">
      {/* Sample selector */}
      <div className="flex justify-center gap-2">
        {SAMPLES.map((s, i) => (
          <button
            key={s.id}
            onClick={() => setActiveIdx(i)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              i === activeIdx
                ? "bg-primary text-primary-foreground"
                : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Side-by-side comparison */}
      <div className="grid gap-6 sm:grid-cols-2">
        <DemoCanvas label="Before（無保護）" isProtected={false} />
        <DemoCanvas label="After（保護済み）" isProtected={true} />
      </div>

      {/* Description */}
      <p className="text-center text-sm text-muted-foreground">
        {sample.description}
      </p>

      {/* Protection details */}
      <div className="mx-auto grid max-w-2xl gap-3 sm:grid-cols-3">
        <div className="rounded-lg border bg-white p-3 text-center dark:bg-zinc-900">
          <p className="text-xs font-medium text-blue-600 dark:text-blue-400">
            PixelSeal
          </p>
          <p className="mt-1 text-lg font-bold">128-bit</p>
          <p className="text-xs text-muted-foreground">不可視透かし</p>
        </div>
        <div className="rounded-lg border bg-white p-3 text-center dark:bg-zinc-900">
          <p className="text-xs font-medium text-purple-600 dark:text-purple-400">
            Mist v2
          </p>
          <p className="mt-1 text-lg font-bold">&#949;=8</p>
          <p className="text-xs text-muted-foreground">敵対的摂動</p>
        </div>
        <div className="rounded-lg border bg-white p-3 text-center dark:bg-zinc-900">
          <p className="text-xs font-medium text-green-600 dark:text-green-400">
            C2PA
          </p>
          <p className="mt-1 text-lg font-bold">ES256</p>
          <p className="text-xs text-muted-foreground">来歴証明署名</p>
        </div>
      </div>
    </div>
  );
}
