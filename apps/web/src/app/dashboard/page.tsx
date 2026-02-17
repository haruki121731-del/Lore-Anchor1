"use client";

import { useState } from "react";
import { LogoutButton } from "@/components/logout-button";
import { ImageUploader } from "@/components/image-uploader";
import { ImageList } from "@/components/image-list";

export default function DashboardPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <header className="border-b bg-white dark:bg-zinc-900">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
          <h1 className="text-lg font-semibold">Lore Anchor</h1>
          <LogoutButton />
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-8 px-6 py-8">
        <section>
          <h2 className="mb-4 text-lg font-medium">Upload Image</h2>
          <ImageUploader
            onUploadComplete={() => setRefreshKey((k) => k + 1)}
          />
        </section>

        <section>
          <h2 className="mb-4 text-lg font-medium">Your Images</h2>
          <ImageList refreshKey={refreshKey} />
        </section>
      </main>
    </div>
  );
}
