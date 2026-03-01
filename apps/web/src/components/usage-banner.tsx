"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getSupabaseClient } from "@/lib/supabase/client";
import { Button } from "@/components/ui/button";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface PlanInfo {
  plan: string;
  monthly_upload_count: number;
  monthly_limit: number;
  unlimited: boolean;
}

export function UsageBanner({ refreshKey }: { refreshKey: number }) {
  const [plan, setPlan] = useState<PlanInfo | null>(null);

  useEffect(() => {
    async function fetchPlan() {
      try {
        const supabase = getSupabaseClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (!session) return;

        const res = await fetch(`${API_BASE}/api/v1/billing/plan`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (res.ok) {
          setPlan(await res.json());
        }
      } catch {
        // Billing endpoint may not be configured yet — silently ignore
      }
    }
    fetchPlan();
  }, [refreshKey]);

  if (!plan) return null;

  if (plan.unlimited) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 dark:border-green-900 dark:bg-green-950">
        <p className="text-sm font-medium text-green-800 dark:text-green-200">
          Pro Plan — 無制限アップロード
        </p>
      </div>
    );
  }

  const remaining = plan.monthly_limit - plan.monthly_upload_count;
  const isExhausted = remaining <= 0;

  return (
    <div
      className={`rounded-lg border px-4 py-3 ${
        isExhausted
          ? "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950"
          : "border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900"
      }`}
    >
      <div className="flex items-center justify-between">
        <p
          className={`text-sm ${
            isExhausted
              ? "font-medium text-red-800 dark:text-red-200"
              : "text-muted-foreground"
          }`}
        >
          {isExhausted
            ? `今月の無料枠（${plan.monthly_limit}枚）を使い切りました`
            : `今月の残り: ${remaining} / ${plan.monthly_limit} 枚`}
        </p>
        {isExhausted && (
          <Link href="/upgrade">
            <Button size="sm">Pro にアップグレード</Button>
          </Link>
        )}
      </div>
    </div>
  );
}
