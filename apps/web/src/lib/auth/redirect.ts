export type RedirectIssueCode =
  | "site_url_missing"
  | "site_url_invalid"
  | "site_url_localhost"
  | "origin_mismatch";

export type RedirectIssueSeverity = "warning" | "error";

export interface RedirectIssue {
  code: RedirectIssueCode;
  severity: RedirectIssueSeverity;
  message: string;
}

export interface RedirectResolution {
  canProceed: boolean;
  redirectTo: string | null;
  resolvedOrigin: string | null;
  issues: RedirectIssue[];
}

function isLocalhostHost(hostname: string): boolean {
  const normalized = hostname.toLowerCase();
  return (
    normalized === "localhost" ||
    normalized === "127.0.0.1" ||
    normalized === "::1" ||
    normalized === "[::1]"
  );
}

function normalizeOrigin(input: string): string | null {
  try {
    const url = new URL(input);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return null;
    }
    return `${url.protocol}//${url.host}`;
  } catch {
    return null;
  }
}

function pushIssue(
  issues: RedirectIssue[],
  code: RedirectIssueCode,
  severity: RedirectIssueSeverity,
  message: string
): void {
  issues.push({ code, severity, message });
}

export function resolveAuthRedirectUrl(
  currentOrigin: string,
  siteUrlRaw: string | undefined = process.env.NEXT_PUBLIC_SITE_URL,
  nodeEnv: string | undefined = process.env.NODE_ENV
): RedirectResolution {
  const issues: RedirectIssue[] = [];
  const isProduction = nodeEnv === "production";

  const normalizedCurrentOrigin = normalizeOrigin(currentOrigin);
  const trimmedSiteUrl = siteUrlRaw?.trim();
  const normalizedSiteOrigin = trimmedSiteUrl ? normalizeOrigin(trimmedSiteUrl) : null;

  if (!trimmedSiteUrl) {
    pushIssue(
      issues,
      "site_url_missing",
      isProduction ? "error" : "warning",
      "NEXT_PUBLIC_SITE_URL が未設定です。"
    );
  } else if (!normalizedSiteOrigin) {
    pushIssue(
      issues,
      "site_url_invalid",
      "error",
      "NEXT_PUBLIC_SITE_URL がURLとして不正です。"
    );
  }

  if (normalizedSiteOrigin) {
    try {
      const host = new URL(normalizedSiteOrigin).hostname;
      if (isLocalhostHost(host)) {
        pushIssue(
          issues,
          "site_url_localhost",
          isProduction ? "error" : "warning",
          "NEXT_PUBLIC_SITE_URL に localhost 系の値が設定されています。"
        );
      }
    } catch {
      // covered by invalid URL check above
    }
  }

  if (isProduction && normalizedSiteOrigin && normalizedCurrentOrigin) {
    if (normalizedCurrentOrigin !== normalizedSiteOrigin) {
      pushIssue(
        issues,
        "origin_mismatch",
        "error",
        "現在のURLと NEXT_PUBLIC_SITE_URL が一致していません。"
      );
    }
  }

  const hasError = issues.some((issue) => issue.severity === "error");
  const resolvedOrigin = normalizedSiteOrigin ?? normalizedCurrentOrigin;

  return {
    canProceed: !hasError && Boolean(resolvedOrigin),
    redirectTo: !hasError && resolvedOrigin ? `${resolvedOrigin}/auth/callback` : null,
    resolvedOrigin,
    issues,
  };
}
