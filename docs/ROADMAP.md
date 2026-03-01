# Lore-Anchor ロードマップ

> **最終更新:** 2026-02-28
> **原則: 処理が動かない状態で集客しない。動く → 体験できる → 口コミ → 収益 → GPU。**

---

## 現状の正直な診断

| 問題 | 詳細 |
|------|------|
| **処理が動いていない** | SaladCloud GPU 停止中。アップロードしても status=completed にならない |
| **LP に嘘がある** | 「Free: CPU処理」と書いているが CPU Worker 未デプロイ |
| **LP が2つある** | waitinglist-lovat.vercel.app と lore-anchor1-who4.vercel.app が競合 |
| **ログイン前の価値体験がない** | 初訪問者はログイン前に何も体験できない |

---

## マイルストーン

### M0: 動くプロダクト（〜2026/03/14）
> ユーザーが実際に画像を処理して、保護済み画像をダウンロードできる状態。
> **これが達成されるまで集客は無意味。**

| Issue | タスク | 優先度 |
|-------|--------|--------|
| [#33](https://github.com/haruki121731-del/Lore-Anchor1/issues/33) | CPU Worker を Railway にデプロイ | P0 |
| [#34](https://github.com/haruki121731-del/Lore-Anchor1/issues/34) | ログイン前に Before/After デモを表示 | P0 |

**M0 完了の定義:**
- [ ] Railway CPU Worker が稼働中
- [ ] テスト画像で status=completed が確認できる
- [ ] Landing ページに処理前後サンプルが表示されている

---

### M1: 初収益（〜2026/04/01）
> M0 完了後に着手。Pro ユーザー 1人目から月¥980の収益が入る。

| Issue | タスク | 優先度 |
|-------|--------|--------|
| [#35](https://github.com/haruki121731-del/Lore-Anchor1/issues/35) | LP を 1本に統一 | P1 |
| [#36](https://github.com/haruki121731-del/Lore-Anchor1/issues/36) | Stripe 決済導入（¥980/月） | P1 |
| [#37](https://github.com/haruki121731-del/Lore-Anchor1/issues/37) | SaladCloud scale-to-zero（MRR≥$20 で有効化） | P1 |

**M1 完了の定義:**
- [ ] Stripe で ¥980 決済が通る
- [ ] Pro ユーザーは GPU 処理される（または CPU の優先キュー）
- [ ] Free ユーザーは月5枚の制限が機能している

---

### M2: 口コミ成長（〜2026/05/01）
> M0 完了後に並行して進める。

| Issue | タスク | 優先度 |
|-------|--------|--------|
| [#38](https://github.com/haruki121731-del/Lore-Anchor1/issues/38) | 口コミ成長エンジン（Note.com / Pixiv / Twitter） | P2 |

**成長ループ:**
```
処理完了 → Twitter シェアボタン → #LoreAnchor 投稿
→ 新規訪問 → 試す → 処理完了 → シェア → ...
```

**M2 完了の定義:**
- [ ] 処理完了ユーザーの 20% 以上が Twitter シェアしている
- [ ] Note.com 記事 3本公開
- [ ] 月間新規ユーザー 50名

---

## やらないこと（今は）

| やらないこと | 理由 |
|-------------|------|
| SaladCloud GPU の常時稼働 | MRR が GPU コストを超えてから |
| OpenAI 依存の朝ツイート生成 | API キー問題。テンプレートで十分 |
| C2PA 本番証明書 | 自己署名で機能的に問題なし |
| PixelSeal NN バックエンド | DWT で十分。学習コストに見合わない |
| Bluesky Outreach | シークレット未設定。Twitter で十分 |

---

## コスト管理方針

```
現在: ~$5/月（Railway のみ）
M0後: ~$5/月（CPU Worker 追加、Railway 内）
M1後: ~$5/月 + Pro 処理コスト（Stripe 収益から相殺）
M2後: MRR ¥20,000 超えたら SaladCloud GPU 有効化
```

**原則: 収益が先。コストは後。**
