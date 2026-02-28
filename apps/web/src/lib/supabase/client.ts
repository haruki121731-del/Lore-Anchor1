"use client";

import { createBrowserClient } from "@supabase/ssr";

let client: ReturnType<typeof createBrowserClient> | null = null;
const LOCK_QUEUES = new Map<string, Promise<void>>();

type AccessTokenOptions = {
  forceRefresh?: boolean;
  expiresSoonSeconds?: number;
};

type AccessTokenErrorCode = "NO_SESSION" | "SESSION_FETCH_FAILED" | "REFRESH_FAILED";

export class AccessTokenError extends Error {
  code: AccessTokenErrorCode;

  constructor(code: AccessTokenErrorCode, message: string) {
    super(message);
    this.name = "AccessTokenError";
    this.code = code;
  }
}

function createAcquireTimeoutError(lockName: string, acquireTimeout: number): Error & { isAcquireTimeout: true } {
  const error = new Error(
    `Acquiring process lock "${lockName}" timed out after ${acquireTimeout}ms`
  ) as Error & { isAcquireTimeout: true };
  error.isAcquireTimeout = true;
  return error;
}

async function inProcessLock<R>(
  name: string,
  acquireTimeout: number,
  fn: () => Promise<R>
): Promise<R> {
  const previous = LOCK_QUEUES.get(name) ?? Promise.resolve();

  let releaseCurrent!: () => void;
  const current = new Promise<void>((resolve) => {
    releaseCurrent = resolve;
  });
  const queueTail = previous.catch(() => undefined).then(() => current);
  LOCK_QUEUES.set(name, queueTail);

  const acquire = previous.catch(() => undefined);
  let timeoutId: ReturnType<typeof window.setTimeout> | null = null;
  try {
    if (acquireTimeout >= 0) {
      await Promise.race([
        acquire,
        new Promise<never>((_, reject) => {
          timeoutId = window.setTimeout(() => {
            reject(createAcquireTimeoutError(name, acquireTimeout));
          }, acquireTimeout);
        }),
      ]);
    } else {
      await acquire;
    }

    if (timeoutId !== null) {
      window.clearTimeout(timeoutId);
    }
    return await fn();
  } finally {
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId);
    }
    releaseCurrent();
    void queueTail.finally(() => {
      if (LOCK_QUEUES.get(name) === queueTail) {
        LOCK_QUEUES.delete(name);
      }
    });
  }
}

function isAuthErrorLike(error: unknown): boolean {
  const detail = error instanceof Error ? error.message.toLowerCase() : String(error).toLowerCase();
  return (
    detail.includes("401") ||
    detail.includes("unauthorized") ||
    detail.includes("invalid or expired token") ||
    detail.includes("missing bearer token") ||
    detail.includes("jwt")
  );
}

export function getSupabaseClient() {
  if (client) return client;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) throw new Error("Supabase env vars not set");

  client = createBrowserClient(url, key, {
    auth: {
      lock: inProcessLock,
    },
  });
  return client;
}

export async function getValidAccessToken(options: AccessTokenOptions = {}): Promise<string> {
  const { forceRefresh = false, expiresSoonSeconds = 60 } = options;
  const supabase = getSupabaseClient();
  const {
    data: { session },
    error,
  } = await supabase.auth.getSession();

  if (error) {
    throw new AccessTokenError("SESSION_FETCH_FAILED", error.message);
  }

  if (!session) {
    throw new AccessTokenError("NO_SESSION", "No active session");
  }

  const nowInSeconds = Math.floor(Date.now() / 1000);
  const expiresSoon =
    typeof session.expires_at === "number" &&
    session.expires_at <= nowInSeconds + expiresSoonSeconds;
  const shouldRefresh = forceRefresh || !session.access_token || expiresSoon;

  if (!shouldRefresh) {
    return session.access_token;
  }

  const { data, error: refreshError } = await supabase.auth.refreshSession();
  if (refreshError || !data.session?.access_token) {
    throw new AccessTokenError(
      "REFRESH_FAILED",
      refreshError?.message ?? "Failed to refresh access token"
    );
  }
  return data.session.access_token;
}

export async function withAccessTokenRetry<T>(
  task: (accessToken: string) => Promise<T>
): Promise<T> {
  const accessToken = await getValidAccessToken();
  try {
    return await task(accessToken);
  } catch (error) {
    if (error instanceof AccessTokenError || !isAuthErrorLike(error)) {
      throw error;
    }

    const refreshedToken = await getValidAccessToken({ forceRefresh: true });
    return task(refreshedToken);
  }
}
