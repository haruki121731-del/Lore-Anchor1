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
import { normalizeUiError, type UiError } from "@/lib/errors/ui";

type AuthSettingsResponse = {
  external?: Record<string, boolean>;
};

function sanitizeNextPath(nextRaw: string | null): string {
  if (!nextRaw) return "/";
  if (!nextRaw.startsWith("/")) return "/";
  if (nextRaw.startsWith("//")) return "/";
  if (nextRaw === "/login" || nextRaw.startsWith("/login?")) return "/";
  if (nextRaw === "/auth/callback" || nextRaw.startsWith("/auth/callback?")) return "/";
  return nextRaw;
}

function joinIssues(issues: RedirectIssue[]): string {
  return issues.map((issue) => issue.message).join(" ");
}

function mapAuthQueryError(errorParam: string | null, description: string | null): UiError | null {
  if (!errorParam && !description) return null;

  const error = (errorParam ?? "").toLowerCase();
  const raw = `${errorParam ?? ""} ${description ?? ""}`.toLowerCase();

  if (error === "oauth_provider_disabled" || raw.includes("provider is not enabled")) {
    return {
      category: "config",
      message: "Googleログインが使えません。管理者へ連絡してください。",
      detail: description ?? errorParam ?? undefined,
    };
  }

  if (error === "invalid_callback" || (raw.includes("redirect") && raw.includes("allow"))) {
    return {
      category: "config",
      message: "ログイン設定に問題があります。管理者へ連絡してください。",
      detail: description ?? errorParam ?? undefined,
    };
  }

  if (raw.includes("access_denied")) {
    return {
      category: "auth",
      message: "ログインがキャンセルされました。もう一度お試しください。",
      detail: description ?? errorParam ?? undefined,
    };
  }

  return {
    category: "auth",
    message: "ログインに失敗しました。もう一度お試しください。",
    detail: description ?? errorParam ?? undefined,
  };
}

function ErrorNotice({ error }: { error: UiError }) {
  return (
    <div className="rounded-[16px] border border-[#FCA5A5] bg-[#FEF2F2] px-[16px] py-[12px] text-[#991B1B]">
      <p className="text-[14px] font-semibold leading-[1.45]">{error.message}</p>
      {error.detail && (
        <details className="mt-[6px] text-[12px] leading-[1.4] text-[#B91C1C]">
          <summary className="cursor-pointer">くわしい情報</summary>
          <p className="mt-[4px] break-words">{error.detail}</p>
        </details>
      )}
    </div>
  );
}

