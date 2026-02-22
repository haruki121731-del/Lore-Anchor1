"use client";

import { createBrowserClient } from "@supabase/ssr";
import { processLock } from "@supabase/supabase-js";

let client: ReturnType<typeof createBrowserClient> | null = null;

export function getSupabaseClient() {
  if (client) return client;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) throw new Error("Supabase env vars not set");

  client = createBrowserClient(url, key, {
    auth: {
      lock: processLock,
    },
  });
  return client;
}
