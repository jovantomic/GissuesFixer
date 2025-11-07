import json
import time
import signal
from typing import List, Dict
from src.agents import DirectAgent, ReactAgent
from src.executor import CodeExecutor


class TimeoutException(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutException()


class ABTestEvaluator:
    """A/B testing: both agents on SAME problems"""
    
    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self.executor = CodeExecutor()

    
        self.direct_agent = DirectAgent(api_key)
        self.react_agent = ReactAgent(api_key)
    
    def load_dataset(self, path: str, sample_size: int = None) -> List[Dict]:
        """Load HumanEvalFix JSONL dataset"""
        problems = []
        
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    problems.append(json.loads(line))
        
        if sample_size:
            problems = problems[:sample_size]
        
        print(f"Loaded {len(problems)} problems\n")
        return problems
    
    def run_ab_test_same_problems(self, dataset_path: str, sample_size: int) -> Dict:
        """Both agents test SAME problems"""
        
        problems = self.load_dataset(dataset_path, sample_size)
        
        
        # Test DirectAgent first
        print("=" * 70)
        print(f"ROUND 1: TESTING DIRECT AGENT ({len(problems)} problems)")
        print("=" * 70)
        direct_results = self._test_agent(
            self.direct_agent, 
            problems, 
            "DirectAgent",
            use_validation=True
        )
        
        # Test ReactAgent on SAME problems
        print("\n" + "=" * 70)
        print(f"ROUND 2: TESTING REACT AGENT ({len(problems)} problems)")
        print("=" * 70)
        react_results = self._test_agent(
            self.react_agent, 
            problems, 
            "ReactAgent",
            use_validation=False
        )
        
        
        both_correct = 0
        only_direct = 0
        only_react = 0
        both_wrong = 0
        
        for i in range(len(problems)):
            direct_success = direct_results['results'][i]['success']
            react_success = react_results['results'][i]['success']
            
            if direct_success and react_success:
                both_correct += 1
            elif direct_success and not react_success:
                only_direct += 1
            elif not direct_success and react_success:
                only_react += 1
            else:
                both_wrong += 1
        
        return {
            'direct_agent_metrics': direct_results['metrics'],
            'react_agent_metrics': react_results['metrics'],
            'direct_agent_results': direct_results['results'],
            'react_agent_results': react_results['results'],
            'both_correct': both_correct,
            'only_direct': only_direct,
            'only_react': only_react,
            'both_wrong': both_wrong
        }
    
    def _test_agent(self, agent, problems: List[Dict], agent_name: str, use_validation: bool) -> Dict:
        """Test a single agent on problems"""
        
        results = []
        total_time = 0
        timeouts = 0
        
        for i, problem in enumerate(problems, 1):
            task_id = problem.get('task_id', f'Problem_{i}')
            buggy_code = problem.get('buggy_code', '')
            test_code = problem.get('test', '')
            entry_point = problem.get('entry_point', '')
            
            initial_result = self.executor.run(buggy_code, test_code, entry_point)
            error = initial_result.get('error', 'Tests failed')
            
            print(f"[{i}/{len(problems)}] {task_id}")
            
            start = time.time()
            
            try:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.timeout)
                
                if use_validation:
                    fix_result = agent.fix(buggy_code, error, test_code, entry_point)
                    fixed_code = fix_result['fixed_code']
                    success = fix_result['confidence'] >= 80
                else:
                    # ReactAgent
                    fixed_code = agent.fix(buggy_code, error)
                    # Test the fix
                    test_result = self.executor.run(fixed_code, test_code, entry_point)
                    success = test_result['success']
                
                # Cancel alarm
                signal.alarm(0)
                elapsed = time.time() - start
                
            except TimeoutException:
                signal.alarm(0)
                elapsed = self.timeout
                success = False
                timeouts += 1
            
            except Exception as e:
                signal.alarm(0)
                elapsed = time.time() - start
                success = False
                print(f"  ❌ error: {str(e)[:50]}")
            
            total_time += elapsed
            
            status = "✅" if success else "❌"
            print(f"  {status} {agent_name.lower()} ({elapsed:.2f}s)")
            
            results.append({
                'task_id': task_id,
                'success': success,
                'time': elapsed
            })
        
        total = len(results)
        fixed = sum(1 for r in results if r['success'])
        
        metrics = {
            'total': total,
            'fixed': fixed,
            'failed': total - fixed,
            'pass_at_1': fixed / total if total > 0 else 0,
            'avg_time': total_time / total if total > 0 else 0,
            'timeouts': timeouts
        }
        
        return {
            'metrics': metrics,
            'results': results
        }
