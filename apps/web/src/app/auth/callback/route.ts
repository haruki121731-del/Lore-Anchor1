import { NextResponse } from "next/server";
import { getSupabaseServer } from "@/lib/supabase/server";

function normalizeCallbackErrorCode(errorRaw: string, descriptionRaw: string): string {
  const lower = `${errorRaw} ${descriptionRaw}`.toLowerCase();
  if (lower.includes("provider is not enabled") || lower.includes("unsupported provider")) {
    return "oauth_provider_disabled";
  }
  if (lower.includes("redirect") && lower.includes("allow")) {
    return "invalid_callback";
  }
  if (lower.includes("missing oauth code")) {
    return "invalid_callback";
  }
  return "auth_failed";
}

function sanitizeNextPath(nextRaw: string | null): string {
  if (!nextRaw) return "/dashboard";
  if (!nextRaw.startsWith("/")) return "/dashboard";
  if (nextRaw.startsWith("//")) return "/dashboard";
  return nextRaw;
}

function buildLoginErrorUrl(origin: string, error: string, description?: string): string {
  const url = new URL("/login", origin);
  url.searchParams.set("error", error);
  if (description) {
    url.searchParams.set("error_description", description);
  }
  return url.toString();
}

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);

  const oauthError = searchParams.get("error") ?? "";
  const oauthErrorDescription = searchParams.get("error_description") ?? "";
  if (oauthError) {
    const code = normalizeCallbackErrorCode(oauthError, oauthErrorDescription);
    return NextResponse.redirect(
      buildLoginErrorUrl(origin, code, oauthErrorDescription || oauthError)
    );
  }

  const code = searchParams.get("code");
  const next = sanitizeNextPath(searchParams.get("next"));

  if (code) {
    const supabase = await getSupabaseServer();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }

    const normalized = normalizeCallbackErrorCode("auth_failed", error.message);
    return NextResponse.redirect(
      buildLoginErrorUrl(origin, normalized, error.message)
    );
  }

  return NextResponse.redirect(
    buildLoginErrorUrl(origin, "invalid_callback", "Missing OAuth code")
  );
}
