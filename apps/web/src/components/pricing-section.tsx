"use client";

import type { JSX } from "react";
import { Check, Shield, Zap, Award, X } from "lucide-react";
import { motion } from "framer-motion";

type PlanFeature = {
  label: string;
  free: boolean | string;
  pro: boolean | string;
};

const FEATURES: PlanFeature[] = [
  { label: "不可視透かし (PixelSeal)", free: true, pro: true },
  { label: "C2PA 来歴証明署名", free: true, pro: true },
  { label: "AI学習妨害 (Mist v2)", free: "CPU (低速)", pro: "GPU (高速)" },
  { label: "月間処理枚数", free: "5枚", pro: "100枚" },
  { label: "処理速度", free: "〜60秒", pro: "〜5秒" },
  { label: "バッチ処理", free: false, pro: true },
  { label: "優先サポート", free: false, pro: true },
];

const HIGHLIGHTS = [
  {
    icon: Shield,
    title: "Mist v2",
    subtitle: "AI学習を妨害",
    description:
      "目に見えないノイズでAIの特徴抽出を阻害。あなたの画風がコピーされるのを防ぎます。",
    color: "#3B82F6",
  },
  {
    icon: Zap,
    title: "PixelSeal",
    subtitle: "不可視の透かし",
    description:
      "128ビットのクリエイターIDを画像に埋め込み。肉眼では見えず、検出ツールで証明できます。",
    color: "#0D9488",
  },
  {
    icon: Award,
    title: "C2PA署名",
    subtitle: "業界標準の来歴証明",
    description:
      "Adobe・Google・Microsoft推進のオープン標準。「AI学習禁止」を技術的に宣言します。",
    color: "#7C3AED",
  },
];

function FeatureCheckCell({ value }: { value: boolean | string }): JSX.Element {
  if (typeof value === "string") {
    return <span className="text-[13px] text-[#6B7280]">{value}</span>;
  }
  return value ? (
    <Check size={18} className="text-[#10B981] mx-auto" />
  ) : (
    <X size={18} className="text-[#D1D5DB] mx-auto" />
  );
}

