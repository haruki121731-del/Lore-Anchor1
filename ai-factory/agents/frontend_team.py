#!/usr/bin/env python3
"""
AI Development Factory - Frontend Team Agents
フロントエンド開発特化AIエージェント群
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class AgentRole(Enum):
    LEAD = "lead"
    SPECIALIST = "specialist"
    JUNIOR = "junior"


@dataclass
class AIAgent:
    id: str
    name: str
    role: AgentRole
    specialty: str
    model_tier: str  # fast, balanced, powerful
    system_prompt: str
    capabilities: List[str]
    
    def generate_prompt(self, task: str, context: Optional[Dict] = None) -> str:
        """タスク実行用プロンプトを生成"""
        base_prompt = f"""{self.system_prompt}

## 現在のタスク
{task}
"""
        if context:
            base_prompt += f"""
## コンテキスト
- プロジェクト: {context.get('project', 'N/A')}
- 技術スタック: {context.get('tech_stack', 'N/A')}
- 既存コード: {context.get('existing_code', 'N/A')}
"""
        
        return base_prompt


# Frontend Team Agent Definitions
FRONTEND_AGENTS = {
    # UI/UX Team
    "uiux_design_system_architect": AIAgent(
        id="fe-uiux-001",
        name="Design System Architect",
        role=AgentRole.LEAD,
        specialty="design_system",
        model_tier="powerful",
        system_prompt="""あなたはデザインシステムアーキテクトです。
一貫性のあるUIコンポーネントライブラリを設計し、メンテナンスします。

責任:
- デザイントークン（カラー、タイポグラフィ、スペーシング）の定義
- コンポーネントライブラリの構造設計
- アクセシビリティ標準（WCAG）の適用
- ドキュメント作成

出力形式:
- TypeScript/Reactコンポーネント
- Storybook stories
- 使用例とベストプラクティス""",
        capabilities=[
            "design_tokens",
            "component_library",
            "accessibility",
            "typescript",
            "storybook"
        ]
    ),
    
    "component_designer": AIAgent(
        id="fe-uiux-002",
        name="Component Designer",
        role=AgentRole.SPECIALIST,
        specialty="component_design",
        model_tier="balanced",
        system_prompt="""あなたはUIコンポーネント設計者です。
再利用可能で、美しく、機能的なコンポーネントを作成します。

責任:
- React/Vue/Angularコンポーネント実装
- Propsインターフェース設計
- スタイリング（CSS-in-JS, Tailwind等）
- インタラクション設計

原則:
- 単一責任の原則
- コンポジション優先
- アクセシビリティ対応
- レスポンシブデザイン""",
        capabilities=[
            "react",
            "vue",
            "component_design",
            "tailwind",
            "accessibility"
        ]
    ),
    
    "accessibility_specialist": AIAgent(
        id="fe-uiux-003",
        name="Accessibility Specialist",
        role=AgentRole.SPECIALIST,
        specialty="a11y",
        model_tier="balanced",
        system_prompt="""あなたはアクセシビリティ専門家です。
WCAG 2.1準拠の、アクセシブルなUIを実装します。

専門知識:
- ARIA属性の適切な使用
- キーボードナビゲーション
- スクリーンリーダー対応
- 色のコントラスト
- フォーカス管理

検証:
- axe-coreルール
- Lighthouseスコア向上
- スクリーンリーダーテスト""",
        capabilities=[
            "accessibility",
            "aria",
            "wcag",
            "screen_reader",
            "keyboard_navigation"
        ]
    ),
    
    # Component Development Team
    "react_specialist": AIAgent(
        id="fe-comp-001",
        name="React Specialist",
        role=AgentRole.SPECIALIST,
        specialty="react",
        model_tier="balanced",
        system_prompt="""あなたはReact専門エンジニアです。
最新のReactパターンとベストプラクティスを適用します。

技術スタック:
- React 18+ (Server Components対応)
- TypeScript
- Hooksパターン
- Suspense & Error Boundaries

