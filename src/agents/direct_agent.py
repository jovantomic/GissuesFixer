from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from src.executor import CodeExecutor
import os
import re

class DirectAgent:
    """Enhanced agent with multi-attempt validation and better pattern recognition"""
    
    def __init__(self, api_key: str):
        api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",  # Upgraded model
            google_api_key=api_key,
            temperature=0.0,  # Deterministic for debugging
            timeout=30
        )
        self.executor = CodeExecutor(timeout=6)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Python debugger specializing in logic bugs.

CRITICAL PATTERNS - Check These First:
1. Off-by-one: range(a, b) vs range(a, b+1) for inclusive ranges
2. Boundary conditions: < vs <=, > vs >=
3. Edge cases: empty lists, single elements, None values
4. Return paths: ensure all branches return correct values
5. Loop logic: break/continue placement, loop counters
6. Math operators: +/-, *//, %/**, correct precedence
7. Comparison chains: a < b < c evaluation order
8. Index errors: list[i] when i might be out of bounds

DEBUGGING PROCESS:
1. Identify the EXACT error from tests
2. Trace logic flow step-by-step
3. Find the minimal change needed
4. Preserve all working logic

STRICT RULES:
- Return ONLY the complete fixed function
- Keep EXACT function signature (name, parameters, types)
- Maintain original indentation style
- NO explanations, NO comments, NO markdown
- Start with 'def' and end after function body"""),
            ("user", """Buggy code:
```python
{code}
```

Test failure: {error}

{context}

Return ONLY the fixed function code, nothing else.""")
        ])
        self.chain = self.prompt | self.llm
    
    def fix(self, code: str, error: str, test_code: str = "", entry_point: str = None) -> dict:
        """Fix with multi-attempt validation"""
        
        context = self._analyze_error(error, code)
        
        for attempt in range(2):
            try:
                response = self.chain.invoke({
                    "code": code,
                    "error": error,
                    "context": context if attempt == 0 else "Previous attempt failed. Try different approach."
                })
                
                content = response.content if hasattr(response, 'content') else str(response)
                fixed_code = self._extract_code(content, code)
                
                if test_code and entry_point:
                    result = self.executor.run(fixed_code, test_code, entry_point)
                    
                    if result['success']:
                        return {
                            'fixed_code': fixed_code,
                            'confidence': 95,
                            'reasoning': f'Validated (attempt {attempt + 1})'
                        }
                    elif attempt == 0:
                        error = result.get('error', error)
                        continue
                    else:
                        return {
                            'fixed_code': fixed_code,
                            'confidence': 25,
                            'reasoning': f'Failed after 2 attempts: {result["error"][:60]}'
                        }
                else:
                    return {
                        'fixed_code': fixed_code,
                        'confidence': 50,
                        'reasoning': 'No tests to validate'
                    }
                    
            except Exception as e:
                if attempt == 1:
                    return {
                        'fixed_code': code,
                        'confidence': 0,
                        'reasoning': f'Error: {str(e)[:60]}'
                    }
                continue
        
        return {
            'fixed_code': code,
            'confidence': 0,
            'reasoning': 'All attempts exhausted'
        }
    
    def _analyze_error(self, error: str, code: str) -> str:
        """Extract useful context from error"""
        hints = []
        
        error_lower = error.lower()
        
        if 'assertion' in error_lower or 'assert' in error_lower:
            hints.append("Test assertion failed - output doesn't match expected.")
        
        if 'index' in error_lower and 'out of range' in error_lower:
            hints.append("Index out of range - check loop bounds and list access.")
        
        if 'key' in error_lower and 'error' in error_lower:
            hints.append("KeyError - missing dictionary key check.")
        
        if 'none' in error_lower and 'type' in error_lower:
            hints.append("NoneType error - missing None check or wrong return.")
        
        if 'recursion' in error_lower:
            hints.append("RecursionError - check base case and termination.")
        
        if 'expected' in error_lower or '!=' in error:
            hints.append("Output mismatch - trace logic with failing test case.")
        
        if 'range(' in code and ('expected' in error_lower or 'assert' in error_lower):
            hints.append("LIKELY: Off-by-one error in range() - check inclusive/exclusive bounds.")
        
        if any(op in code for op in ['<', '>', '<=', '>=']):
            hints.append("Check comparison operators for boundary conditions.")
        
        return "HINTS: " + " ".join(hints) if hints else "Analyze the test failure carefully."
    
    def _extract_code(self, text: str, original: str) -> str:
        """Enhanced code extraction with fallbacks"""
        
        text = text.replace('```python', '```').replace('```Python', '```')
        
        patterns = [
            r'```\s*(def\s+\w+.*?)```',
            r'```\s*(def\s+\w+.*?)$',
            r'^(def\s+\w+.*?)(?:\n```|\n\n```|\Z)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
            if match:
                code = match.group(1).strip()
                if self._is_valid_function(code):
                    return code
        
        lines = []
        in_function = False
        indent_level = None
        
        for line in text.split('\n'):
            stripped = line.strip()
            
            if stripped.startswith('def '):
                in_function = True
                indent_level = len(line) - len(line.lstrip())
                lines.append(line)
            elif in_function:
                if stripped and not stripped.startswith('#'):
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent <= indent_level and stripped:
                        break
                lines.append(line)
                
                if not stripped and len(lines) > 5:
                    break
        
        if lines:
            code = '\n'.join(lines).strip()
            if self._is_valid_function(code):
                return code
        
        return original
    
    def _is_valid_function(self, code: str) -> bool:
        """Check if extracted code is a valid function"""
        if not code.strip().startswith('def '):
            return False
        
        first_line = code.split('\n')[0]
        if ':' not in first_line:
            return False
        
        if len(code.split('\n')) < 2:
            return False
        
        return True