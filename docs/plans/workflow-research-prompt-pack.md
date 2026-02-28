# Lore-Anchor ワークフロー解像度最大化リサーチプロンプトパック

このドキュメントは、Lore-Anchor向けに「AARRR全体の運用ワークフロー解像度」を引き上げるための実行用プロンプトセットです。  
前提は `日米先行` `個人クリエイター中心` `実装設計は除外` です。

## 1. 実行プロトコル（3走）

1. 第1走: メイン調査プロンプトで全体マップを生成する。
2. 第2走: ギャップ充填プロンプトで未充足セルのみ追補する。
3. 第3走: 品質監査プロンプトで矛盾・証拠・市場適合を監査する。

運用ルール:
- 第1走の出力を第2走の入力に必ず渡す。
- 第2走の出力を第3走の入力に必ず渡す。
- 第3走で `PASS` になるまで第2走→第3走を反復する。

## 2. 入力仕様（PromptInput）

```json
{
  "product_context": "Lore-Anchor: 画像生成AIの無断学習からクリエイターを保護するサービス",
  "stage": "Private Beta",
  "target_segment": "個人クリエイター（イラスト/漫画/映像/デザイン）",
  "geos": ["JP", "US"],
  "aarrr_scope": ["Acquisition", "Activation", "Retention", "Referral", "Revenue"],
  "exclusion_scope": [
    "AIエージェント実装アーキテクチャ提案",
    "システム設計やコード設計",
    "特定ツールの導入設計"
  ],
  "output_language": "ja",
  "evidence_policy": {
    "min_sources_per_record": 2,
    "prefer_primary_sources": true,
    "require_publish_date": true,
    "require_market_fit_tag": true,
    "allow_inference_only_with_flag": true
  }
}
```

## 3. 出力オントロジー（固定）

### 3.1 WorkflowRecord

各ワークフローは以下を必須とします。

```json
{
  "workflow_id": "ACQ-001",
  "aarrr_stage": "Acquisition",
  "job_type": "獲得",
  "priority": "P0",
  "market_fit": ["JP", "US"],
  "objective": "このワークフローの成果目的",
  "actor": ["実行役割A", "実行役割B"],
  "trigger": "開始条件",
  "preconditions": ["事前条件1", "事前条件2"],
  "inputs": ["入力データ1", "入力データ2"],
  "tools": ["利用ツール1", "利用ツール2"],
  "micro_steps": [
    "8ステップ以上で記述する",
    "各ステップは観察可能な作業単位にする"
  ],
  "decision_rules": [
    "if/then形式で3件以上",
    "閾値・判断条件を含む"
  ],
  "exceptions": [
    "失敗・例外シナリオを3件以上",
    "復旧手順とエスカレーション条件を含む"
  ],
  "handoff": {
    "to_workflow_id": "ACT-002",
    "handoff_payload": ["次工程に渡す項目"],
    "handoff_sla": "24h以内"
  },
  "sla_time": "1件あたり目安時間 or バッチ時間",
  "volume": {
    "unit": "件/日",
    "typical": "通常値",
    "peak": "ピーク値"
  },
  "kpi": [
    {"name": "主要KPI", "formula": "定義式", "target": "目標値"}
  ],
  "risks": ["主要リスク"],
  "controls": ["予防統制", "検知統制"],
  "required_skills": ["必要スキル"],
  "quality_thresholds": ["品質閾値"],
  "evidence": [
    {
      "source_type": "一次",
      "source_url": "https://example.com",
      "publish_date": "2026-01-10",
      "market_fit": "US",
      "recency": "latest",
      "contradiction_notes": ""
    }
  ],
  "confidence": 0.0,
  "unknowns": ["未確定事項"],
  "repair_actions": ["監査で要求された修正アクション"]
}
```

最低品質条件:
- `micro_steps >= 8`
- `decision_rules >= 3`
- `exceptions >= 3`
- `evidence >= 2`

### 3.2 CoverageMatrix

軸: `AARRR × ジョブタイプ（獲得/教育/支援/回収） × チャネル × 重要度`

```json
{
  "aarrr_stage": "Activation",
  "job_type": "教育",
  "channel": "オンボーディングメール",
  "priority": "P1",
  "required_workflow_count": 1,
  "actual_workflow_count": 0,
  "status": "missing",
  "gap_reason": "該当ワークフロー未収集",
  "linked_workflow_ids": []
}
```

### 3.3 EvidenceSpec

`WorkflowRecord.evidence[*]` は以下を必須とします。

- `source_type`: `一次` / `二次` / `実務知見`
- `source_url`: 検証可能URL
- `publish_date`: `YYYY-MM-DD`
- `market_fit`: `JP` or `US`
- `recency`: `latest` / `acceptable` / `stale`
- `contradiction_notes`: 反証・相違があれば記載

## 4. プロンプト1（メイン調査）

