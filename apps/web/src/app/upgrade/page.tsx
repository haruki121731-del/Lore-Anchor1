"use client";

import { useState } from "react";
import Link from "next/link";
import { getSupabaseClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function UpgradePage() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleUpgrade() {
    setLoading(true);
    setError(null);

    try {
      const supabase = getSupabaseClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setError("ログインが必要です");
        setLoading(false);
        return;
      }

      const res = await fetch(`${API_BASE}/api/v1/billing/checkout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session.access_token}` },
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(
          body.detail || `Checkout failed (${res.status})`
        );
      }

      const { checkout_url } = await res.json();
      if (checkout_url) {
        window.location.href = checkout_url;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "エラーが発生しました");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <header className="border-b bg-white dark:bg-zinc-900">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
          <Link href="/dashboard" className="text-lg font-semibold">
            Lore Anchor
          </Link>
          <Link href="/dashboard">
            <Button variant="ghost" size="sm">
              ダッシュボードに戻る
            </Button>
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-16">
        <h1 className="text-center text-3xl font-bold">Pro プランにアップグレード</h1>
        <p className="mt-4 text-center text-muted-foreground">
          無制限の画像保護とGPU高速処理をご利用いただけます。
        </p>

        <div className="mt-10 rounded-xl border-2 border-primary bg-white p-8 dark:bg-zinc-900">
          <div className="mb-2 inline-block rounded-full bg-primary px-3 py-0.5 text-xs font-medium text-primary-foreground">
            Pro
          </div>
          <p className="mt-2 text-4xl font-bold">
            ¥980
            <span className="text-base font-normal text-muted-foreground">
              /月（税込）
            </span>
          </p>

          <ul className="mt-6 space-y-3 text-sm">
            <li className="flex items-center gap-2">
              <span className="text-green-600">&#10003;</span> 無制限の画像保護
            </li>
            <li className="flex items-center gap-2">
              <span className="text-green-600">&#10003;</span> GPU高速処理（~5秒/枚）
            </li>
            <li className="flex items-center gap-2">
              <span className="text-green-600">&#10003;</span> 三層防御（PixelSeal + Mist v2 + C2PA）
            </li>
            <li className="flex items-center gap-2">
              <span className="text-green-600">&#10003;</span> 優先サポート
            </li>
          </ul>

          <Button
            className="mt-8 w-full"
            size="lg"
            onClick={handleUpgrade}
            disabled={loading}
          >
            {loading ? "処理中..." : "Proプランを購入する"}
          </Button>

          {error && (
            <p className="mt-4 text-center text-sm text-red-600 dark:text-red-400">
              {error}
            </p>
          )}

          <p className="mt-4 text-center text-xs text-muted-foreground">
            Stripeによる安全な決済。いつでもキャンセル可能。
          </p>
        </div>
      </main>
    </div>
  );
}