function LoginPageContent() {
  const searchParams = useSearchParams();
  const nextPath = useMemo(() => sanitizeNextPath(searchParams.get("next")), [searchParams]);
  const queryError = useMemo(
    () => mapAuthQueryError(searchParams.get("error"), searchParams.get("error_description")),
    [searchParams]
  );

  const [email, setEmail] = useState("");
  const [showEmailForm, setShowEmailForm] = useState(false);
  const [busyAction, setBusyAction] = useState<"google" | "email" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [uiError, setUiError] = useState<UiError | null>(null);

  const [googleEnabled, setGoogleEnabled] = useState(true);
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [resolution, setResolution] = useState<RedirectResolution | null>(null);

  const warningIssues = useMemo(
    () => resolution?.issues.filter((issue) => issue.severity === "warning") ?? [],
    [resolution]
  );
  const blockingIssues = useMemo(
    () => resolution?.issues.filter((issue) => issue.severity === "error") ?? [],
    [resolution]
  );

  const blockingError = useMemo<UiError | null>(() => {
    if (blockingIssues.length === 0) return null;
    return {
      category: "config",
      message: "ログイン設定に問題があります。管理者へ連絡してください。",
      detail: joinIssues(blockingIssues),
    };
  }, [blockingIssues]);

  useEffect(() => {
    setResolution(resolveAuthRedirectUrl(window.location.origin));
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
        if (!json.external) return;

        if (typeof json.external.google === "boolean") {
          setGoogleEnabled(json.external.google);
        }
        if (typeof json.external.email === "boolean") {
          setEmailEnabled(json.external.email);
        }
      } catch (error) {
        console.error("[login] failed to load auth settings", error);
      }
    }

    void loadAuthSettings();
  }, []);

  function resolveCallbackOrShowError(): string | null {
    const currentResolution = resolution ?? resolveAuthRedirectUrl(window.location.origin);
    if (!resolution) {
      setResolution(currentResolution);
    }

    if (!currentResolution.canProceed || !currentResolution.redirectTo) {
      setUiError({
        category: "config",
        message: "ログイン設定に問題があります。管理者へ連絡してください。",
        detail:
          joinIssues(currentResolution.issues.filter((issue) => issue.severity === "error")) ||
          "認証設定が不正です。",
      });
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

  async function handleEmailLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setUiError(null);
    setBusyAction("email");

    if (!emailEnabled) {
      setUiError({
        category: "config",
        message: "メールログインが使えません。管理者へ連絡してください。",
      });
      setBusyAction(null);
      return;
    }

    const callback = resolveCallbackOrShowError();
    if (!callback) {
      setBusyAction(null);
      return;
    }

    try {
      const supabase = getSupabaseClient();
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: callback },
      });

      if (error) {
        throw error;
      }

      setMessage("メールを送りました。メールのボタンを押してください。");
    } catch (error) {
      const normalized = normalizeUiError(error, "auth");
      setUiError(normalized);
      console.error("[login] email auth failed", error);
    } finally {
      setBusyAction(null);
    }
  }

  async function handleGoogleLogin() {
    setMessage(null);
    setUiError(null);
    setBusyAction("google");

    if (!googleEnabled) {
      setUiError({
        category: "config",
        message: "Googleログインが使えません。管理者へ連絡してください。",
      });
      setBusyAction(null);
      return;
    }

    const callback = resolveCallbackOrShowError();
    if (!callback) {
      setBusyAction(null);
      return;
    }

    try {
      const supabase = getSupabaseClient();
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: callback },
      });
      if (error) {
        throw error;
      }
    } catch (error) {
      const normalized = normalizeUiError(error, "auth");
      setUiError(normalized);
      console.error("[login] google auth failed", error);
      setBusyAction(null);
    }
  }

  const shouldDisableActions = blockingIssues.length > 0;

  return (
    <main className="flex min-h-screen w-full items-center justify-center px-[16px] py-[32px] bg-gradient-to-b from-[#F8FAFC] to-[#FFFFFF]">
      <section className="w-full max-w-[560px] rounded-[28px] border border-[#E5E7EB] bg-[rgba(255,255,255,0.86)] px-[20px] py-[28px] shadow-[0_18px_44px_rgba(15,23,42,0.08)] backdrop-blur-[10px] md:px-[32px] md:py-[36px]">
        <p className="text-[11px] font-bold tracking-[0.25em] text-[#0D9488]">PRIVATE BETA</p>
        <h1 className="mt-[14px] text-[34px] font-[800] leading-[1.08] tracking-[-0.02em] text-[#111827] md:text-[42px]">
          かんたんログイン
        </h1>
        <p className="mt-[12px] text-[16px] leading-[1.55] text-[#6B7280]">
          ログインしたら、すぐに画像を守れます。
        </p>

        <div className="mt-[18px] rounded-[18px] border border-[#DBEAFE] bg-[#EFF6FF] px-[14px] py-[12px]">
          <p className="text-[13px] font-semibold text-[#1D4ED8]">3ステップ</p>
          <p className="mt-[4px] text-[13px] leading-[1.5] text-[#1E3A8A]">
            1. ログインする → 2. 画像をえらぶ → 3. 保護完了
          </p>
        </div>

        <div className="mt-[16px] space-y-[10px]">
          {queryError && <ErrorNotice error={queryError} />}
          {blockingError && <ErrorNotice error={blockingError} />}
          {uiError && <ErrorNotice error={uiError} />}
        </div>

        {warningIssues.length > 0 && (
          <div className="mt-[12px] rounded-[14px] border border-[#FDE68A] bg-[#FEFCE8] px-[14px] py-[10px] text-[12px] text-[#92400E]">
            <p className="font-semibold">お知らせ</p>
            <p className="mt-[4px] leading-[1.45]">{joinIssues(warningIssues)}</p>
          </div>
        )}

        <button
          type="button"
          className="mt-[22px] h-[64px] w-full rounded-[32px] bg-[#111827] text-[20px] font-bold text-white transition-colors duration-200 hover:bg-[#000000] disabled:cursor-not-allowed disabled:opacity-60"
          disabled={busyAction !== null || shouldDisableActions || !googleEnabled}
          onClick={() => {
            void handleGoogleLogin();
          }}
        >
          {busyAction === "google" ? "つないでいます..." : "Googleでつづける"}
        </button>

        <button
          type="button"
          className="mt-[12px] h-[56px] w-full rounded-[28px] border border-[#D1D5DB] bg-white text-[17px] font-semibold text-[#111827] transition-colors duration-200 hover:bg-[#F9FAFB] disabled:cursor-not-allowed disabled:opacity-60"
          disabled={busyAction !== null || shouldDisableActions || !emailEnabled}
          onClick={() => {
            setShowEmailForm((prev) => !prev);
          }}
        >
          {showEmailForm ? "メール入力をとじる" : "メールでつづける"}
        </button>

        {showEmailForm && (
          <form className="mt-[12px] space-y-[10px]" onSubmit={handleEmailLogin}>
            <label className="block text-[13px] font-semibold text-[#374151]" htmlFor="email">
              メールアドレス
            </label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
              }}
              required
              className="h-[52px] w-full rounded-[16px] border border-[#D1D5DB] px-[14px] text-[16px] outline-none transition-colors focus:border-[#60A5FA]"
            />
            <button
              type="submit"
              disabled={busyAction !== null || shouldDisableActions || !emailEnabled}
              className="h-[54px] w-full rounded-[27px] bg-[#111827] text-[17px] font-semibold text-white transition-colors duration-200 hover:bg-[#000000] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busyAction === "email" ? "送っています..." : "メールを送る"}
            </button>
          </form>
        )}

        {message && (
          <div className="mt-[12px] rounded-[14px] border border-[#86EFAC] bg-[#F0FDF4] px-[14px] py-[10px] text-[14px] font-semibold text-[#166534]">
            {message}
          </div>
        )}

        <div className="mt-[20px] text-center">
          <Link className="text-[14px] font-semibold text-[#2563EB] underline" href="/">
            トップへ戻る
          </Link>
        </div>
      </section>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginPageContent />
    </Suspense>
  );
}
