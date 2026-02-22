"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { getSupabaseClient } from "@/lib/supabase/client";
import {
  resolveAuthRedirectUrl,
  type RedirectIssue,
  type RedirectResolution,
} from "@/lib/auth/redirect";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type AuthSettingsResponse = {
  external?: Record<string, boolean>;
};

function mapAuthError(errorParam: string | null, errorDescription: string | null): string | null {
  if (!errorParam && !errorDescription) return null;

  const error = (errorParam ?? "").toLowerCase();
  const raw = `${errorParam ?? ""} ${errorDescription ?? ""}`.toLowerCase();

  if (error === "oauth_provider_disabled") {
    return "Googleログインが無効です。管理者が Supabase の Google Provider を有効化してください。";
  }
  if (error === "invalid_callback") {
    return "認証コールバックURLが不正です。デプロイ環境のURL設定を確認してください。";
  }
  if (raw.includes("provider is not enabled") || raw.includes("unsupported provider")) {
    return "Googleログインが無効です。管理者が Supabase の Google Provider を有効化してください。";
  }
  if (raw.includes("redirect") && raw.includes("allow")) {
    return "認証リダイレクトURLが許可されていません。Supabase の Redirect URL 設定を確認してください。";
  }
  if (raw.includes("access_denied")) {
    return "認証がキャンセルされました。もう一度お試しください。";
  }
  return "認証に失敗しました。時間をおいて再度お試しください。";
}

function mapSupabaseError(messageText: string): string {
  const lower = messageText.toLowerCase();
  if (lower.includes("invalid email")) return "メールアドレスの形式が正しくありません。";
  if (lower.includes("email provider") && lower.includes("disabled")) {
    return "メール認証が無効です。管理者が Supabase の Email Provider を有効化してください。";
  }
  if (lower.includes("provider is not enabled") || lower.includes("unsupported provider")) {
    return "Googleログインが無効です。管理者が Supabase の Google Provider を有効化してください。";
  }
  if (lower.includes("redirect") && lower.includes("allow")) {
    return "認証リダイレクトURLが許可されていません。環境変数 NEXT_PUBLIC_SITE_URL と Supabase 設定を確認してください。";
  }
  if (lower.includes("rate")) return "試行回数が多すぎます。少し待ってから再度お試しください。";
  if (lower.includes("network")) return "ネットワークエラーが発生しました。接続を確認してください。";
  return "認証に失敗しました。時間をおいて再度お試しください。";
}

function sanitizeNextPath(nextRaw: string | null): string {
  if (!nextRaw) return "/dashboard";
  if (!nextRaw.startsWith("/")) return "/dashboard";
  if (nextRaw.startsWith("//")) return "/dashboard";
  if (nextRaw === "/login" || nextRaw.startsWith("/login?")) return "/dashboard";
  if (nextRaw === "/auth/callback" || nextRaw.startsWith("/auth/callback?")) return "/dashboard";
  return nextRaw;
}

function joinIssues(issues: RedirectIssue[]): string {
  return issues.map((issue) => issue.message).join(" ");
}

