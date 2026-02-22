import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

function sanitizeNextPath(nextRaw: string | null): string {
  if (!nextRaw) return "/dashboard";
  if (!nextRaw.startsWith("/")) return "/dashboard";
  if (nextRaw.startsWith("//")) return "/dashboard";
  if (nextRaw === "/login" || nextRaw.startsWith("/login?")) return "/dashboard";
  if (nextRaw === "/auth/callback" || nextRaw.startsWith("/auth/callback?")) return "/dashboard";
  return nextRaw;
}

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({ request });

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) {
    return supabaseResponse;
  }

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) =>
          request.cookies.set(name, value)
        );
        supabaseResponse = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          supabaseResponse.cookies.set(name, value, options)
        );
      },
    },
  });

  const {
    data: { user },
  } = await supabase.auth.getUser();

  const isLandingPage = request.nextUrl.pathname === "/";
  const isLoginPage = request.nextUrl.pathname === "/login";
  const isAuthCallback = request.nextUrl.pathname === "/auth/callback";

  if (!user && !isLandingPage && !isLoginPage && !isAuthCallback) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("next", `${request.nextUrl.pathname}${request.nextUrl.search}`);
    return NextResponse.redirect(loginUrl);
  }

  if (user && isLoginPage) {
    const nextPath = sanitizeNextPath(request.nextUrl.searchParams.get("next"));
    return NextResponse.redirect(new URL(nextPath, request.url));
  }

  return supabaseResponse;
}
