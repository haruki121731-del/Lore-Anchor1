#!/usr/bin/env python3
"""
Self-Improving Article Writer for Note.com
パフォーマンスフィードバックにより継続的に改善する記事執筆システム

Concept: 強化学習 + A/Bテスト + 継続的最適化
"""

import json
import logging
import random
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ElementType(Enum):
    """テスト可能な記事要素"""
    TITLE = "title"
    HOOK = "hook"  # 導入文
    STRUCTURE = "structure"  # 記事構成
    CTAS = "ctas"  # 行動喚起
    TONE = "tone"  # トーン・雰囲気
    LENGTH = "length"  # 記事長
    VISUALS = "visuals"  # 画像・図表


@dataclass
class ArticleVariant:
    """A/Bテスト用の記事バリエーション"""
    variant_id: str
    element_type: ElementType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # パフォーマンス（後から埋まる）
    impressions: int = 0
    clicks: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    time_on_page: float = 0.0
    conversion: int = 0  # Lore-Anchorへの遷移


@dataclass
class WritingStrategy:
    """記事執筆戦略（継続的に更新される）"""
    version: int
    updated_at: str
    
    # タイトル戦略
    title_patterns: List[Dict] = field(default_factory=list)
    # 導入文戦略
    hook_templates: List[Dict] = field(default_factory=list)
    # 構成戦略
    structure_templates: List[Dict] = field(default_factory=list)
    # CTA戦略
    cta_patterns: List[Dict] = field(default_factory=list)
    # トーン戦略
    tone_profiles: List[Dict] = field(default_factory=list)
    
    # パフォーマンス履歴
    performance_history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "WritingStrategy":
        return cls(**data)