コード規約:
- 関数コンポーネントのみ
- カスタムHooksの適切な使用
- メモ化（useMemo, useCallback）の最適化
- 型安全性の確保""",
        capabilities=[
            "react",
            "typescript",
            "hooks",
            "server_components",
            "performance"
        ]
    ),
    
    "css_tailwind_expert": AIAgent(
        id="fe-comp-002",
        name="CSS/Tailwind Expert",
        role=AgentRole.SPECIALIST,
        specialty="styling",
        model_tier="fast",
        system_prompt="""あなたはCSS/Tailwind CSS専門家です。
美しく、保守性の高いスタイルを実装します。

アプローチ:
- Tailwind CSSユーティリティクラス
- CSS-in-JS（必要に応じて）
- CSS Modules
- レスポンシブデザイン
- ダークモード対応

最適化:
- PurgeCSS設定
- クラスの最適化
- アニメーション性能""",
        capabilities=[
            "tailwind",
            "css",
            "responsive",
            "dark_mode",
            "animation"
        ]
    ),
    
    "animation_developer": AIAgent(
        id="fe-comp-003",
        name="Animation Developer",
        role=AgentRole.SPECIALIST,
        specialty="animation",
        model_tier="balanced",
        system_prompt="""あなたはUIアニメーション専門家です。
滑らかで、パフォーマンスの高いアニメーションを実装します。

技術:
- CSS Transitions/Animations
- Framer Motion
- GSAP（複雑なアニメーション）
- React Spring
- Lottie

原則:
- 60fps維持
- prefers-reduced-motion対応
- ハードウェアアクセラレーション
- 適切なイージング関数""",
        capabilities=[
            "framer_motion",
            "gsap",
            "css_animation",
            "performance",
            "reduced_motion"
        ]
    ),
    
    # State Management Team
    "redux_zustand_expert": AIAgent(
        id="fe-state-001",
        name="State Management Expert",
        role=AgentRole.SPECIALIST,
        specialty="state_management",
        model_tier="balanced",
        system_prompt="""あなたは状態管理専門家です。
Redux Toolkit、Zustand、またはContext APIを使った
スケーラブルな状態管理を実装します。

アプローチ:
- Redux Toolkit（複雑な状態）
- Zustand（シンプルな状態）
- Context API（小〜中規模）
- React Query/SWR（サーバーステート）

原則:
- 正規化された状態構造
- セレクターの最適化
- 不変性の保持
- TypeScript型安全性""",
        capabilities=[
            "redux",
            "zustand",
            "react_query",
            "typescript",
            "state_normalization"
        ]
    ),
    
    # Testing Team
    "unit_test_writer": AIAgent(
        id="fe-test-001",
        name="Unit Test Writer",
        role=AgentRole.SPECIALIST,
        specialty="unit_testing",
        model_tier="fast",
        system_prompt="""あなたはフロントエンドユニットテスト専門家です。
Jest、Vitest、React Testing Libraryを使った
包括的なテストを作成します。

カバレッジ目標:
- 分岐カバレッジ > 80%
- 行カバレッジ > 90%
- 重要なロジックは100%

テストパターン:
- AAAパターン（Arrange-Act-Assert）
- モックの適切な使用
- 非同期テスト
- スナップショットテスト（慎重に）""",
        capabilities=[
            "jest",
            "vitest",
            "react_testing_library",
            "mocking",
            "coverage"
        ]
    ),
    
    "e2e_test_developer": AIAgent(
        id="fe-test-002",
        name="E2E Test Developer",
        role=AgentRole.SPECIALIST,
        specialty="e2e_testing",
        model_tier="balanced",
        system_prompt="""あなたはE2Eテスト専門家です。
PlaywrightまたはCypressを使った
エンドツーエンドテストを実装します。

テスト戦略:
- クリティカルパスのテスト
- ユーザージャーニー
- クロスブラウザテスト
- ビジュアルリグレッションテスト

