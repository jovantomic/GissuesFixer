from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
import os
import re


class ReactAgent:
    """
    Advanced reasoning agent without tools - pure prompt engineering.
    Uses chain-of-thought reasoning to fix complex bugs.
    """
    
    def __init__(self, api_key: str):
        api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.1
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Python debugger using systematic reasoning.

REASONING PROCESS:
1. ANALYZE: What does the error tell us?
2. INSPECT: Read the code line by line
3. HYPOTHESIZE: What could cause this behavior?
4. VERIFY: Does the hypothesis explain all symptoms?
5. FIX: Apply minimal correction

COMMON HUMANEVAL BUG PATTERNS:
- Off-by-one: range(lower, upper) needs range(lower, upper+1) for inclusive
- Boundary logic: max(2, min(a,b)) limits incorrectly - should be min(a,b) and max(a,b)
- Comparison: < should be <=, > should be >=
- Missing return or wrong return value
- Initialization: starting at wrong value (0 vs 1)
- Operator: max/min swapped, +/- wrong, * vs +

CRITICAL RULES:
- Return COMPLETE function with 'def' keyword
- Keep EXACT original function signature
- Fix ONLY the bug, preserve everything else
- Think step-by-step before fixing"""),
            ("user", """Fix this buggy code using systematic reasoning:
```python
{code}
```

Error: {error}
{context}

Think through the problem step-by-step:
1. What is the error telling us?
2. What does the code currently do?
3. What should it do instead?
4. What is the minimal fix?

Then provide ONLY the complete fixed function.""")
        ])
        
        self.chain = self.prompt | self.llm
        self._current_test = ""
        self._current_entry_point = ""
    
    def fix(self, code: str, error: str, context: str = None) -> str:
        """
        Fix code using chain-of-thought reasoning.
        
        Args:
            code: Buggy code
            error: Error message
            context: Optional context from DirectAgent
            
        Returns:
            str: Fixed code
        """
        context_text = f"\nPREVIOUS ATTEMPT:\n{context}" if context else ""
        
        try:
            response = self.chain.invoke({
                "code": code,
                "error": error,
                "context": context_text
            })
            
            content = response.content if hasattr(response, 'content') else str(response)
            fixed_code = self._extract_code(content, code)
            
            return fixed_code if fixed_code else code
            
        except Exception as e:
            print(f"    ReactAgent error: {e}")
            return code
    
    def _extract_code(self, text: str, original: str) -> str:
        """Extract Python code from response"""
        patterns = [
            r'```python\n(def .*?)```',
            r'```\n(def .*?)```',
            r'(def \w+\([^)]*\):.*?)(?:\n```|\n\n|\Z)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                code = match.group(1).strip()
                code = re.sub(r'```+\s*$', '', code).strip()
                if code.startswith('def '):
                    return code
        
        lines = text.split('\n')
        code_lines = []
        capturing = False
        
        for line in lines:
            if line.strip().startswith('def '):
                capturing = True
                code_lines.append(line)
            elif capturing:
                if line.strip() and not line.strip().startswith('```'):
                    code_lines.append(line)
                elif not line.strip() and len(code_lines) > 3:
                    break
        
        if code_lines:
            return '\n'.join(code_lines).strip()
        
        return original