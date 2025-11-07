from src.executor import CodeExecutor
from src.agents import AgentOrchestrator
import time
import os


class BugFixPipeline:
    """Pipeline using confidence-based agent orchestration"""
    
    def __init__(self, api_key: str = None):
        self.executor = CodeExecutor()
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.orchestrator = AgentOrchestrator(self.api_key)
        
        self.stats = {
            'total': 0,
            'fixed': 0,
            'failed': 0
        }
    
    def fix_bug(self, buggy_code: str, test_case: str = "", entry_point: str = None) -> dict:
        """Main pipeline entry point"""
        start_time = time.time()
        self.stats['total'] += 1
        
        # Get initial error
        if test_case and entry_point:
            result = self.executor.run(buggy_code, test_case, entry_point)
            error = result.get('error', 'Tests failed')
        else:
            error = 'Code contains bugs'
        
        # Fix using orchestrator
        fix_result = self.orchestrator.fix(buggy_code, error, test_case, entry_point)
        fixed_code = fix_result['fixed_code']
        method = fix_result['method']
        
        # Validate fix
        if test_case and entry_point:
            result = self.executor.run(fixed_code, test_case, entry_point)
            if result['success']:
                self.stats['fixed'] += 1
                if method == 'direct':
                    self.orchestrator.stats['direct_success'] += 1
                else:
                    self.orchestrator.stats['react_success'] += 1
                
                return {
                    'success': True,
                    'fixed_code': fixed_code,
                    'method': method,
                    'confidence': fix_result.get('confidence'),
                    'time': time.time() - start_time
                }
            
            print(f"  Fix validation failed: {result['error'][:80]}")
        
        self.stats['failed'] += 1
        return {
            'success': False,
            'fixed_code': fixed_code,
            'method': 'failed',
            'time': time.time() - start_time
        }
