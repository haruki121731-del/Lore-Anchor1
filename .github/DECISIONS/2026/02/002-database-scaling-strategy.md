# Decision Record: 002 - データベーススケーリング戦略

## ステータス
- [x] 提案中
- [ ] 審議中
- [ ] 承認済み
- [ ] 実装中
- [ ] 完了

## コンテキスト
現在Supabase無料枠（50K行）を使用しているが、ユーザー増加に伴い制限に近づく見込み。
スケーリング戦略を事前に決定しておく必要がある。

## 決定事項（提案）
段階的スケーリングアプローチを採用：

### Phase 1（現在〜3ヶ月）: Supabase無料枠
- 50K行まで無料で維持
- 画像メタデータのみ保存（ processed imagesは参照のみ）
- アーカイブ戦略で古いデータを管理

### Phase 2（3〜6ヶ月）: Supabase Pro
- $25/月で500K行
- パフォーマンス向上
- バックアップ自動化

### Phase 3（6〜12ヶ月）: ハイブリッド構成
- ホットデータ: Supabase
- コールドデータ: S3/R2 + 分析用DB

### Phase 4（12ヶ月以降）: 専用構成検討
- 要件に応じて自前PostgreSQL or Aurora等

## 関係チーム
- 🏗️ Architecture Team
- 📊 Data Team
- 🚀 DevOps Team
- 📈 Growth Team（ユーザー予測）

## 検討した代替案

### 代替案1: 即座にSupabase Proに移行
**長所:**
- 安心感
- パフォーマンス向上

**短所:**
- コスト増（現在は不要）
- 自律成長の原則（コスト前収益）に反する

**判断:** 現時点では不要。制限に近づいたら移行。

### 代替案2: 自前PostgreSQL
**長所:**
- 完全なコントロール
- 長期的にコスト効率

**短所:**
- 運用負担
- 初期セットアップ工数
- バックアップ・監視の責任

**判断:** 収益化・チーム拡大後に検討。

## 実装詳細

### アーカイブ戦略
```sql
-- 3ヶ月以上前の完了済みタスクをアーカイブ
CREATE OR REPLACE FUNCTION archive_old_tasks()
RETURNS void AS $$
BEGIN
  INSERT INTO archived_tasks 
  SELECT * FROM tasks 
  WHERE completed_at < NOW() - INTERVAL '3 months';
  
  DELETE FROM tasks 
  WHERE completed_at < NOW() - INTERVAL '3 months';
END;
$$ LANGUAGE plpgsql;

-- 毎週実行
SELECT cron.schedule('archive-tasks', '0 0 * * 0', 'SELECT archive_old_tasks()');
```

### 行数監視
```yaml
alert_rules:
  - name: high_row_count
    expr: supabase_table_row_count / 50000 > 0.8
    for: 1h
    labels:
      severity: warning
    annotations:
      summary: "Database row count is {{ $value | humanizePercentage }} of limit"
```

## コスト比較

| 段階 | 月額 | 備考 |
|------|------|------|
| Phase 1 | $0 | 無料枠内 |
| Phase 2 | $25 | Proプラン |
| Phase 3 | $50-100 | ハイブリッド |
| Phase 4 | $200+ | 専用構成 |

## 提案日
2026-02-28