class PerformanceAnalyzer:
    """
    記事パフォーマンスの分析エンジン
    """
    
    # 各指標の重み（合計100）
    METRIC_WEIGHTS = {
        "likes": 30,        # スキ（最も重要）
        "comments": 20,     # エンゲージメント
        "shares": 15,       # 拡散
        "time_on_page": 15, # 読了度
        "conversion": 15,   # ビジネス価値
        "ctr": 5,           # 興味喚起
    }
    
    def __init__(self):
        self.baseline_metrics = self.load_baseline()
    
    def load_baseline(self) -> Dict[str, float]:
        """業界平均・過去平均をロード"""
        return {
            "likes": 25.0,
            "comments": 3.0,
            "shares": 5.0,
            "time_on_page": 120.0,  # 秒
            "conversion": 2.0,
            "ctr": 0.03,
        }
    
    def calculate_score(self, metrics: Dict[str, float]) -> float:
        """
        総合スコアを計算（0-100）
        """
        score = 0.0
        
        for metric, weight in self.METRIC_WEIGHTS.items():
            if metric in metrics and metric in self.baseline_metrics:
                # ベースラインに対する比率
                ratio = metrics[metric] / self.baseline_metrics[metric]
                # 0.5倍〜2倍の範囲でスコアリング
                normalized = min(max(ratio, 0.5), 2.0)
                score += (normalized / 2.0) * weight
        
        return min(score, 100.0)
    
    def analyze_why_successful(self, article: Dict, metrics: Dict) -> List[str]:
        """
        「なぜ成功したか」を分析
        """
        insights = []
        score = self.calculate_score(metrics)
        
        if score > 80:
            insights.append("高品質コンテンツ: 深い洞察と実用的な情報")
        
        if metrics.get("likes", 0) > self.baseline_metrics["likes"] * 1.5:
            insights.append("共感を誘う内容: 読者の痛みに的確にアプローチ")
        
        if metrics.get("comments", 0) > self.baseline_metrics["comments"] * 2:
            insights.append("議論を促す構成: 問いかけや意見交換の余地")
        
        if metrics.get("shares", 0) > self.baseline_metrics["shares"] * 1.5:
            insights.append("シェアされやすい: 有用性と新規性のバランス")
        
        if metrics.get("time_on_page", 0) > self.baseline_metrics["time_on_page"] * 1.3:
            insights.append("読みやすい構成: 適切な見出しと段落分け")
        
        if metrics.get("conversion", 0) > self.baseline_metrics["conversion"] * 2:
            insights.append("効果的なCTA: 自然な誘導と信頼構築")
        
        return insights
    
    def analyze_why_failed(self, article: Dict, metrics: Dict) -> List[str]:
        """
        「なぜ失敗したか」を分析
        """
        issues = []
        
        if metrics.get("likes", 0) < self.baseline_metrics["likes"] * 0.5:
            issues.append("共感不足: 抽象的すぎる、または対象が不明確")
        
        if metrics.get("time_on_page", 0) < self.baseline_metrics["time_on_page"] * 0.5:
            issues.append("読みにくい: 文章が長すぎる、または構成が不明瞭")
        
        title = article.get("title", "")
        if len(title) < 10 or len(title) > 40:
            issues.append("タイトル問題: 長さが適切でない（10-40文字推奨）")
        
        content = article.get("content", "")
        if len(content) < 1000:
            issues.append("内容薄: 2000字以上で深い価値を提供")
        
        if metrics.get("conversion", 0) < 1:
            issues.append("CTA不足: 行動喚起が弱い、または不自然")
        
        return issues
    
    def compare_variants(self, variants: List[ArticleVariant]) -> Tuple[ArticleVariant, Dict]:
        """
        A/Bテスト結果を分析して勝者を決定
        """
        if not variants:
            return None, {}
        
        # 各バリアントのスコア計算
        scored_variants = []
        for v in variants:
            metrics = {
                "likes": v.likes,
                "comments": v.comments,
                "shares": v.shares,
                "time_on_page": v.time_on_page,
                "conversion": v.conversion,
            }
            score = self.calculate_score(metrics)
            scored_variants.append((v, score))
        
        # 勝者を選択
        winner = max(scored_variants, key=lambda x: x[1])
        
        # 統計的有意性の検証（簡易版）
        analysis = {
            "winner_id": winner[0].variant_id,
            "winner_score": winner[1],
            "improvement": winner[1] - scored_variants[0][1] if len(scored_variants) > 1 else 0,
            "all_scores": {v.variant_id: s for v, s in scored_variants},
            "confidence": "high" if winner[1] > 70 else "medium" if winner[1] > 50 else "low"
        }
        
        return winner[0], analysis


