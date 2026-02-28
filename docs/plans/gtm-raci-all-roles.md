# Lore-Anchor GTM RACI（全ロール版）

## 1. Scope
対象は `Marketing / Sales / Customer Success / Revenue Assurance / RevOps / Governance` の全運用。  
このRACIは `/Users/harukiuesaka/Lore-Anchor1/docs/plans/gtm-architecture-marketing-sales-cs.md` の実行責任をロール別に分解したもの。

## 2. RACI Legend

- `R` Responsible: 実作業を行う担当
- `A` Accountable: 最終責任者（意思決定・承認）
- `C` Consulted: 事前相談先
- `I` Informed: 共有のみ

## 3. Role Catalog

| role_id | role_name | type | mission |
| --- | --- | --- | --- |
| GTM | GTM Commander | Human | GTM全体の優先順位と例外承認 |
| MKT-H | Marketing Lead | Human | 獲得戦略とチャネル運用 |
| SLS-H | Sales Lead | Human | PQL転換と拡張提案 |
| CS-H | Customer Success Lead | Human | 活性化・継続・回復運用 |
| BILL-H | Billing Ops Lead | Human | 請求回収・Dunning運用 |
| COM-H | Community Lead | Human | 紹介・アンバサダー運用 |
| TRUST-H | Trust & Moderation Specialist | Human | 人間制作証跡の審査品質 |
| PM-H | Product Manager | Human | 体験課題の優先度と改善反映 |
| REV-H | RevOps Lead | Human | KPI定義・データ運用・予測 |
| LEG-H | Legal & Compliance Lead | Human | 高リスク文面・規制適合 |
| MIA | Market Intelligence Agent | AI | 市場シグナル収集と分類 |
| NAR | Narrative Agent | AI | 市場別メッセージ草案生成 |
| OUT | Outreach Agent | AI | 候補抽出・送信下書き・ログ補助 |
| PQLA | PQL Scoring Agent | AI | PQL判定と優先度付け |
| CSA | CS Copilot | AI | CS文面草案・次アクション提案 |
| BILLA | Billing Recovery Agent | AI | 決済失敗優先度付けと督促草案 |
| REVA | RevOps Auditor | AI | KPI監査・逸脱検知 |

## 4. Task Dictionary

| task_id | domain | task |
| --- | --- | --- |
| T01 | Governance | 四半期GTM目標と予算を確定 |
| T02 | Governance | JP/USメッセージガードレール承認 |
| T03 | Governance | 高リスクアクション承認（送信/課金/返金/BAN） |
| T04 | Governance | 月次GTMアーキレビュー実施 |
| T05 | Marketing | 市場シグナル日次収集 |
| T06 | Marketing | シグナルの週次クラスタリングと仮説化 |
| T07 | Marketing | 市場別ナラティブ草案作成 |
| T08 | Marketing | キャンペーンコピー承認・公開 |
| T09 | Marketing | アウトリーチ対象抽出 |
| T10 | Marketing | アウトリーチ文面作成 |
| T11 | Marketing | 送信バッチ承認 |
| T12 | Marketing | 送信実行と台帳記録 |
| T13 | Sales | PQLスコア規則更新 |
| T14 | Sales | PQLルーティング |
| T15 | Sales | Assisted発見面談実施 |
| T16 | Sales | プラン提案・見積提示 |
| T17 | Sales | 受注/失注判定と理由記録 |
| T18 | Sales | 拡張提案プレイブック発火 |
| T19 | CS | Activationコンシェルジュ運用 |
| T20 | CS/Trust | 人間制作証跡レビュー |
| T21 | CS | 初回価値到達まで伴走 |
| T22 | CS | At-Risk検知と回復連絡 |
| T23 | CS/Product | フリクションをProductへエスカレーション |
| T24 | CS | 週次保護レポート配信 |
| T25 | Community | スーパーリファラー特定 |
| T26 | Community | VIP/アンバサダー運用 |
| T27 | Community | リファラル不正・整合性チェック |
| T28 | Billing | 決済失敗トリアージ |
| T29 | Billing | 市場別Dunning文面設計 |
| T30 | Billing | Dunning承認・送信実行 |
| T31 | Billing | 回収トラッキングと状態更新 |
| T32 | Billing | 返金・例外処理 |
| T33 | RevOps | KPIダッシュボード運用・データ品質監査 |
| T34 | RevOps | 月次事業レビューと予測更新 |
| T35 | Compliance | 高リスク文面/施策の法務審査 |
| T36 | Governance | ポリシー逸脱監査と是正指示 |