function LoginPageContent() {
  const searchParams = useSearchParams();
  const authError = mapAuthError(
    searchParams.get("error"),
    searchParams.get("error_description")
  );
  const nextPath = useMemo(() => sanitizeNextPath(searchParams.get("next")), [searchParams]);

  const [email, setEmail] = useState("");
  const [loadingEmail, setLoadingEmail] = useState(false);
  const [loadingGoogle, setLoadingGoogle] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [googleEnabled, setGoogleEnabled] = useState(true);
  const [emailEnabled, setEmailEnabled] = useState(true);

  const [resolution, setResolution] = useState<RedirectResolution | null>(null);

  const warningIssues = useMemo(
    () => resolution?.issues.filter((issue) => issue.severity === "warning") ?? [],
    [resolution]
  );
  const errorIssues = useMemo(
    () => resolution?.issues.filter((issue) => issue.severity === "error") ?? [],
    [resolution]
  );

  useEffect(() => {
    const current = window.location.origin;
    setResolution(resolveAuthRedirectUrl(current));
  }, []);

  useEffect(() => {
    async function loadAuthSettings() {
      const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
      const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
      if (!supabaseUrl || !anonKey) return;

      try {
        const res = await fetch(`${supabaseUrl}/auth/v1/settings`, {
          headers: { apikey: anonKey },
          cache: "no-store",
        });
        if (!res.ok) return;

        const json = (await res.json()) as AuthSettingsResponse;
        const external = json.external;
        if (!external) return;

        if (typeof external.google === "boolean") {
          setGoogleEnabled(external.google);
        }
        if (typeof external.email === "boolean") {
          setEmailEnabled(external.email);
        }
      } catch {
        // keep defaults if settings fetch fails
      }
    }

    void loadAuthSettings();
  }, []);

  function resolveCallbackOrShowError(): string | null {
    const currentResolution = resolution ?? resolveAuthRedirectUrl(window.location.origin);
    if (!resolution) setResolution(currentResolution);

    if (!currentResolution.canProceed || !currentResolution.redirectTo) {
      setErrorMessage(
        joinIssues(
          currentResolution.issues.filter((issue) => issue.severity === "error")
        ) || "認証設定が不正です。管理者に連絡してください。"
      );
      return null;
    }

    try {
      const callbackUrl = new URL(currentResolution.redirectTo);
      callbackUrl.searchParams.set("next", nextPath);
      return callbackUrl.toString();
    } catch {
      return currentResolution.redirectTo;
    }
  }

  async function handleEmailLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoadingEmail(true);
    setMessage(null);
    setErrorMessage(null);

    if (!emailEnabled) {
      setErrorMessage("メール認証が無効です。管理者へご連絡ください。");
      setLoadingEmail(false);
      return;
    }

    const callback = resolveCallbackOrShowError();
    if (!callback) {
      setLoadingEmail(false);
      return;
    }

    const supabase = getSupabaseClient();
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: callback },
    });

    if (error) {
      setErrorMessage(mapSupabaseError(error.message));
    } else {
      setMessage("ログインリンクを送信しました。受信箱と迷惑メールをご確認ください。");
    }
    setLoadingEmail(false);
  }

  async function handleGoogleLogin() {
    setLoadingGoogle(true);
    setMessage(null);
    setErrorMessage(null);

    if (!googleEnabled) {
      setErrorMessage("Googleログインは現在無効です。メールリンクをご利用ください。");
      setLoadingGoogle(false);
      return;
    }

    const callback = resolveCallbackOrShowError();
    if (!callback) {
      setLoadingGoogle(false);
      return;
    }

    try {
      const supabase = getSupabaseClient();
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: callback },
      });
      if (error) {
        setErrorMessage(mapSupabaseError(error.message));
      }
    } catch {
      setErrorMessage("ネットワークエラーが発生しました。接続を確認してください。");
    } finally {
      setLoadingGoogle(false);
    }
  }

  return (
    <div className="auth-shell">
      <Card className="auth-card w-full max-w-lg">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl">Lore Anchor ベータ</CardTitle>
          <CardDescription>
            ログイン後に、画像保護パイプラインをそのまま体験できます。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {authError && (
            <div className="rounded-md border border-rose-300/40 bg-rose-100/50 p-3 dark:bg-rose-900/20">
              <p className="text-center text-sm text-rose-700 dark:text-rose-200">{authError}</p>
            </div>
          )}

          {warningIssues.length > 0 && (
            <div className="rounded-md border border-amber-300/40 bg-amber-100/40 p-3 dark:bg-amber-900/20">
              <p className="text-center text-xs text-amber-800 dark:text-amber-200">
                {joinIssues(warningIssues)}
              </p>
            </div>
          )}

          {errorIssues.length > 0 && (
            <div className="rounded-md border border-rose-300/40 bg-rose-100/50 p-3 dark:bg-rose-900/20">
              <p className="text-center text-xs text-rose-700 dark:text-rose-200">
                {joinIssues(errorIssues)}
              </p>
            </div>
          )}

          <div className="rounded-xl border border-cyan-400/30 bg-cyan-500/10 p-4 text-sm">
            <p className="font-semibold text-cyan-900 dark:text-cyan-100">ログイン方法</p>
            <ul className="mt-2 list-disc pl-5 text-cyan-900/80 dark:text-cyan-100/80">
              <li>Google: ワンクリックですぐ開始</li>
              <li>メールリンク: パスワード不要で安全にログイン</li>
            </ul>
          </div>

          {!googleEnabled && (
            <p className="text-center text-xs text-amber-700 dark:text-amber-300">
              Googleログインは現在無効です（Supabase設定）。
            </p>
          )}

          {!emailEnabled && (
            <p className="text-center text-xs text-amber-700 dark:text-amber-300">
              メール認証は現在無効です（Supabase設定）。
            </p>
          )}

          <form onSubmit={handleEmailLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <Button
              type="submit"
              className="w-full"
              disabled={loadingEmail || !emailEnabled || errorIssues.length > 0}
            >
              {loadingEmail ? "送信中..." : "メールリンクを送信"}
            </Button>
          </form>

          {errorMessage && (
            <p className="text-center text-sm text-rose-600 dark:text-rose-300">
              {errorMessage}
            </p>
          )}

          {message && (
            <p className="text-center text-sm text-emerald-700 dark:text-emerald-300">{message}</p>
          )}

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">または</span>
            </div>
          </div>

          <Button
            variant="outline"
            className="w-full"
            disabled={loadingGoogle || !googleEnabled || errorIssues.length > 0}
            onClick={handleGoogleLogin}
          >
            <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                fill="#4285F4"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#34A853"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                fill="#FBBC05"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              />
            </svg>
            {loadingGoogle ? "Googleへ接続中..." : "Googleでログイン"}
          </Button>

          <p className="text-center text-xs text-zinc-500">
            ログイン後は <strong>1枚アップロード</strong> して保護完了までご確認ください。
          </p>

          <div className="text-center">
            <Link className="text-sm text-cyan-700 underline dark:text-cyan-300" href="/">
              トップページへ戻る
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginPageContent />
    </Suspense>
  );
}
