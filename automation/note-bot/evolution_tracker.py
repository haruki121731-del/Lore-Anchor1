#!/usr/bin/env python3
"""
Evolution Tracker
記事の進化過程を追跡・可視化するダッシュボード
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 非GUI環境用


class EvolutionTracker:
    """
    記事執筆システムの進化を追跡
    """
    
    def __init__(self, data_dir: str = "evolution_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
    def record_generation(self, article_id: str, strategy_version: int,
                         elements: Dict, performance: Dict):
        """記事生成を記録"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "article_id": article_id,
            "strategy_version": strategy_version,
            "elements": elements,
            "performance": performance
        }
        
        # ファイルに追記
        file_path = self.data_dir / "generations.jsonl"
        with open(file_path, 'a') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def load_history(self) -> List[Dict]:
        """履歴をロード"""
        file_path = self.data_dir / "generations.jsonl"
        if not file_path.exists():
            return []
        
        records = []
        with open(file_path) as f:
            for line in f:
                records.append(json.loads(line))
        return records
    
    def generate_report(self) -> Dict:
        """進化レポートを生成"""
        history = self.load_history()
        
        if not history:
            return {"error": "No data available"}
        
        # 基本統計
        total_articles = len(history)
        avg_score = sum(r["performance"].get("score", 0) for r in history) / total_articles
        
        # バージョンごとの進化
        version_scores = {}
        for record in history:
            ver = record["strategy_version"]
            score = record["performance"].get("score", 0)
            if ver not in version_scores:
                version_scores[ver] = []
            version_scores[ver].append(score)
        
        version_avg = {v: sum(scores)/len(scores) for v, scores in version_scores.items()}
        
        # 成功パターンの抽出
        successful = [r for r in history if r["performance"].get("score", 0) > 60]
        failed = [r for r in history if r["performance"].get("score", 0) <= 60]
        
        return {
            "total_articles": total_articles,
            "average_score": avg_score,
            "version_evolution": version_avg,
            "success_rate": len(successful) / total_articles,
            "successful_patterns": self._extract_patterns(successful),
            "failure_patterns": self._extract_patterns(failed),
        }
    
    def _extract_patterns(self, records: List[Dict]) -> Dict:
        """パターンを抽出"""
        patterns = {
            "title_types": {},
            "hook_types": {},
            "structure_types": {},
        }
        
        for record in records:
            elements = record.get("elements", {})
            
            # タイトルパターン
            title_type = elements.get("title_strategy", {}).get("pattern", "unknown")
            patterns["title_types"][title_type] = patterns["title_types"].get(title_type, 0) + 1
            
            # フックパターン
            hook_type = elements.get("hook_strategy", {}).get("type", "unknown")
            patterns["hook_types"][hook_type] = patterns["hook_types"].get(hook_type, 0) + 1
            
            # 構成パターン
            structure_type = elements.get("structure_strategy", {}).get("name", "unknown")
            patterns["structure_types"][structure_type] = patterns["structure_types"].get(structure_type, 0) + 1
        
        return patterns
    
    def visualize_evolution(self, output_path: str = "evolution_chart.png"):
        """進化を可視化"""
        history = self.load_history()
        
        if len(history) < 2:
            print("Not enough data to visualize")
            return
        
        # 時系列データ
        scores = [r["performance"].get("score", 0) for r in history]
        versions = [r["strategy_version"] for r in history]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # スコアの推移
        ax1.plot(range(len(scores)), scores, marker='o', linewidth=2, markersize=4)
        ax1.axhline(y=60, color='r', linestyle='--', label='Success Threshold')
        ax1.set_xlabel('Article Number')
        ax1.set_ylabel('Performance Score')
        ax1.set_title('Article Performance Evolution')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # バージョンごとの平均スコア
        version_data = {}
        for r in history:
            v = r["strategy_version"]
            s = r["performance"].get("score", 0)
            if v not in version_data:
                version_data[v] = []
            version_data[v].append(s)
        
        versions_sorted = sorted(version_data.keys())
        version_avgs = [sum(version_data[v])/len(version_data[v]) for v in versions_sorted]
        
        ax2.bar(versions_sorted, version_avgs, color='skyblue', edgecolor='navy')
        ax2.axhline(y=60, color='r', linestyle='--', label='Success Threshold')
        ax2.set_xlabel('Strategy Version')
        ax2.set_ylabel('Average Score')
        ax2.set_title('Strategy Version Performance')
        ax2.legend()
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Chart saved to {output_path}")


if __name__ == "__main__":
    tracker = EvolutionTracker()
    
    # サンプルデータ生成
    for i in range(20):
        tracker.record_generation(
            article_id=f"article_{i}",
            strategy_version=1 + (i // 5),  # 5記事ごとにバージョンアップ
            elements={
                "title_strategy": {"pattern": f"pattern_{i % 3}"},
                "hook_strategy": {"type": f"type_{i % 2}"},
            },
            performance={
                "score": 40 + (i * 2) + (5 if i > 10 else 0),  # 改善傾向
                "likes": 10 + i,
                "shares": 5 + (i // 2),
            }
        )
    
    # レポート生成
    report = tracker.generate_report()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    
    # 可視化
    tracker.visualize_evolution()