## 5. Role-Based RACI Decomposition

### 5.1 Master View (by Role)

| role_id | A | R | C | I |
| --- | --- | --- | --- | --- |
| GTM | T01,T02,T03,T04,T34,T36 | T01,T04 | T08,T11,T16,T30,T35 | T05,T06,T07,T09,T10,T12,T13,T14,T15,T17,T18,T19,T20,T21,T22,T23,T24,T25,T26,T27,T28,T29,T31,T32,T33 |
| MKT-H | T05,T06,T07,T08,T09,T10,T11,T12 | T08,T11 | T01,T02,T33,T34,T35 | T03,T04,T13,T14,T15,T16,T17,T18,T19,T20,T21,T22,T23,T24,T25,T26,T27,T28,T29,T30,T31,T32,T36 |
| SLS-H | T13,T14,T15,T16,T17,T18 | T15,T16,T17,T18 | T01,T11,T33,T34 | T02,T03,T04,T05,T06,T07,T08,T09,T10,T12,T19,T20,T21,T22,T23,T24,T25,T26,T27,T28,T29,T30,T31,T32,T35,T36 |
| CS-H | T19,T21,T22,T24 | T19,T21,T22,T23,T24 | T01,T03,T20,T30,T31,T34 | T02,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13,T14,T15,T16,T17,T18,T25,T26,T27,T28,T29,T32,T33,T35,T36 |
| BILL-H | T28,T29,T30,T31,T32 | T30,T31,T32 | T01,T03,T34,T35 | T02,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13,T14,T15,T16,T17,T18,T19,T20,T21,T22,T23,T24,T25,T26,T27,T33,T36 |
| COM-H | T25,T26,T27 | T26,T27 | T02,T22,T34,T35 | T01,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13,T14,T15,T16,T17,T18,T19,T20,T21,T23,T24,T28,T29,T30,T31,T32,T33,T36 |
| TRUST-H | T20 | T20 | T19,T21,T23,T35 | T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13,T14,T15,T16,T17,T18,T22,T24,T25,T26,T27,T28,T29,T30,T31,T32,T33,T34,T36 |
| PM-H | T23 | T23 | T01,T04,T19,T20,T34,T36 | T02,T03,T05,T06,T07,T08,T09,T10,T11,T12,T13,T14,T15,T16,T17,T18,T21,T22,T24,T25,T26,T27,T28,T29,T30,T31,T32,T33,T35 |
| REV-H | T33 | T33,T34 | T01,T03,T06,T13,T24,T27,T31,T36 | T02,T04,T05,T07,T08,T09,T10,T11,T12,T14,T15,T16,T17,T18,T19,T20,T21,T22,T23,T25,T26,T28,T29,T30,T32,T35 |
| LEG-H | T35 | T35 | T02,T03,T08,T11,T29,T30,T32,T36 | T01,T04,T05,T06,T07,T09,T10,T12,T13,T14,T15,T16,T17,T18,T19,T20,T21,T22,T23,T24,T25,T26,T27,T28,T31,T33,T34 |
| MIA | - | T05,T06,T09,T25 | T07,T10,T33 | T01,T02,T03,T04,T08,T11,T12,T13,T14,T15,T16,T17,T18,T19,T20,T21,T22,T23,T24,T26,T27,T28,T29,T30,T31,T32,T34,T35,T36 |
| NAR | - | T07,T10,T29 | T02,T08,T35 | T01,T03,T04,T05,T06,T09,T11,T12,T13,T14,T15,T16,T17,T18,T19,T20,T21,T22,T23,T24,T25,T26,T27,T28,T30,T31,T32,T33,T34,T36 |
| OUT | - | T10,T12 | T09,T11,T33 | T01,T02,T03,T04,T05,T06,T07,T08,T13,T14,T15,T16,T17,T18,T19,T20,T21,T22,T23,T24,T25,T26,T27,T28,T29,T30,T31,T32,T34,T35,T36 |
| PQLA | - | T13,T14,T18 | T15,T16,T33,T34 | T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T17,T19,T20,T21,T22,T23,T24,T25,T26,T27,T28,T29,T30,T31,T32,T35,T36 |
| CSA | - | T19,T21,T22,T24 | T20,T23,T33 | T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13,T14,T15,T16,T17,T18,T25,T26,T27,T28,T29,T30,T31,T32,T34,T35,T36 |
| BILLA | - | T28,T29,T31 | T30,T32,T33 | T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13,T14,T15,T16,T17,T18,T19,T20,T21,T22,T23,T24,T25,T26,T27,T34,T35,T36 |
| REVA | - | T33,T36 | T34,T35 | T01,T02,T03,T04,T05,T06,T07,T08,T09,T10,T11,T12,T13,T14,T15,T16,T17,T18,T19,T20,T21,T22,T23,T24,T25,T26,T27,T28,T29,T30,T31,T32 |

