import Link from "next/link";
import { BeforeAfterDemo } from "@/components/before-after-demo";
import { Button } from "@/components/ui/button";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950">
      {/* ── Header ── */}
      <header className="border-b bg-white/80 backdrop-blur dark:bg-zinc-950/80">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-lg font-bold tracking-tight">Lore Anchor</span>
          <div className="flex items-center gap-3">
            <Link href="/login">
              <Button variant="ghost" size="sm">
                Log in
              </Button>
            </Link>
            <Link href="/login">
              <Button size="sm">Get Started</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="mx-auto max-w-4xl px-6 py-20 text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          AI学習から
          <span className="text-primary"> あなたの作品を守る</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          不可視透かし・敵対的摂動・来歴証明の三層防御で、
          画像生成AIによる無断学習からクリエイターの著作権を保護します。
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <Link href="/login">
            <Button size="lg">無料で始める</Button>
          </Link>
          <a href="#demo">
            <Button variant="outline" size="lg">
              デモを見る
            </Button>
          </a>
        </div>
      </section>

      {/* ── Before / After Demo (#34) ── */}
      <section id="demo" className="border-y bg-zinc-50 dark:bg-zinc-900">
        <div className="mx-auto max-w-5xl px-6 py-16">
          <h2 className="mb-2 text-center text-2xl font-bold">
            保護前 vs 保護後
          </h2>
          <p className="mx-auto mb-10 max-w-xl text-center text-muted-foreground">
            見た目はほぼ同じ。しかしAI学習モデルは保護済み画像から
            正しく学習できなくなります。
          </p>
          <BeforeAfterDemo />
        </div>
      </section>

      {/* ── 三層防御の仕組み ── */}
      <section className="mx-auto max-w-5xl px-6 py-16">
        <h2 className="mb-10 text-center text-2xl font-bold">
          三層防御パイプライン
        </h2>
        <div className="grid gap-8 md:grid-cols-3">
          <div className="rounded-xl border p-6">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900">
              <svg
                className="h-6 w-6 text-blue-600 dark:text-blue-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
            </div>
            <h3 className="mb-2 font-semibold">PixelSeal</h3>
            <p className="text-sm text-muted-foreground">
              128-bit DWTスペクトラム拡散による不可視透かし。
              肉眼では見えないが、いつでも検証可能な所有権証明を画像に埋め込みます。
            </p>
          </div>
          <div className="rounded-xl border p-6">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-900">
              <svg
                className="h-6 w-6 text-purple-600 dark:text-purple-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
            </div>
            <h3 className="mb-2 font-semibold">Mist v2</h3>
            <p className="text-sm text-muted-foreground">
              VAE潜在空間へのPGD攻撃による敵対的摂動。
              AIモデルが画像の特徴を正しく学習することを妨害します。
            </p>
          </div>
          <div className="rounded-xl border p-6">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900">
              <svg
                className="h-6 w-6 text-green-600 dark:text-green-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>
            <h3 className="mb-2 font-semibold">C2PA</h3>
            <p className="text-sm text-muted-foreground">
              Content Credentials準拠の来歴証明署名。
              「AI学習禁止」のメタデータを暗号学的に記録します。
            </p>
          </div>
        </div>
      </section>

      {/* ── 競合比較 ── */}
      <section className="border-y bg-zinc-50 dark:bg-zinc-900">
        <div className="mx-auto max-w-4xl px-6 py-16">
          <h2 className="mb-10 text-center text-2xl font-bold">他ツールとの比較</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="pb-3 text-left font-medium">機能</th>
                  <th className="pb-3 text-center font-medium">Lore Anchor</th>
                  <th className="pb-3 text-center font-medium text-muted-foreground">
                    Glaze
                  </th>
                  <th className="pb-3 text-center font-medium text-muted-foreground">
                    Nightshade
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                <tr>
                  <td className="py-3">敵対的摂動</td>
                  <td className="py-3 text-center text-green-600">&#10003;</td>
                  <td className="py-3 text-center text-green-600">&#10003;</td>
                  <td className="py-3 text-center text-green-600">&#10003;</td>
                </tr>
                <tr>
                  <td className="py-3">不可視透かし（所有権証明）</td>
                  <td className="py-3 text-center text-green-600">&#10003;</td>
                  <td className="py-3 text-center text-red-500">&#10007;</td>
                  <td className="py-3 text-center text-red-500">&#10007;</td>
                </tr>
                <tr>
                  <td className="py-3">C2PA来歴証明</td>
                  <td className="py-3 text-center text-green-600">&#10003;</td>
                  <td className="py-3 text-center text-red-500">&#10007;</td>
                  <td className="py-3 text-center text-red-500">&#10007;</td>
                </tr>
                <tr>
                  <td className="py-3">ブラウザ完結（インストール不要）</td>
                  <td className="py-3 text-center text-green-600">&#10003;</td>
                  <td className="py-3 text-center text-red-500">&#10007;</td>
                  <td className="py-3 text-center text-red-500">&#10007;</td>
                </tr>
                <tr>
                  <td className="py-3">無料プラン</td>
                  <td className="py-3 text-center text-green-600">5枚/月</td>
                  <td className="py-3 text-center text-green-600">&#10003;</td>
                  <td className="py-3 text-center text-green-600">&#10003;</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ── Pricing ── */}
      <section id="pricing" className="mx-auto max-w-4xl px-6 py-16">
        <h2 className="mb-10 text-center text-2xl font-bold">料金プラン</h2>
        <div className="grid gap-6 md:grid-cols-2">
          {/* Free */}
          <div className="rounded-xl border p-6">
            <h3 className="text-lg font-semibold">Free</h3>
            <p className="mt-1 text-3xl font-bold">
              ¥0<span className="text-base font-normal text-muted-foreground">/月</span>
            </p>
            <ul className="mt-6 space-y-3 text-sm text-muted-foreground">
              <li className="flex items-center gap-2">
                <span className="text-green-600">&#10003;</span> 月5枚まで保護
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-600">&#10003;</span> 三層防御
                （PixelSeal + Mist + C2PA）
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-600">&#10003;</span> CPU処理
              </li>
            </ul>
            <Link href="/login" className="mt-6 block">
              <Button variant="outline" className="w-full">
                無料で始める
              </Button>
            </Link>
          </div>
          {/* Pro */}
          <div className="rounded-xl border-2 border-primary p-6">
            <div className="mb-2 inline-block rounded-full bg-primary px-3 py-0.5 text-xs font-medium text-primary-foreground">
              おすすめ
            </div>
            <h3 className="text-lg font-semibold">Pro</h3>
            <p className="mt-1 text-3xl font-bold">
              ¥980<span className="text-base font-normal text-muted-foreground">/月</span>
            </p>
            <ul className="mt-6 space-y-3 text-sm text-muted-foreground">
              <li className="flex items-center gap-2">
                <span className="text-green-600">&#10003;</span> 無制限の画像保護
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-600">&#10003;</span> 三層防御
                （PixelSeal + Mist + C2PA）
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-600">&#10003;</span> GPU高速処理（~5秒）
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-600">&#10003;</span> 優先サポート
              </li>
            </ul>
            <Link href="/login" className="mt-6 block">
              <Button className="w-full">Proを始める</Button>
            </Link>
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="border-t bg-zinc-50 dark:bg-zinc-900">
        <div className="mx-auto max-w-4xl px-6 py-16 text-center">
          <h2 className="text-2xl font-bold">
            今すぐあなたの作品を守りましょう
          </h2>
          <p className="mt-4 text-muted-foreground">
            登録は30秒。メールアドレスだけで始められます。
          </p>
          <Link href="/login" className="mt-6 inline-block">
            <Button size="lg">無料アカウントを作成</Button>
          </Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t">
        <div className="mx-auto max-w-6xl px-6 py-8 text-center text-sm text-muted-foreground">
          &copy; {new Date().getFullYear()} Lore Anchor. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
