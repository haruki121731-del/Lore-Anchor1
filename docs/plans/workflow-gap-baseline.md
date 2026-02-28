# 既存調査ギャップ抽出ベースライン（Lore-Anchor向け）

対象: `/Users/harukiuesaka/Downloads/B2C SaaS グロースオペレーション洗い出し.md`

このベースラインは、既存ワークフロー記述に対して `WorkflowRecord` 必須項目の不足を機械的にタグ化した初期結果です。  
判定ルールは以下です。

- `present`: 明示的で再現可能な記述がある
- `partial`: 記述はあるが曖昧、または閾値/条件が不足
- `missing`: 記述がない

## 1. 抽出したワークフローID

1. ACQ-01
2. ACQ-02
3. ACQ-03
4. ACT-01
5. ACT-02
6. ACT-03
7. RET-01
8. RET-02
9. RET-03
10. REF-01
11. REF-02
12. REV-01
13. REV-02

## 2. 不足項目タグ一覧（ワークフロー別）

| workflow_id | aarrr_stage | missing_tags | partial_tags | gap_priority |
| --- | --- | --- | --- | --- |
| ACQ-01 | Acquisition | `preconditions`,`exceptions`,`controls`,`required_skills`,`quality_thresholds`,`evidence`,`confidence`,`repair_actions` | `decision_rules`,`handoff`,`volume` | P0 |
| ACQ-02 | Acquisition | `preconditions`,`exceptions`,`controls`,`required_skills`,`quality_thresholds`,`evidence`,`confidence`,`repair_actions` | `decision_rules`,`handoff` | P1 |
| ACQ-03 | Acquisition | `preconditions`,`exceptions`,`controls`,`required_skills`,`quality_thresholds`,`evidence`,`confidence`,`repair_actions` | `decision_rules`,`handoff`,`volume` | P0 |
| ACT-01 | Activation | `preconditions`,`exceptions`,`controls`,`required_skills`,`quality_thresholds`,`evidence`,`confidence`,`repair_actions` | `decision_rules`,`sla_time`,`volume` | P0 |
| ACT-02 | Activation | `preconditions`,`exceptions`,`controls`,`required_skills`,`quality_thresholds`,`evidence`,`confidence`,`repair_actions` | `decision_rules`,`handoff`,`volume` | P0 |
| ACT-03 | Activation | `preconditions`,`exceptions`,`controls`,`required_skills`,`quality_thresholds`,`evidence`,`confidence`,`repair_actions` | `decision_rules`,`sla_time`,`volume` | P1 |
| RET-01 | Retention | `preconditions`,`exceptions`,`controls`,`required_skills`,`quality_thresholds`,`evidence`,`confidence`,`repair_actions` | `decision_rules`,`volume` | P0 |
| RET-02 | Retention | `preconditions`,`exceptions`,`controls`,`required_skills`,`quality_thresholds`,`evidence`,`confidence`,`repair_actions` | `decision_rules`,`sla_time`,`volume` | P1 |
| RET-03 | Retention | `preconditions`,`exceptions`,`controls`,`required_skills`,`quality_thresholds`,`evidence`,`confidence`,`repair_actions` | `decision_rules`,`sla_time`,`volume` | P1 |
| REF-01 | Referral | `preconditions`,`exceptions`,`required_skills`,`quality_thresholds`,`evidence`,`confidence`,`repair_actions` | `decision_rules`,`sla_time`,`controls` | P0 |
| REF-02 | Referral | `preconditions`,`exceptions`,`controls`,`required_skills`,`quality_thresholds`,`evidence`,`confidence`,`repair_actions` | `decision_rules`,`sla_time`,`volume` | P0 |
| REV-01 | Revenue | `preconditions`,`required_skills`,`quality_thresholds`,`evidence`,`confidence`,`repair_actions` | `exceptions`,`controls`,`volume` | P0 |
| REV-02 | Revenue | `preconditions`,`exceptions`,`controls`,`required_skills`,`quality_thresholds`,`evidence`,`confidence`,`repair_actions` | `decision_rules`,`volume` | P0 |

## 3. 横断ギャップ集計（頻度）

| フィールド | missing件数 | partial件数 | 優先コメント |
| --- | ---: | ---: | --- |
| `evidence` | 13 | 0 | 根拠品質の比較可能性が欠如 |
| `confidence` | 13 | 0 | 推定精度の可視化不能 |
| `repair_actions` | 13 | 0 | 監査後の修正導線なし |
| `preconditions` | 13 | 0 | 実行開始条件が曖昧 |
| `required_skills` | 13 | 0 | 担当アサイン基準が作れない |
| `quality_thresholds` | 13 | 0 | 品質合否判定ができない |
| `controls` | 11 | 2 | リスク統制が弱い |
| `exceptions` | 12 | 1 | 失敗時の復旧標準が不足 |
| `decision_rules` | 0 | 13 | 判断ルールがif/thenで未定義 |
| `volume` | 0 | 11 | 工数・負荷見積もりに不足 |
| `sla_time` | 0 | 6 | 反応時間の統一管理が困難 |
| `handoff` | 0 | 5 | 次工程への受け渡し粒度が不足 |

## 4. このベースラインの使い方

1. 第1走（メイン調査）では `missing_tags` を全件埋めることを最低要件にする。  
2. 第2走（ギャップ充填）では `partial_tags` を機械可読レベルまで明確化する。  
3. 第3走（品質監査）では `confidence` と `repair_actions` を全Recordに強制付与する。
