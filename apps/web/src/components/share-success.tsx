"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

interface ShareSuccessProps {
  imageId: string;
}

export function ShareSuccess({ imageId }: ShareSuccessProps) {
  const [copied, setCopied] = useState(false);

  const siteUrl = typeof window !== "undefined" ? window.location.origin : "";
  const referralUrl = `${siteUrl}/?ref=${imageId.slice(0, 8)}`;
  const tweetText = encodeURIComponent(
    "この作品は #LoreAnchor で保護されています。AIによる無断学習から大切なイラストを守ろう！\n"
  );
  const tweetUrl = encodeURIComponent(referralUrl);
  const twitterShareUrl = `https://twitter.com/intent/tweet?text=${tweetText}&url=${tweetUrl}`;

  async function handleCopyLink() {
    try {
      await navigator.clipboard.writeText(referralUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: do nothing
    }
  }

  return (
    <div className="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-900 dark:bg-green-950">
      <div className="flex items-center gap-2">
        <svg
          className="h-5 w-5 text-green-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <p className="text-sm font-medium text-green-800 dark:text-green-200">
          保護が完了しました！
        </p>
      </div>

      <p className="mt-2 text-sm text-green-700 dark:text-green-300">
        SNSで共有して、他のクリエイターにも教えてあげましょう。
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        <a
          href={twitterShareUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          <Button size="sm" className="gap-1.5">
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
            </svg>
            Xで共有する
          </Button>
        </a>

        <Button
          variant="outline"
          size="sm"
          onClick={handleCopyLink}
          className="gap-1.5"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
            />
          </svg>
          {copied ? "コピーしました！" : "紹介リンクをコピー"}
        </Button>
      </div>
    </div>
  );
}
