-- =============================================================================
-- User plans + monthly usage tracking for Stripe billing
-- =============================================================================

-- User plan management table
CREATE TABLE IF NOT EXISTS user_plans (
    user_id uuid PRIMARY KEY,
    plan text NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'pro')),
    stripe_customer_id text,
    stripe_subscription_id text,
    monthly_upload_count int NOT NULL DEFAULT 0,
    monthly_reset_at timestamptz NOT NULL DEFAULT date_trunc('month', now()) + interval '1 month',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Index for Stripe customer lookup during webhook handling
CREATE INDEX IF NOT EXISTS idx_user_plans_stripe_customer
    ON user_plans(stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;

-- RLS policies
ALTER TABLE user_plans ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can read own plan" ON user_plans;
CREATE POLICY "Users can read own plan"
    ON user_plans FOR SELECT
    TO authenticated
    USING ((SELECT auth.uid()) = user_id);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION set_user_plans_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_user_plans_updated_at ON user_plans;
CREATE TRIGGER trg_user_plans_updated_at
    BEFORE UPDATE ON user_plans
    FOR EACH ROW
    EXECUTE FUNCTION set_user_plans_updated_at();
