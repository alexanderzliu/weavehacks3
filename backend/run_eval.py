#!/usr/bin/env python3
"""Run cheatsheet evaluation from command line.

Usage:
    python run_eval.py <series_id>                    # Run full evaluation
    python run_eval.py <series_id> --summary          # Just show summary (no LLM calls)
    python run_eval.py <series_id> --games 1 2 3      # Evaluate specific games
    python run_eval.py <series_id> --model gpt-4o     # Use different scorer model
"""

import argparse
import asyncio
import os
import sys

# Ensure backend is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import directly to avoid game/__init__.py which has heavy dependencies
import importlib.util

import weave

from config import get_settings

spec = importlib.util.spec_from_file_location(
    "evaluation", os.path.join(os.path.dirname(__file__), "game", "evaluation.py")
)
evaluation_module = importlib.util.module_from_spec(spec)
sys.modules["game.evaluation"] = evaluation_module
spec.loader.exec_module(evaluation_module)
run_cheatsheet_evaluation = evaluation_module.run_cheatsheet_evaluation
get_evaluation_summary = evaluation_module.get_evaluation_summary


async def main():
    parser = argparse.ArgumentParser(description="Run cheatsheet helpfulness evaluation")
    parser.add_argument("series_id", help="Series ID to evaluate")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Only show dataset summary (no LLM evaluation)",
    )
    parser.add_argument(
        "--games",
        type=int,
        nargs="+",
        help="Specific game numbers to evaluate",
    )
    parser.add_argument(
        "--provider",
        default="openai",
        choices=["anthropic", "openai", "google", "gemini", "openai_compatible", "openrouter"],
        help="LLM provider for scorer (default: openai)",
    )
    parser.add_argument(
        "--model",
        default="gpt-5-mini",
        help="Model name for scorer (default: gpt-5-mini)",
    )
    parser.add_argument(
        "--name",
        help="Custom name for this evaluation run",
    )

    args = parser.parse_args()

    # Initialize Weave
    settings = get_settings()
    if settings.WANDB_API_KEY:
        # Weave needs WANDB_API_KEY in os.environ
        os.environ["WANDB_API_KEY"] = settings.WANDB_API_KEY
        weave_project = f"{settings.WEAVE_ENTITY}/{settings.WEAVE_PROJECT}"
        weave.init(weave_project)
        print(f"Weave initialized: {weave_project}")
    else:
        print("Warning: WANDB_API_KEY not set, Weave tracing disabled")

    if args.summary:
        # Just show summary
        print(f"\nGetting evaluation summary for series {args.series_id}...")
        summary = await get_evaluation_summary(args.series_id, args.games)

        if "error" in summary:
            print(f"Error: {summary['error']}")
            return

        print("\n" + "=" * 50)
        print("EVALUATION DATASET SUMMARY")
        print("=" * 50)
        print(f"Series ID: {summary['series_id']}")
        print(f"Total rows to evaluate: {summary['total_evaluation_rows']}")
        print(f"Games: {summary['games_count']} ({summary['games']})")
        print(f"Players: {summary['players_count']}")
        print(f"Win rate: {summary['win_rate']:.1%}")
        print(f"Survival rate: {summary['survival_rate']:.1%}")
        print(f"Rows with cheatsheet: {summary['rows_with_cheatsheet']}")
        print(f"Avg cheatsheet version: {summary['avg_cheatsheet_version']:.1f}")
        print(f"Estimated LLM calls: {summary['estimated_llm_calls']}")
        print("=" * 50)

    else:
        # Run full evaluation
        print(f"\nRunning cheatsheet evaluation for series {args.series_id}...")
        if args.games:
            print(f"Evaluating games: {args.games}")

        results = await run_cheatsheet_evaluation(
            series_id=args.series_id,
            eval_name=args.name,
            game_numbers=args.games,
            scorer_provider=args.provider,
            scorer_model=args.model,
        )

        if "error" in results:
            print(f"Error: {results['error']}")
            return

        print("\n" + "=" * 50)
        print("EVALUATION COMPLETE")
        print("=" * 50)
        print(f"Series: {results['series_id']}")
        print(f"Total rows evaluated: {results['total_rows']}")
        print("\nWeave Evaluation Results:")
        print(results.get("results", "No results available"))
        print("=" * 50)
        print("\nView detailed results in Weave UI at:")
        print(
            f"  https://wandb.ai/{settings.WEAVE_ENTITY}/{settings.WEAVE_PROJECT}/weave/evaluations"
        )


if __name__ == "__main__":
    asyncio.run(main())