class StrategyEvolver:
    """
    執筆戦略を進化させるエンジン
    """
    
    def __init__(self, strategy_file: str = "writing_strategy.json"):
        self.strategy_file = Path(strategy_file)
        self.strategy = self.load_strategy()
    
    def load_strategy(self) -> WritingStrategy:
        """戦略をロード（なければ初期値）"""
        if self.strategy_file.exists():
            with open(self.strategy_file) as f:
                data = json.load(f)
                return WritingStrategy.from_dict(data)
        
        # 初期戦略
        return self.create_initial_strategy()
    
    def create_initial_strategy(self) -> WritingStrategy:
        """初期戦略の作成"""
        return WritingStrategy(
            version=1,
            updated_at=datetime.now().isoformat(),
            title_patterns=[
                {
                    "pattern": "{数字}選|{数字}つの方法",
                    "weight": 1.0,
                    "examples": ["AI学習対策5選", "作品を守る3つの方法"],
                    "success_rate": 0.5  # 初期値
                },
                {
                    "pattern": "徹底解説|完全ガイド",
                    "weight": 1.0,
                    "examples": ["C2PA署名徹底解説", "AI対策完全ガイド"],
                    "success_rate": 0.5
                },
                {
                    "pattern": "初心者向け|入門",
                    "weight": 1.0,
                    "examples": ["初心者向けAI学習対策", "著作権入門"],
                    "success_rate": 0.5
                },
                {
                    "pattern": "比較|vs",
                    "weight": 1.0,
                    "examples": ["Glaze vs Nightshade比較"],
                    "success_rate": 0.5
                },
            ],
            hook_templates=[
                {
                    "type": "pain_point",
                    "template": "「{具体的な悩み}」\nこのように感じている{対象}は多いのではないでしょうか。",
                    "weight": 1.0,
                    "success_rate": 0.5
                },
                {
                    "type": "shocking_fact",
                    "template": "実は、{驚きの事実}。\nこの事実を知らない{対象}が後を絶ちません。",
                    "weight": 1.0,
                    "success_rate": 0.5
                },
                {
                    "type": "question",
                    "template": "{問いかけ}？\nこの記事では、その疑問に答えます。",
                    "weight": 1.0,
                    "success_rate": 0.5
                },
            ],
            structure_templates=[
                {
                    "name": "problem_solution",
                    "sections": ["はじめに", "問題の背景", "解決策", "具体的手順", "まとめ"],
                    "weight": 1.0,
                    "success_rate": 0.5
                },
                {
                    "name": "comparison",
                    "sections": ["はじめに", "比較サマリー", "Aの詳細", "Bの詳細", "どちらを選ぶか", "結論"],
                    "weight": 1.0,
                    "success_rate": 0.5
                },
                {
                    "name": "case_study",
                    "sections": ["プロフィール", "課題", "解決策", "結果", "教訓"],
                    "weight": 1.0,
                    "success_rate": 0.5
                },
            ],
            cta_patterns=[
                {
                    "type": "soft",
                    "text": "{サービス名}で{効果}を実感してみませんか？",
                    "weight": 1.0,
                    "success_rate": 0.5
                },
                {
                    "type": "urgency",
                    "text": "今なら{特典}。{期限}までにお試しください。",
                    "weight": 1.0,
                    "success_rate": 0.5
                },
            ],
            tone_profiles=[
                {
                    "name": "friendly_expert",
                    "description": "親しみやすい専門家",
                    "characteristics": ["です・ます調", "絵文字適度", "共感的"],
                    "weight": 1.0,
                    "success_rate": 0.5
                },
                {
                    "name": "professional",
                    "description": "ビジネスライク",
                    "characteristics": ["堅実", "データ重視", "簡潔"],
                    "weight": 1.0,
                    "success_rate": 0.5
                },
            ],
        )
    
    def save_strategy(self):
        """戦略を保存"""
        with open(self.strategy_file, 'w') as f:
            json.dump(self.strategy.to_dict(), f, indent=2, ensure_ascii=False)
    
    def update_from_feedback(self, element_type: ElementType, 
                            variant: ArticleVariant, 
                            success: bool,
                            analysis: Dict):
        """
        フィードバックから戦略を更新
        """
        strategy_pool = None
        
        if element_type == ElementType.TITLE:
            strategy_pool = self.strategy.title_patterns
        elif element_type == ElementType.HOOK:
            strategy_pool = self.strategy.hook_templates
        elif element_type == ElementType.STRUCTURE:
            strategy_pool = self.strategy.structure_templates
        elif element_type == ElementType.CTAS:
            strategy_pool = self.strategy.cta_patterns
        elif element_type == ElementType.TONE:
            strategy_pool = self.strategy.tone_profiles
        
        if strategy_pool:
            # 成功した戦略の重みを上げる
            for item in strategy_pool:
                if self.matches_variant(item, variant):
                    if success:
                        item["weight"] = min(item["weight"] * 1.1, 2.0)
                        item["success_rate"] = (item["success_rate"] * 9 + 1) / 10
                    else:
                        item["weight"] = max(item["weight"] * 0.9, 0.5)
                        item["success_rate"] = (item["success_rate"] * 9 + 0) / 10
        
        # バージョンアップ
        self.strategy.version += 1
        self.strategy.updated_at = datetime.now().isoformat()
        
        # 履歴に追加
        self.strategy.performance_history.append({
            "timestamp": datetime.now().isoformat(),
            "element_type": element_type.value,
            "variant_id": variant.variant_id,
            "success": success,
            "analysis": analysis
        })
        
        self.save_strategy()
        logger.info(f"Strategy updated to version {self.strategy.version}")
    
    def matches_variant(self, item: Dict, variant: ArticleVariant) -> bool:
        """アイテムがバリアントにマッチするか"""
        # 簡易的なマッチング（実際はより高度に）
        return item.get("pattern") == variant.metadata.get("pattern") or \
               item.get("type") == variant.metadata.get("type") or \
               item.get("name") == variant.metadata.get("name")
    
    def select_best_strategy(self, element_type: ElementType) -> Dict:
        """
        重み付きランダム選択で最適な戦略を選択
        """
        strategy_pool = None
        
        if element_type == ElementType.TITLE:
            strategy_pool = self.strategy.title_patterns
        elif element_type == ElementType.HOOK:
            strategy_pool = self.strategy.hook_templates
        elif element_type == ElementType.STRUCTURE:
            strategy_pool = self.strategy.structure_templates
        elif element_type == ElementType.CTAS:
            strategy_pool = self.strategy.cta_patterns
        elif element_type == ElementType.TONE:
            strategy_pool = self.strategy.tone_profiles
        
        if not strategy_pool:
            return {}
        
        # 重み付きランダム選択
        weights = [item.get("weight", 1.0) for item in strategy_pool]
        total = sum(weights)
        probs = [w/total for w in weights]
        
        selected = random.choices(strategy_pool, weights=probs, k=1)[0]
        return selected


