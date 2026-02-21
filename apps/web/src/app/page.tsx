import Link from "next/link";
import { getSupabaseServer } from "@/lib/supabase/server";

export default async function Home() {
  let ctaHref = "/login";
  let ctaLabel = "無料ベータを試す";

  try {
    const supabase = await getSupabaseServer();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (user) {
      ctaHref = "/dashboard";
      ctaLabel = "ダッシュボードへ";
    }
  } catch {
    // Supabase env is not configured in some local contexts.
  }

  return (
    <main className="landing-shell">
      <section className="landing-hero">
        <p className="landing-eyebrow">Private Beta</p>
        <h1 className="landing-title">画像を守る。権利を証明する。</h1>
        <p className="landing-subtitle">
          Lore Anchor は、PixelSeal・Mist v2・C2PA の三層防御で、
          クリエイターの作品をAI無断学習から守ります。
        </p>
        <div className="landing-cta-row">
          <Link href={ctaHref} className="landing-cta-primary">
            {ctaLabel}
          </Link>
          <Link href="/login" className="landing-cta-secondary">
            ログイン
          </Link>
        </div>
      </section>

      <section className="landing-grid">
        <article className="landing-card">
          <h2>1. アップロード</h2>
          <p>
            PNG / JPEG / WebP（20MBまで）をアップロード。すぐに保護ジョブが開始します。
          </p>
        </article>
        <article className="landing-card">
          <h2>2. 保護処理</h2>
          <p>
            PixelSeal → Mist v2 → C2PA の順で処理。処理状況はダッシュボードで追跡できます。
          </p>
        </article>
        <article className="landing-card">
          <h2>3. ダウンロード</h2>
          <p>
            完了後すぐに保護済み画像を取得。来歴情報と透かし情報を保持します。
          </p>
        </article>
      </section>
    </main>
  );
}