export default function PricingSection(): JSX.Element {
  return (
    <section className="w-full max-w-[960px] mx-auto mt-[80px] px-[16px]">
      {/* Feature Highlights */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-3 gap-[20px] mb-[80px]"
        initial={{ opacity: 0, y: 32 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-60px" }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      >
        {HIGHLIGHTS.map((item) => (
          <div
            key={item.title}
            className="rounded-[20px] bg-white/70 backdrop-blur-[8px] border border-[#E5E7EB] p-[28px] hover:border-[#D1D5DB] transition-colors duration-200"
          >
            <div
              className="w-[44px] h-[44px] rounded-[12px] flex items-center justify-center mb-[16px]"
              style={{ backgroundColor: `${item.color}14` }}
            >
              <item.icon size={22} style={{ color: item.color }} />
            </div>
            <h3 className="text-[18px] font-bold text-[#111827] mb-[4px]">{item.title}</h3>
            <p className="text-[13px] font-medium text-[#9CA3AF] mb-[12px]">{item.subtitle}</p>
            <p className="text-[14px] leading-[1.7] text-[#6B7280]">{item.description}</p>
          </div>
        ))}
      </motion.div>

      {/* Pricing Comparison */}
      <motion.div
        initial={{ opacity: 0, y: 32 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-60px" }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
      >
        <h2 className="text-[28px] md:text-[36px] font-[800] text-center text-[#111827] mb-[8px]">
          シンプルな料金プラン
        </h2>
        <p className="text-[15px] text-[#9CA3AF] text-center mb-[40px]">
          まずは無料ではじめて、必要に応じてアップグレード。
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-[20px] max-w-[720px] mx-auto">
          {/* Free Plan */}
          <div className="rounded-[20px] border border-[#E5E7EB] bg-white/80 backdrop-blur-[8px] p-[32px] flex flex-col">
            <span className="text-[13px] font-bold tracking-[0.15em] text-[#9CA3AF] mb-[8px]">
              FREE
            </span>
            <div className="flex items-baseline gap-[4px] mb-[8px]">
              <span className="text-[40px] font-[800] text-[#111827]">¥0</span>
              <span className="text-[14px] text-[#9CA3AF]">/月</span>
            </div>
            <p className="text-[14px] text-[#6B7280] mb-[24px] leading-[1.6]">
              基本的な保護機能を無料で。
              <br />
              クリエイターの第一歩を応援します。
            </p>
            <ul className="space-y-[12px] mb-[28px] flex-1">
              <li className="flex items-start gap-[8px] text-[14px] text-[#374151]">
                <Check size={16} className="text-[#10B981] mt-[2px] shrink-0" />
                <span>不可視透かし (PixelSeal)</span>
              </li>
              <li className="flex items-start gap-[8px] text-[14px] text-[#374151]">
                <Check size={16} className="text-[#10B981] mt-[2px] shrink-0" />
                <span>C2PA 来歴証明署名</span>
              </li>
              <li className="flex items-start gap-[8px] text-[14px] text-[#374151]">
                <Check size={16} className="text-[#10B981] mt-[2px] shrink-0" />
                <span>AI学習妨害 (CPU処理)</span>
              </li>
              <li className="flex items-start gap-[8px] text-[14px] text-[#374151]">
                <Check size={16} className="text-[#10B981] mt-[2px] shrink-0" />
                <span>月5枚まで</span>
              </li>
            </ul>
            <button
              type="button"
              className="w-full h-[48px] rounded-[24px] border-2 border-[#111827] text-[#111827] font-bold text-[15px] hover:bg-[#111827] hover:text-white transition-colors duration-200"
              onClick={() => {
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
            >
              無料ではじめる
            </button>
          </div>

          {/* Pro Plan */}
          <div className="rounded-[20px] border-2 border-[#3B82F6] bg-white/80 backdrop-blur-[8px] p-[32px] flex flex-col relative overflow-hidden">
            <div className="absolute top-0 right-0 bg-[#3B82F6] text-white text-[11px] font-bold px-[16px] py-[4px] rounded-bl-[12px]">
              RECOMMENDED
            </div>
            <span className="text-[13px] font-bold tracking-[0.15em] text-[#3B82F6] mb-[8px]">
              PRO
            </span>
            <div className="flex items-baseline gap-[4px] mb-[8px]">
              <span className="text-[40px] font-[800] text-[#111827]">¥980</span>
              <span className="text-[14px] text-[#9CA3AF]">/月</span>
            </div>
            <p className="text-[14px] text-[#6B7280] mb-[24px] leading-[1.6]">
              GPUによる高速処理で本格運用。
              <br />
              プロクリエイターのための全機能。
            </p>
            <ul className="space-y-[12px] mb-[28px] flex-1">
              <li className="flex items-start gap-[8px] text-[14px] text-[#374151]">
                <Check size={16} className="text-[#3B82F6] mt-[2px] shrink-0" />
                <span>Free プランのすべて</span>
              </li>
              <li className="flex items-start gap-[8px] text-[14px] text-[#374151]">
                <Check size={16} className="text-[#3B82F6] mt-[2px] shrink-0" />
                <span>
                  <strong>GPU高速処理</strong>（〜5秒/枚）
                </span>
              </li>
              <li className="flex items-start gap-[8px] text-[14px] text-[#374151]">
                <Check size={16} className="text-[#3B82F6] mt-[2px] shrink-0" />
                <span>月100枚まで</span>
              </li>
              <li className="flex items-start gap-[8px] text-[14px] text-[#374151]">
                <Check size={16} className="text-[#3B82F6] mt-[2px] shrink-0" />
                <span>バッチ処理対応</span>
              </li>
              <li className="flex items-start gap-[8px] text-[14px] text-[#374151]">
                <Check size={16} className="text-[#3B82F6] mt-[2px] shrink-0" />
                <span>優先サポート</span>
              </li>
            </ul>
            <button
              type="button"
              className="w-full h-[48px] rounded-[24px] bg-[#3B82F6] text-white font-bold text-[15px] hover:bg-[#2563EB] transition-colors duration-200 shadow-[0_4px_12px_rgba(59,130,246,0.3)]"
              onClick={() => {
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
            >
              Pro をはじめる
            </button>
            <p className="text-[12px] text-[#9CA3AF] text-center mt-[12px]">
              年額 ¥9,800（2ヶ月分お得）
            </p>
          </div>
        </div>

        {/* Comparison Table */}
        <div className="mt-[48px] overflow-x-auto">
          <table className="w-full max-w-[720px] mx-auto text-[14px]">
            <thead>
              <tr className="border-b border-[#E5E7EB]">
                <th className="text-left py-[12px] text-[#6B7280] font-medium">機能</th>
                <th className="text-center py-[12px] text-[#6B7280] font-medium w-[100px]">
                  Free
                </th>
                <th className="text-center py-[12px] text-[#3B82F6] font-bold w-[100px]">Pro</th>
              </tr>
            </thead>
            <tbody>
              {FEATURES.map((feature) => (
                <tr key={feature.label} className="border-b border-[#F3F4F6]">
                  <td className="py-[12px] text-[#374151]">{feature.label}</td>
                  <td className="py-[12px] text-center">
                    <FeatureCheckCell value={feature.free} />
                  </td>
                  <td className="py-[12px] text-center">
                    <FeatureCheckCell value={feature.pro} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Competitor Comparison */}
        <div className="mt-[64px] mb-[80px]">
          <h3 className="text-[22px] font-[800] text-center text-[#111827] mb-[32px]">
            他のツールとの比較
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full max-w-[720px] mx-auto text-[14px]">
              <thead>
                <tr className="border-b border-[#E5E7EB]">
                  <th className="text-left py-[12px] text-[#6B7280] font-medium">機能</th>
                  <th className="text-center py-[12px] text-[#9CA3AF] font-medium w-[90px]">
                    Glaze
                  </th>
                  <th className="text-center py-[12px] text-[#9CA3AF] font-medium w-[90px]">
                    Nightshade
                  </th>
                  <th className="text-center py-[12px] text-[#3B82F6] font-bold w-[110px]">
                    Lore-Anchor
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[#F3F4F6]">
                  <td className="py-[12px] text-[#374151]">AI学習妨害</td>
                  <td className="py-[12px] text-center">
                    <Check size={18} className="text-[#10B981] mx-auto" />
                  </td>
                  <td className="py-[12px] text-center">
                    <Check size={18} className="text-[#10B981] mx-auto" />
                  </td>
                  <td className="py-[12px] text-center">
                    <Check size={18} className="text-[#3B82F6] mx-auto" />
                  </td>
                </tr>
                <tr className="border-b border-[#F3F4F6]">
                  <td className="py-[12px] text-[#374151]">不可視透かし</td>
                  <td className="py-[12px] text-center">
                    <X size={18} className="text-[#D1D5DB] mx-auto" />
                  </td>
                  <td className="py-[12px] text-center">
                    <X size={18} className="text-[#D1D5DB] mx-auto" />
                  </td>
                  <td className="py-[12px] text-center">
                    <Check size={18} className="text-[#3B82F6] mx-auto" />
                  </td>
                </tr>
                <tr className="border-b border-[#F3F4F6]">
                  <td className="py-[12px] text-[#374151]">来歴証明 (C2PA)</td>
                  <td className="py-[12px] text-center">
                    <X size={18} className="text-[#D1D5DB] mx-auto" />
                  </td>
                  <td className="py-[12px] text-center">
                    <X size={18} className="text-[#D1D5DB] mx-auto" />
                  </td>
                  <td className="py-[12px] text-center">
                    <Check size={18} className="text-[#3B82F6] mx-auto" />
                  </td>
                </tr>
                <tr className="border-b border-[#F3F4F6]">
                  <td className="py-[12px] text-[#374151]">クラウド処理</td>
                  <td className="py-[12px] text-center">
                    <span className="text-[13px] text-[#9CA3AF]">ローカル</span>
                  </td>
                  <td className="py-[12px] text-center">
                    <span className="text-[13px] text-[#9CA3AF]">ローカル</span>
                  </td>
                  <td className="py-[12px] text-center">
                    <Check size={18} className="text-[#3B82F6] mx-auto" />
                  </td>
                </tr>
                <tr className="border-b border-[#F3F4F6]">
                  <td className="py-[12px] text-[#374151]">処理速度</td>
                  <td className="py-[12px] text-center">
                    <span className="text-[13px] text-[#9CA3AF]">数分〜数十分</span>
                  </td>
                  <td className="py-[12px] text-center">
                    <span className="text-[13px] text-[#9CA3AF]">数分〜数十分</span>
                  </td>
                  <td className="py-[12px] text-center">
                    <span className="text-[13px] font-medium text-[#3B82F6]">5秒〜60秒</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-[13px] text-[#9CA3AF] text-center mt-[16px]">
            防衛だけじゃない。証明まで。
          </p>
        </div>
      </motion.div>
    </section>
  );
}