### 5.2 Role Runbook (Cadence)

| role_id | daily_focus | weekly_focus | monthly_focus |
| --- | --- | --- | --- |
| GTM | 例外承認、重大リスク判定 | KPI偏差レビュー | GTM優先順位更新、アーキレビュー |
| MKT-H | 送信バッチ承認、反応監視 | ナラティブ更新、チャネル配分 | 施策ROI見直し |
| SLS-H | 高意図リード面談、案件進行 | PQL品質レビュー | 勝因/敗因分析と提案更新 |
| CS-H | At-Risk対応、初回伴走 | 継続率レビュー、改善提案 | CS運用設計見直し |
| BILL-H | 決済失敗対応、回収追跡 | Dunning結果レビュー | 回収戦略改定 |
| COM-H | VIP対応、コミュニティ監視 | 紹介成果レビュー | アンバサダー制度改定 |
| TRUST-H | 証跡審査、誤判定救済 | 審査品質サンプリング | 審査基準改定 |
| PM-H | 高頻度フリクションの優先度付け | 改善チケット整理 | プロダクト改善計画更新 |
| REV-H | データ品質監視 | ダッシュボード改善 | 予測更新、経営レビュー |
| LEG-H | 高リスク文面審査 | 規約・法令差分監視 | コンプライアンス監査 |
| MIA | シグナル収集/分類 | クラスタ更新 | 市場変化レポート |
| NAR | 文面草案生成 | コピー改善提案 | ガイドライン最適化 |
| OUT | 対象抽出/下書き | 返信学習ループ更新 | 送信品質監査補助 |
| PQLA | PQLスコア算出 | 閾値評価 | スコア規則再学習提案 |
| CSA | CS返信草案/次アクション提案 | 回復施策の有効性評価 | CSプレイブック更新提案 |
| BILLA | 決済失敗優先度付け | 回収パターン更新 | Dunningロジック改善提案 |
| REVA | KPI逸脱・運用逸脱検知 | 監査結果配信 | 月次監査報告と是正提案 |

## 6. Approval-Critical Tasks (Human Only)

以下はAIが提案可能でも、必ず人間が最終責任を持つ。

| task_id | required_human_A |
| --- | --- |
| T03 | GTM |
| T08 | MKT-H |
| T11 | MKT-H |
| T16 | SLS-H |
| T20 | TRUST-H |
| T30 | BILL-H |
| T32 | BILL-H |
| T35 | LEG-H |
| T36 | GTM |

## 7. Machine-Readable RACI (YAML)

```yaml
raci_version: "1.0"
roles:
  - GTM
  - MKT-H
  - SLS-H
  - CS-H
  - BILL-H
  - COM-H
  - TRUST-H
  - PM-H
  - REV-H
  - LEG-H
  - MIA
  - NAR
  - OUT
  - PQLA
  - CSA
  - BILLA
  - REVA
task_count: 36
critical_human_accountability:
  - T03
  - T08
  - T11
  - T16
  - T20
  - T30
  - T32
  - T35
  - T36
ownership:
  GTM:
    A: [T01, T02, T03, T04, T34, T36]
    R: [T01, T04]
  MKT-H:
    A: [T05, T06, T07, T08, T09, T10, T11, T12]
    R: [T08, T11]
  SLS-H:
    A: [T13, T14, T15, T16, T17, T18]
    R: [T15, T16, T17, T18]
  CS-H:
    A: [T19, T21, T22, T24]
    R: [T19, T21, T22, T23, T24]
  BILL-H:
    A: [T28, T29, T30, T31, T32]
    R: [T30, T31, T32]
  COM-H:
    A: [T25, T26, T27]
    R: [T26, T27]
  TRUST-H:
    A: [T20]
    R: [T20]
  PM-H:
    A: [T23]
    R: [T23]
  REV-H:
    A: [T33]
    R: [T33, T34]
  LEG-H:
    A: [T35]
    R: [T35]
  MIA:
    R: [T05, T06, T09, T25]
  NAR:
    R: [T07, T10, T29]
  OUT:
    R: [T10, T12]
  PQLA:
    R: [T13, T14, T18]
  CSA:
    R: [T19, T21, T22, T24]
  BILLA:
    R: [T28, T29, T31]
  REVA:
    R: [T33, T36]
```

