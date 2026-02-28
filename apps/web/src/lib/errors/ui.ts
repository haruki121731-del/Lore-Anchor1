export type UiErrorCategory = "auth" | "network" | "config" | "server" | "unknown";

export type UiError = {
  message: string;
  detail?: string;
  category: UiErrorCategory;
};

type NormalizeContext = "auth" | "upload" | "dashboard" | "processing" | "generic";

function toDetail(error: unknown): string | undefined {
  if (!error) return undefined;
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  try {
    return JSON.stringify(error);
  } catch {
    return String(error);
  }
}

function isAuthIssue(detail: string): boolean {
  return (
    detail.includes("no active session") ||
    detail.includes("no_session") ||
    detail.includes("401") ||
    detail.includes("unauthorized") ||
    detail.includes("invalid or expired token") ||
    detail.includes("missing bearer token") ||
    detail.includes("refresh_failed") ||
    detail.includes("jwt")
  );
}

function isNetworkIssue(detail: string): boolean {
  return (
    detail.includes("network error") ||
    detail.includes("failed to fetch") ||
    detail.includes("fetch failed") ||
    detail.includes("connection") ||
    detail.includes("timeout")
  );
}

function isConfigIssue(detail: string): boolean {
  return (
    detail.includes("provider is not enabled") ||
    detail.includes("unsupported provider") ||
    detail.includes("redirect") ||
    detail.includes("site_url") ||
    detail.includes("supabase env vars not set") ||
    detail.includes("invalid_callback")
  );
}

export function normalizeUiError(
  error: unknown,
  context: NormalizeContext = "generic"
): UiError {
  const detail = toDetail(error);
  const lower = detail?.toLowerCase() ?? "";

  if (isAuthIssue(lower)) {
    return {
      category: "auth",
      message: "ログインが必要です。もう一度ログインしてください。",
      detail,
    };
  }

  if (isNetworkIssue(lower)) {
    return {
      category: "network",
      message: "通信に失敗しました。通信環境を確認してください。",
      detail,
    };
  }

  if (isConfigIssue(lower)) {
    return {
      category: "config",
      message: "ログイン設定に問題があります。管理者へ連絡してください。",
      detail,
    };
  }

  const statusMatch = lower.match(/\b([45]\d{2})\b/);
  if (statusMatch && statusMatch[1].startsWith("5")) {
    return {
      category: "server",
      message: "処理に失敗しました。少し待って再試行してください。",
      detail,
    };
  }

  if (context === "processing" || context === "upload" || context === "dashboard") {
    return {
      category: "server",
      message: "処理に失敗しました。少し待って再試行してください。",
      detail,
    };
  }

  return {
    category: "unknown",
    message: "エラーが発生しました。少し待って再試行してください。",
    detail,
  };
}
