import { NextResponse } from "next/server";
import { getSupabaseServer } from "@/lib/supabase/server";

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

  const oauthError = searchParams.get("error");
  const oauthErrorDescription = searchParams.get("error_description");
  if (oauthError) {
    return NextResponse.redirect(
      buildLoginErrorUrl(origin, oauthError, oauthErrorDescription ?? undefined)
    );
  }

  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? "/dashboard";

  if (code) {
    const supabase = await getSupabaseServer();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }

    return NextResponse.redirect(
      buildLoginErrorUrl(origin, "auth_failed", error.message)
    );
  }

  return NextResponse.redirect(
    buildLoginErrorUrl(origin, "auth_failed", "Missing OAuth code")
  );
}
