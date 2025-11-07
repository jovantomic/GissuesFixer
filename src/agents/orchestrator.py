from .direct_agent import DirectAgent
from .react_agent import ReactAgent
import os


class AgentOrchestrator:
    """
    Smart orchestrator: DirectAgent validates fixes before reporting confidence.
    Only uses DirectAgent result if tests actually pass.
    """
    
    def __init__(self, api_key: str, confidence_threshold: int = 80):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.confidence_threshold = confidence_threshold
        
        self.direct_agent = DirectAgent(self.api_key)
        self.react_agent = None
        
        self.stats = {
            'direct_used': 0,
            'react_used': 0,
            'direct_success': 0,
            'react_success': 0
        }
    
    def fix(self, code: str, error: str, test_code: str = "", entry_point: str = None) -> dict:
        """
        Orchestrate fix with validation-based confidence.
        """
        
        print(f"  [DirectAgent] Attempting fix and validation...")
        
        # DirectAgent validates fix internally
        direct_result = self.direct_agent.fix(code, error, test_code, entry_point)
        
        confidence = direct_result['confidence']
        reasoning = direct_result['reasoning']
        fixed_code = direct_result['fixed_code']
        
        print(f"    Confidence: {confidence}%")
        print(f"    Reasoning: {reasoning[:100]}...")
        
        if confidence >= self.confidence_threshold:
            self.stats['direct_used'] += 1
            print(f"  ✓ Validated fix - using DirectAgent")
            
            return {
                'fixed_code': fixed_code,
                'method': 'direct',
                'confidence': confidence,
                'reasoning': reasoning
            }
        
        else:
            self.stats['react_used'] += 1
            print(f"  ⚠ Validation failed - escalating to ReactAgent")
            
            if self.react_agent is None:
                self.react_agent = ReactAgent(self.api_key)
            
            self.react_agent._current_test = test_code
            self.react_agent._current_entry_point = entry_point
            
            context = f"DirectAgent attempted fix but failed: {reasoning}"
            react_fixed = self.react_agent.fix(code, error, context)
            
            return {
                'fixed_code': react_fixed,
                'method': 'react',
                'confidence': None,
                'reasoning': f'Escalated. {reasoning}'
            }
