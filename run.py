import os
import json
from dotenv import load_dotenv
from src.evaluator import ABTestEvaluator


def main():
    load_dotenv()
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env")
        return
    
    DATASET_PATH = 'data/humaneval_fix.jsonl'
    SAMPLE_SIZE = 163  # Isti 50 problema
    TIMEOUT = 30  # Max 30 sekundi po problemu
    
    if not os.path.exists(DATASET_PATH):
        print(f"Error: Dataset not found at {DATASET_PATH}")
        print("Run: python data/download_dataset.py")
        return
    
    print("=" * 70)
    print("A/B TEST: DirectAgent vs ReactAgent (SAME 50 PROBLEMS)")
    print("=" * 70)
    print(f"Dataset: {DATASET_PATH}")
    print(f"Problems: First {SAMPLE_SIZE} from dataset")
    print(f"Timeout: {TIMEOUT}s per problem")
    print(f"Strategy: BOTH agents test SAME problems")
    print("=" * 70 + "\n")
    
    # Run A/B test
    evaluator = ABTestEvaluator(api_key, timeout=TIMEOUT)
    results = evaluator.run_ab_test_same_problems(DATASET_PATH, SAMPLE_SIZE)
    
    # Save results
    output_file = 'ab_test_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    
    # Print comparison
    print(f"\n" + "=" * 70)
    print("FINAL COMPARISON (SAME 50 PROBLEMS)")
    print("=" * 70)
    
    direct_metrics = results['direct_agent_metrics']
    react_metrics = results['react_agent_metrics']
    
    print(f"\nDIRECT AGENT:")
    print(f"  Pass@1:       {direct_metrics['pass_at_1']:.1%}")
    print(f"  Fixed:        {direct_metrics['fixed']}/{direct_metrics['total']}")
    print(f"  Avg time:     {direct_metrics['avg_time']:.2f}s")
    print(f"  Timeouts:     {direct_metrics['timeouts']}")
    
    print(f"\nREACT AGENT:")
    print(f"  Pass@1:       {react_metrics['pass_at_1']:.1%}")
    print(f"  Fixed:        {react_metrics['fixed']}/{react_metrics['total']}")
    print(f"  Avg time:     {react_metrics['avg_time']:.2f}s")
    print(f"  Timeouts:     {react_metrics['timeouts']}")
    
    # Head-to-head
    both_correct = results['both_correct']
    only_direct = results['only_direct']
    only_react = results['only_react']
    both_wrong = results['both_wrong']
    
    print(f"\nHEAD-TO-HEAD:")
    print(f"  Both correct:      {both_correct}")
    print(f"  Only Direct won:   {only_direct}")
    print(f"  Only React won:    {only_react}")
    print(f"  Both failed:       {both_wrong}")
    
    winner = "DirectAgent" if direct_metrics['pass_at_1'] > react_metrics['pass_at_1'] else \
             "ReactAgent" if react_metrics['pass_at_1'] > direct_metrics['pass_at_1'] else "TIE"
    
    print(f"\nWINNER: {winner}")
    print("=" * 70)


if __name__ == "__main__":
    main()