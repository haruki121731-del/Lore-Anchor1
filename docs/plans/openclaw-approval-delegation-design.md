# OpenClaw 承認権限委譲設計（Lore-Anchor GTM）

## 1. 結論

OpenClawに「承認権限の一部」を与えることは可能。  
ただし、実装方針は以下に固定する。

1. OpenClawは `一次承認（機械承認）` まで。
2. 高不可逆タスクは `最終承認は人間` を維持。
3. 実際の副作用実行は、Lobsterの `approval required` と `resume` トークンでゲートする。

## 2. 根拠（OpenClaw公式機能）

以下の機能により、委譲設計が成立する。

1. `openclaw approvals` でホスト/ゲートウェイ/ノードごとのexec承認ルールを管理可能。  
   参考: [approvals CLI](https://docs.openclaw.ai/cli/approvals)
2. Lobsterで、外部副作用（送信など）前に明示的承認チェックポイントを挿入可能。  
   参考: [Lobster](https://docs.openclaw.ai/tools/lobster)
3. Heartbeat/Cronで、定常監視と定期実行を自動化可能。  
   参考: [Heartbeat](https://docs.openclaw.ai/gateway/heartbeat), [Cron jobs](https://docs.openclaw.ai/cron-jobs)
4. Hooksで監査ログやイベント連携を追加可能。  
   参考: [Hooks](https://docs.openclaw.ai/automation/hooks)

## 3. 委譲ポリシー（Level別）

| Level | 委譲方針 | OpenClaw権限 |
| --- | --- | --- |
| 0 | 完全自動化 | 実行まで自動許可 |
| 1 | 例外時のみ人間 | 既定実行は許可、`confidence/anomaly/policy` 条件で停止 |
| 2 | 人間承認必須 | ドラフトと実行準備のみ、`requiresApproval=true` で停止 |
| 3 | 人間主体 | 情報収集と選択肢提案のみ（実行不可） |

## 4. タスク別委譲可否（新RACIとの対応）

### 4.1 OpenClawへ委譲可能（実行可）

1. Level 0: `T05`
2. Level 1: `T06,T07,T09,T10,T14,T17,T18,T23,T24,T25,T28,T31,T33`

条件:
- `AI confidence >= 0.80`
- `policy_violation_flag = false`
- `anomaly_score <= 0.70`

### 4.2 OpenClawは実行準備まで（人間承認後に実行）

1. Level 2: `T08,T11,T12,T13,T22,T27,T29,T30,T36`

### 4.3 OpenClawは提案のみ（実行不可）

1. Level 3: `T01,T02,T03,T04,T15,T16,T19,T20,T21,T26,T32,T34,T35`

## 5. 承認フロー実装パターン

### 5.1 推奨フロー

1. OpenClawが入力を解析
2. Lobster pipelineを実行
3. 副作用直前で `approval required`
4. 承認対象（要約＋差分＋リスク）を人間に提示
5. 人間が `approve / reject / revise` を選択
6. `approve` の場合のみ `resumeToken` で再開

### 5.2 監査要件

1. 全承認イベントに `request_id`, `task_id`, `operator`, `decision`, `reason`, `timestamp` を保存
2. `reject` と `revise` は再提出履歴を残す
3. 月次で `approval SLA` と `rejection rate` を監査

## 6. 実装コンポーネント（最小）

1. `Policy Engine`
   - レベル別ルール適用
   - confidence/anomaly/policy判定
2. `Approval Gateway`
   - 承認要求の配信と回収
   - `approve/reject/revise` API
3. `Execution Runner`
   - Lobster run/resume呼び出し
4. `Audit Log Store`
   - 承認証跡の永続化
5. `Ops Console`
   - 人間承認UI
   - 承認キュー可視化

## 7. OpenClaw設定の実装イメージ

### 7.1 approvalsの管理

```bash
openclaw approvals get
openclaw approvals set --file ./exec-approvals.json
openclaw approvals allowlist add --agent "*" "/usr/bin/rg"
```

### 7.2 Lobsterで承認ゲートを入れる

```yaml
name: gtm-outreach-send
steps:
  - id: draft
    command: outreach draft --json
  - id: approve
    command: outreach approve-preview --json
    stdin: $draft.stdout
    approval: required
  - id: execute
    command: outreach send --json
    stdin: $draft.stdout
    condition: $approve.approved
```

### 7.3 自動実行（監視系）

```bash
openclaw cron add \
  --name "daily-signal-scan" \
  --cron "0 */2 * * *" \
  --session main \
  --system-event "Run market signal scan for T05/T06" \
  --wake now
```

## 8. 人間承認の配置（最終責任者）

| タスク群 | 最終承認者 |
| --- | --- |
| 外部発信（T08,T11,T12,T22,T29,T30） | MKT-H / CS-H / BILL-H（必要時LEG-H） |
| 収益・金銭（T16,T30,T32） | SLS-H / BILL-H |
| 審査・法務（T20,T35） | TRUST-H / LEG-H |
| 経営判断（T01,T03,T04,T34,T36） | GTM |

## 9. 導入ステップ（4週間）

1. Week 1
   - approvalsファイル定義
   - Task→Levelマッピング実装
2. Week 2
   - Level 0/1タスクをCron/Heartbeatで自動化
   - 例外エスカレーション実装
3. Week 3
   - Level 2をLobster承認ゲートへ移行
   - 承認UIと監査ログ接続
4. Week 4
   - Level 3は提案品質改善
   - SLAと拒否率を監査し閾値調整

## 10. 失敗させないための制約

1. `自動承認` を Level 2/3 へ拡張しない
2. 承認UIなしで `resume` を許可しない
3. 法務レビュー対象をAI単独で公開しない
4. 金銭操作をAI自動実行しない

この4つを破ると、不可逆リスクが急増する。

