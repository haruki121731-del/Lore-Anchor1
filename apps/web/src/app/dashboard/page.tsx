"use client";

import { useState } from "react";
import { LogoutButton } from "@/components/logout-button";
import { ImageUploader } from "@/components/image-uploader";
import { ImageList } from "@/components/image-list";

export default function DashboardPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="dashboard-shell min-h-screen">
      <header className="border-b border-white/10 bg-slate-950/70 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-cyan-300/80">Private Beta</p>
            <h1 className="text-xl font-semibold text-white">Lore Anchor Dashboard</h1>
          </div>
          <LogoutButton />
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-6 px-6 py-8 md:grid-cols-[1.2fr_2fr]">
        <section className="rounded-2xl border border-white/10 bg-slate-900/70 p-5 shadow-2xl shadow-slate-950/30">
          <h2 className="text-lg font-semibold text-white">アップロード</h2>
          <p className="mt-1 text-sm text-slate-300">
            画像をアップロードすると、保護処理が自動でキューに追加されます。
          </p>
          <ImageUploader
            onUploadComplete={() => setRefreshKey((k) => k + 1)}
          />
        </section>

        <section className="rounded-2xl border border-white/10 bg-slate-900/70 p-5 shadow-2xl shadow-slate-950/30">
          <h2 className="text-lg font-semibold text-white">ジョブ状況</h2>
          <p className="mt-1 text-sm text-slate-300">
            pending / processing / completed / failed をリアルタイムで追跡できます。
          </p>
          <ImageList refreshKey={refreshKey} />
        </section>
      </main>
    </div>
  );
}