class SelfImprovingWriter:
    """
    自己改善型記事執筆エンジン
    """
    
    def __init__(self):
        self.analyzer = PerformanceAnalyzer()
        self.evolver = StrategyEvolver()
        self.article_history: List[Dict] = []
    
    async def write_article(self, topic: str, test_mode: bool = False) -> Dict:
        """
        記事を執筆（A/Bテスト用の複数バリアント生成）
        """
        logger.info(f"Writing article about: {topic}")
        
        # 複数のバリエーションを生成
        variants = []
        
        # バリアントA: 最適戦略を使用
        strategy_a = self.generate_with_strategy(topic, "optimized")
        variants.append(strategy_a)
        
        if test_mode:
            # バリアントB: 別戦略をテスト
            strategy_b = self.generate_with_strategy(topic, "experimental")
            variants.append(strategy_b)
            
            # バリアントC: ランダム戦略
            strategy_c = self.generate_with_strategy(topic, "random")
            variants.append(strategy_c)
        
        return {
            "topic": topic,
            "variants": variants,
            "recommended": variants[0],  # 最適戦略を推奨
            "test_mode": test_mode
        }
    
    def generate_with_strategy(self, topic: str, 
                              strategy_type: str) -> ArticleVariant:
        """
        特定の戦略で記事を生成
        """
        # 各要素の戦略を選択
        title_strategy = self.evolver.select_best_strategy(ElementType.TITLE)
        hook_strategy = self.evolver.select_best_strategy(ElementType.HOOK)
        structure_strategy = self.evolver.select_best_strategy(ElementType.STRUCTURE)
        cta_strategy = self.evolver.select_best_strategy(ElementType.CTAS)
        tone_strategy = self.evolver.select_best_strategy(ElementType.TONE)
        
        # 記事生成（実際はLLM呼び出し）
        title = self.generate_title(topic, title_strategy)
        hook = self.generate_hook(topic, hook_strategy)
        structure = structure_strategy.get("sections", [])
        cta = self.generate_cta(cta_strategy)
        
        content = self.assemble_article(
            title=title,
            hook=hook,
            structure=structure,
            body=self.generate_body(topic, structure),
            cta=cta,
            tone=tone_strategy
        )
        
        return ArticleVariant(
            variant_id=f"{strategy_type}_{int(time.time())}",
            element_type=ElementType.STRUCTURE,  # 主なテスト対象
            content=content,
            metadata={
                "strategy_type": strategy_type,
                "title_strategy": title_strategy,
                "hook_strategy": hook_strategy,
                "structure_strategy": structure_strategy,
                "cta_strategy": cta_strategy,
                "tone_strategy": tone_strategy,
            }
        )
    
    def generate_title(self, topic: str, strategy: Dict) -> str:
        """戦略に基づいてタイトルを生成"""
        pattern = strategy.get("pattern", "{トピック}徹底解説")
        
        # パターンに応じたタイトル生成
        if "選" in pattern or "つの方法" in pattern:
            return f"{topic}5選｜初心者でもできる具体的手法"
        elif "比較" in pattern or "vs" in pattern:
            return f"{topic}徹底比較｜あなたに合ったのはどれ？"
        elif "解説" in pattern or "ガイド" in pattern:
            return f"{topic}完全ガイド｜初心者向け徹底解説"
        else:
            return f"{topic}とは？初心者向け徹底解説"
    
    def generate_hook(self, topic: str, strategy: Dict) -> str:
        """導入文を生成"""
        hook_type = strategy.get("type", "pain_point")
        
        if hook_type == "pain_point":
            return f"「{topic}について、何から始めればいいか分からない」\nこのように感じているクリエイターさんは多いのではないでしょうか。"
        elif hook_type == "shocking_fact":
            return f"実は、90%のイラストレーターが{topic}を見落としています。\nこの記事では、その盲点を解説します。"
        else:
            return f"{topic}を知っていますか？\nこの記事では、基礎から実践まで徹底解説します。"
    
    def generate_body(self, topic: str, structure: List[str]) -> str:
        """本文を生成"""
        # 実際はLLMで詳細な内容を生成
        sections = []
        for section in structure[2:-1]:  # 導入とまとめを除く
            sections.append(f"## {section}\n\n{topic}に関する詳細な解説...")
        return "\n\n".join(sections)
    
    def generate_cta(self, strategy: Dict) -> str:
        """CTAを生成"""
        cta_type = strategy.get("type", "soft")
        
        if cta_type == "soft":
            return "Lore-Anchorで作品保護を始めてみませんか？月5枚まで無料で試せます。"
        elif cta_type == "urgency":
            return "今ならProプランが1ヶ月無料。限定30名様まで、お早めに！"
        else:
            return "詳細はLore-Anchor公式サイトをご覧ください。"
    
    def assemble_article(self, title: str, hook: str, structure: List[str],
                        body: str, cta: str, tone: Dict) -> str:
        """記事を組み立て"""
        tone_chars = tone.get("characteristics", [])
        
        article = f"""# {title}

{hook}

{body}

## まとめ

{hook.split('。')[0]}について解説しました。
- 重要なポイントを3つまとめる
- 次のステップを示す

{cta}

---

**この記事が役に立ったら「スキ」してください！**  
**質問があればコメント欄へ** 💬
"""
        
        # トーンに応じた調整
        if "絵文字適度" in tone_chars:
            article = article.replace("!", "! 💪").replace("。", "。")
        
        return article
    
    async def collect_performance(self, article_id: str, 
                                 metrics: Dict[str, float]) -> Dict:
        """
        パフォーマンスデータを収集・分析
        """
        logger.info(f"Collecting performance for {article_id}")
        
        # スコア計算
        score = self.analyzer.calculate_score(metrics)
        
        # 成功判定
        is_success = score > 60  # 60点以上を成功とする
        
        # 分析
        if is_success:
            insights = self.analyzer.analyze_why_successful({}, metrics)
        else:
            insights = self.analyzer.analyze_why_failed({}, metrics)
        
        analysis = {
            "article_id": article_id,
            "score": score,
            "is_success": is_success,
            "insights": insights,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
        # 履歴に保存
        self.article_history.append(analysis)
        
        return analysis
    
    async def improve_from_feedback(self, article_id: str, 
                                   variant: ArticleVariant,
                                   analysis: Dict):
        """
        フィードバックから戦略を改善
        """
        logger.info(f"Improving strategy from feedback: {article_id}")
        
        # 各要素タイプでフィードバックを適用
        for element_type in ElementType:
            if element_type.value in variant.metadata:
                self.evolver.update_from_feedback(
                    element_type=element_type,
                    variant=variant,
                    success=analysis["is_success"],
                    analysis=analysis
                )
        
        logger.info("Strategy evolution complete")
    
    async def run_continuous_improvement_loop(self):
        """
        継続的改善ループ（メイン実行関数）
        """
        logger.info("Starting continuous improvement loop...")
        
        # 1. 新しい記事を書く（A/Bテストバリアント含む）
        topic = self.select_next_topic()
        article_package = await self.write_article(topic, test_mode=True)
        
        # 2. 投稿（実際はNotePublisherに委譲）
        # await self.publish(article_package)
        
        # 3. 待機（データ収集期間：1週間）
        logger.info("Waiting for performance data collection...")
        # await asyncio.sleep(7 * 24 * 3600)  # 1週間
        
        # 4. パフォーマンス収集
        for variant in article_package["variants"]:
            # 実際はNote.com APIやスクレイピングで取得
            mock_metrics = {
                "likes": random.randint(10, 50),
                "comments": random.randint(0, 10),
                "shares": random.randint(0, 20),
                "time_on_page": random.randint(60, 300),
                "conversion": random.randint(0, 5),
            }
            
            analysis = await self.collect_performance(
                variant.variant_id, 
                mock_metrics
            )
            
            # 5. 戦略を改善
            await self.improve_from_feedback(
                variant.variant_id,
                variant,
                analysis
            )
        
        logger.info("Improvement cycle complete. Strategy updated.")
    
    def select_next_topic(self) -> str:
        """次のトピックを選択（トレンド分析結果から）"""
        # 実際はTrendResearcherから取得
        topics = [
            "AI学習対策",
            "Glaze vs Nightshade比較",
            "C2PA署名入門",
            "無断転載への対処法",
            "AI時代の著作権",
        ]
        return random.choice(topics)
    
    def get_strategy_report(self) -> Dict:
        """現在の戦略レポートを取得"""
        return {
            "version": self.evolver.strategy.version,
            "updated_at": self.evolver.strategy.updated_at,
            "title_patterns": len(self.evolver.strategy.title_patterns),
            "hook_templates": len(self.evolver.strategy.hook_templates),
            "performance_history_count": len(self.evolver.strategy.performance_history),
            "article_count": len(self.article_history),
            "avg_score": sum(a["score"] for a in self.article_history) / len(self.article_history) if self.article_history else 0,
        }


# メイン実行部分
async def main():
    """メイン実行関数"""
    writer = SelfImprovingWriter()
    
    # 初期状態を表示
    print("=== Initial Strategy Report ===")
    print(json.dumps(writer.get_strategy_report(), indent=2, ensure_ascii=False))
    
    # 改善ループを実行
    for i in range(3):  # 3サイクル実行
        print(f"\n=== Improvement Cycle {i+1} ===")
        await writer.run_continuous_improvement_loop()
        
        # 進捗表示
        report = writer.get_strategy_report()
        print(f"Strategy Version: {report['version']}")
        print(f"Average Score: {report['avg_score']:.1f}")
    
    # 最終レポート
    print("\n=== Final Strategy Report ===")
    print(json.dumps(writer.get_strategy_report(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # テスト実行
    asyncio.run(main())
