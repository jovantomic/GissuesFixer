from datasets import load_dataset
import json
import os

def download_humaneval_fix():
    """Downloads HumanEvalFix dataset from Hugging Face and converts to JSONL format"""
    
    print("Downloading HumanEvalFix dataset...")
    
    try:
        dataset = load_dataset("eitanturok/humaneval-fix-starcoder", split="test")
        print(f"Loaded {len(dataset)} problems")
        
        os.makedirs('data', exist_ok=True)
        problems = []
        
        for i, item in enumerate(dataset):
            problem = {
                'task_id': item.get('task_id', f"HumanEvalFix/{i}"),
                'prompt': item.get('prompt', ''),
                'entry_point': item.get('entry_point', ''),
                'canonical_solution': item.get('canonical_solution', ''),
                'test': item.get('test', ''),
                'test_inputs': item.get('test_inputs', []),
                'test_outputs': item.get('test_outputs', []),
                'language': item.get('language', 'python')
            }
            
            # Extract buggy code from prompt
            prompt = item.get('prompt', '')
            if 'Fix bugs in' in prompt:
                parts = prompt.split('Fix bugs in')
                problem['buggy_code'] = parts[0].strip() if len(parts) >= 2 else ''
            else:
                problem['buggy_code'] = ''
            
            problem['fixed_code'] = item.get('canonical_solution', '')
            problems.append(problem)
        
        # Save as JSONL
        output_path = 'data/humaneval_fix.jsonl'
        with open(output_path, 'w', encoding='utf-8') as f:
            for problem in problems:
                f.write(json.dumps(problem, ensure_ascii=False) + '\n')
        
        print(f"Dataset saved to {output_path}")
        print(f"Total problems: {len(problems)}")
        
        return len(problems)
        
    except Exception as e:
        print(f"Error downloading dataset: {e}")
        return 0

if __name__ == "__main__":
    count = download_humaneval_fix()
    if count > 0:
        print(f"Ready to run evaluation on {count} problems")
    else:
        print("Download failed. Check your internet connection and try again.")