```text
あなたはB2C SaaS Growth Operationsの主任リサーチャーです。
目的は、Lore-Anchor向けにAARRR全体の運用ワークフローを、実務再現可能な粒度でマッピングすることです。

[固定前提]
- 対象プロダクト: Lore-Anchor（クリエイター保護）
- フェーズ: Private Beta
- 主対象: 個人クリエイター
- 市場: JPとUS
- スコープ: AARRR全体
- 非スコープ: AIエージェント実装設計、システム設計、コード設計

[入力]
以下のPromptInput JSONを読み込んで実行してください:
<PROMPT_INPUT_JSON>

[必須手順]
1) AARRR全体の候補ワークフローを列挙し、重複を統合する。
2) 各ワークフローをWorkflowRecord形式で記述する。
3) CoverageMatrixを作成し、filled/partial/missingを判定する。
4) unknownは推測で埋めず、unknownsへ記録する。
5) JPとUSで実務が異なる場合は統合せず条件分岐で記述する。

[厳守制約]
- 各WorkflowRecordで micro_steps>=8, decision_rules>=3, exceptions>=3 を満たすこと。
- 各WorkflowRecordに evidenceを2件以上付与すること。
- evidenceはpublish_dateとmarket_fitを必須とすること。
- 推測は「inference」と明示し、confidenceを下げること。
- 実装アーキテクチャ提案は禁止。

[出力形式]
以下の順序でMarkdownを返すこと。

## Layer 1: 経営向けサマリー
- 最重要課題Top5（P0優先）
- 期待インパクト（AARRR別）
- JP/US差分の要点
- unknownの件数と意思決定リスク

## Layer 2: オペレーション詳細台帳
1. CoverageMatrix（JSON配列）
2. Workflow Ledger（WorkflowRecord JSON配列）
3. Unknown Backlog（優先度付き）

[終了条件]
- AARRR全フェーズに最低1つ以上のWorkflowRecordが存在する。
- CoverageMatrixにmissing理由が全件記述されている。
- 重大なunknownが残る場合、追調査計画を必ず提示する。
```

## 5. プロンプト2（ギャップ充填）

```text
あなたは前走結果の欠落を埋めるリサーチ担当です。
入力されたCoverageMatrixとWorkflow Ledgerを解析し、missing/partialセルだけを対象に追補調査を行ってください。

[入力]
1) PromptInput JSON
2) 第1走のCoverageMatrix
3) 第1走のWorkflow Ledger
4) 第1走のUnknown Backlog

[必須手順]
1) missing/partialセルをP0→P1→P2で並び替える。
2) 高インパクトかつ高不確実性のセルから埋める。
3) 既存WorkflowRecordは上書きではなく差分更新（delta）で示す。
4) 根拠不足のレコードには追加evidenceを付与する。
5) 依然として不明な項目はunknownとして残し、次の調査方法を具体化する。

[厳守制約]
- 新規追加または更新したWorkflowRecordも micro_steps>=8, decision_rules>=3, exceptions>=3 を満たすこと。
- 各更新レコードに evidenceを2件以上保持すること。
- 推測で欠落を埋めないこと。

[出力形式]
## Gap Resolution Summary
- 解消したmissing件数
- 解消したpartial件数
- 残課題件数

## Updated CoverageMatrix
- 全セルの最新版（JSON配列）

## Workflow Delta Pack
- 追加/更新したWorkflowRecordのみ（JSON配列）

## Remaining Unknowns and Next Probe
- unknownごとの次アクション（誰が、どこを、いつ確認するか）
```

## 6. プロンプト3（品質監査・レッドチーム）

```text
あなたは品質監査担当（レッドチーム）です。
第1走と第2走の結果を監査し、矛盾・根拠薄弱・市場不一致・再現不能を指摘してください。

[入力]
1) PromptInput JSON
2) 最新CoverageMatrix
3) 最新Workflow Ledger（第1走+第2走の統合版）
4) Remaining Unknowns

[監査観点]
- 網羅性: AARRR全体と主要チャネルがカバーされているか
- 粒度: micro_steps/decision_rules/exceptionsの閾値を満たすか
- 実務再現性: 誰が、いつ、何を、どこまで行うか再現できるか
- 証拠強度: evidenceの件数・一次性・日付・市場適合
- JP/US適合: 差分が統合されず条件分岐で扱われているか

[スコアリング]
- 網羅性 25点
- 粒度 20点
- 実務再現性 20点
- 証拠強度 20点
- JP/US適合 15点
- 合格条件: 総合85点以上かつ重大欠陥0件

[重大欠陥の定義]
- AARRRのいずれかが未充足
- evidence<2のWorkflowRecordが存在
- high-impactレコードで矛盾未解消
- JP/US差分を混在させ意思決定不能

[出力形式]
## Audit Scorecard
- 軸別スコア
- 総合スコア
- 判定（PASS/FAIL）

## Critical Findings
- 重大欠陥の一覧（なければ「なし」）

## Record-level Repairs
- 各WorkflowRecordごとに confidence と repair_actions を提示

## Release Recommendation
- 今回の台帳を運用投入してよいか（条件付き可/不可を明示）
```

## 7. スコアリング基準（固定）

| 評価軸 | 配点 | 合格条件 |
| --- | ---: | --- |
| 網羅性 | 25 | AARRR全体と優先チャネルを充足 |
| 粒度 | 20 | すべてのRecordで最小粒度要件を達成 |
| 実務再現性 | 20 | 第三者が手順を再現可能 |
| 証拠強度 | 20 | 各Recordで2件以上、日付と市場適合あり |
| JP/US適合 | 15 | 地域差分が条件分岐で明示 |

合格閾値:
- 総合 `85/100` 以上
- 重大欠陥 `0件`

## 8. 受け入れテスト（実行時チェックリスト）

1. 網羅性テスト: AARRR各フェーズにWorkflowRecordが存在するか。
2. 粒度テスト: 各Recordで `micro_steps>=8` `decision_rules>=3` `exceptions>=3` を満たすか。
3. 根拠テスト: 各Recordに信頼できるevidenceが2件以上あるか。
4. 矛盾テスト: JP/US差分や相反実務が分離記述されているか。
5. 再現性テスト: 実行者・タイミング・入力・出力が明示されているか。
6. 目的整合テスト: 実装設計に逸脱していないか。

## 9. デフォルト前提（固定）

- Lore-AnchorはPrivate Beta相当として扱う。
- 主対象は個人クリエイターとする。
- 市場はJP/US先行で扱う。
- 出力言語は日本語をデフォルトとする。
- 不明情報は `unknown` で残し、追調査計画を必須化する。
- AIエージェントの実装方式提案はスコープ外とする。
