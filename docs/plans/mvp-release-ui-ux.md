# MVPリリース計画（UI/UX改善中心・Private Beta）

## 1. Summary
本計画は、`/Users/harukiuesaka/Lore-Anchor1` を「実際に使えるMVP」に仕上げるための実装順序を固定したリリースプランです。

- Scope: `Core Flow First`（ログイン→アップロード→進捗確認→ダウンロード）
- UI depth: `Design Heavy`
- Launch: `Private Beta`（Soft Private）
- Entry flow: `Landing + CTA`
- Language: `Japanese First`
- Release gate: `E2E + Usability Check`
- KPI: `Flow Completion`（アップロード→completed→ダウンロード）

## 2. Step 1: UX監査と導線定義
### 2.1 対象フロー
- `apps/web/src/app/login/page.tsx`
- `apps/web/src/app/dashboard/page.tsx`
- `apps/web/src/components/image-uploader.tsx`
- `apps/web/src/components/image-list.tsx`

### 2.2 フリクション分類（優先順）
1. **初回理解（P0）**
   - トップ遷移がダッシュボード固定で、初見ユーザーに価値説明がない。
   - Login画面が英語中心で、Private Betaの案内文脈が弱い。
2. **処理中の不安（P0）**
   - pending/processingの理由が分からず、待ち時間の体感が悪い。
   - 「壊れているのか、処理中なのか」の判断がつきにくい。
3. **失敗時復帰（P0）**
   - failed時の理由と復帰導線が不足。
   - 再試行手段がUIに存在しない。
4. **成果確認（P1）**
   - completed後の達成感（保護完了・次アクション）が弱い。
   - ダウンロード行動がKPIとして計測されていない。

### 2.3 KPI定義
- **Flow Completion** = `downloadクリック数 / upload成功数`
- 週次で算出し、MVP判定の主指標とする。

## 3. Step 2: 情報設計とビジュアル方針
### 3.1 IA（固定）
1. Landing（価値訴求 + CTA）
2. Login（メールリンク/OAuth選択）
3. Dashboard（アップロード面 + ジョブ面）

### 3.2 日本語コピー基準
- Hero: 「画像を守る。権利を証明する。」
- CTA: 「無料ベータを試す」「ダッシュボードへ」
- 処理中: 「現在保護処理中です（通常30秒〜数分）」
- 失敗時: 「画像の保護に失敗しました。再試行してください。」

### 3.3 デザイントークン指針
- 主色: 深いネイビー + シアン系アクセント
- 状態色:
  - pending: amber
  - processing: cyan
  - completed: emerald
  - failed: rose
- レイアウト: グラデ背景 + ガラス調カード + セクション階層を明確化

## 4. 実装タスク（Step 3〜8）
### Step 3: Landing + CTA
- `/` をLPに変更
- Hero / 3-step flow / trust section / CTA を追加
- CTAは認証状態で `/login` or `/dashboard` 切替

### Step 4: Login改良
- 日本語中心UIに刷新
- OAuthとメールリンクの違いを明示
- 原因別エラー表現
- 成功時の次アクションを明示

### Step 5: Dashboard改良
- アップロード面とジョブ面を分離
- 制約（形式、20MB、推奨解像度）を明示
- 状態別カード + 処理中アニメーション
- 空/読込/エラー状態の統一

### Step 6: 失敗復帰導線
- `GET /api/v1/tasks/{image_id}/status` をUI利用
- `POST /api/v1/tasks/{image_id}/retry` 追加
- failedカードにRetryボタンを追加

### Step 7: KPI計測
- `POST /api/v1/images/{image_id}/downloaded` 追加
- `images.download_count` を追加
- ダウンロード時にイベント記録
- 週次算出SQLを追加

### Step 8: QA・受け入れ・リリース
- API: `ruff`, `mypy`, `pytest`
- Web: `eslint`, `next build`
- 3ユーザーテスト（手動）
- KPI + 使用感でGo/No-Go判定

## 5. リリース判定基準
- `upload → completed` 成功率 85%以上
- `completed → downloaded` 比率 60%以上
- 3ユーザーテストで重大詰まり0件

## 6. Assumptions
- 言語は日本語優先（i18nはMVP外）
- Private BetaはSoft Private
- Worker基盤は稼働中前提
- 変更範囲は `apps/web` と `apps/api` 中心