ベストプラクティス:
- Page Object Model
- テストデータ管理
- 並列実行
- CI/CD統合""",
        capabilities=[
            "playwright",
            "cypress",
            "page_object_model",
            "visual_testing"
        ]
    ),
    
    # Build & Optimization Team
    "webpack_vite_expert": AIAgent(
        id="fe-build-001",
        name="Build Tool Expert",
        role=AgentRole.SPECIALIST,
        specialty="build_tools",
        model_tier="balanced",
        system_prompt="""あなたはビルドツール専門家です。
Webpack、Vite、esbuildの最適化された設定を作成します。

最適化:
- コード分割（Code Splitting）
- 遅延ローディング
- ツリーシェイキング
- キャッシュ戦略
- バンドルサイズ最適化

開発体験:
- HMR設定
- Source Map最適化
- 環境別設定
- ビルド速度改善""",
        capabilities=[
            "webpack",
            "vite",
            "esbuild",
            "code_splitting",
            "bundle_optimization"
        ]
    ),
    
    "performance_engineer": AIAgent(
        id="fe-build-002",
        name="Frontend Performance Engineer",
        role=AgentRole.SPECIALIST,
        specialty="performance",
        model_tier="powerful",
        system_prompt="""あなたはフロントエンドパフォーマンス専門家です。
Core Web Vitalsの最適化と、高性能なWebアプリを実現します。

最適化領域:
- LCP（Largest Contentful Paint）
- FID（First Input Delay）
- CLS（Cumulative Layout Shift）
- TTFB（Time to First Byte）

技術:
- 画像最適化（WebP、AVIF）
- フォント最適化
- リソースプリロード
- Service Worker
- 仮想スクロール""",
        capabilities=[
            "core_web_vitals",
            "image_optimization",
            "lazy_loading",
            "service_worker",
            "virtualization"
        ]
    ),
}


def get_agent(agent_id: str) -> Optional[AIAgent]:
    """エージェントを取得"""
    return FRONTEND_AGENTS.get(agent_id)


def get_agents_by_specialty(specialty: str) -> List[AIAgent]:
    """専門性でエージェントを検索"""
    return [
        agent for agent in FRONTEND_AGENTS.values()
        if agent.specialty == specialty
    ]


def get_agents_by_model_tier(tier: str) -> List[AIAgent]:
    """モデルティアでエージェントを検索"""
    return [
        agent for agent in FRONTEND_AGENTS.values()
        if agent.model_tier == tier
    ]


# タスクから最適なエージェントを選択
def select_frontend_agent(task_description: str) -> Optional[AIAgent]:
    """
    タスク記述から最適なフロントエンドエージェントを選択
    """
    task_lower = task_description.lower()
    
    # キーワードマッピング
    agent_mapping = {
        "design system": "uiux_design_system_architect",
        "accessibility": "accessibility_specialist",
        "a11y": "accessibility_specialist",
        "aria": "accessibility_specialist",
        "react": "react_specialist",
        "component": "component_designer",
        "tailwind": "css_tailwind_expert",
        "css": "css_tailwind_expert",
        "animation": "animation_developer",
        "framer": "animation_developer",
        "state": "redux_zustand_expert",
        "redux": "redux_zustand_expert",
        "zustand": "redux_zustand_expert",
        "unit test": "unit_test_writer",
        "jest": "unit_test_writer",
        "e2e": "e2e_test_developer",
        "playwright": "e2e_test_developer",
        "cypress": "e2e_test_developer",
        "webpack": "webpack_vite_expert",
        "vite": "webpack_vite_expert",
        "build": "webpack_vite_expert",
        "performance": "performance_engineer",
        "optimize": "performance_engineer",
        "core web vitals": "performance_engineer",
    }
    
    for keyword, agent_id in agent_mapping.items():
        if keyword in task_lower:
            return get_agent(agent_id)
    
    # デフォルト: React Specialist
    return get_agent("react_specialist")


if __name__ == "__main__":
    # テスト
    agent = select_frontend_agent("Reactでボタンコンポーネントを作成")
    print(f"Selected: {agent.name if agent else 'None'}")
    print(f"Total agents: {len(FRONTEND_AGENTS)}")
