import subprocess
import sys
import tempfile
import os


class CodeExecutor:
    
    def __init__(self, timeout=5):
        self.timeout = timeout
    
    def run(self, code: str, test: str = "", entry_point: str = None) -> dict:
        if test and entry_point:
            full_code = f'''{code}

{test}

try:
    check({entry_point})
    print("__TEST_PASSED__")
except AssertionError as e:
    print(f"__TEST_FAILED__: {{str(e)}}")
    sys.exit(1)
except NameError as e:
    print(f"__EXECUTION_ERROR__: NameError: {{str(e)}}")
    sys.exit(2)
except Exception as e:
    print(f"__EXECUTION_ERROR__: {{type(e).__name__}}: {{str(e)}}")
    sys.exit(2)
'''
        else:
            full_code = code
        
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.py', 
            delete=False, 
            encoding='utf-8'
        ) as f:
            f.write(full_code)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            stdout = result.stdout
            
            if '__TEST_PASSED__' in stdout:
                return {
                    'success': True,
                    'output': stdout,
                    'error': None
                }
            
            if '__TEST_FAILED__' in stdout:
                msg = stdout.split('__TEST_FAILED__: ')[1].strip()
                return {
                    'success': False,
                    'output': '',
                    'error': f"Test failed: {msg}"
                }
            
            if '__EXECUTION_ERROR__' in stdout:
                msg = stdout.split('__EXECUTION_ERROR__: ')[1].strip()
                if 'NameError' in msg and entry_point and entry_point in msg:
                    return {
                        'success': False,
                        'output': '',
                        'error': f"Function '{entry_point}' not defined"
                    }
                return {
                    'success': False,
                    'output': '',
                    'error': msg
                }
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'output': stdout,
                    'error': result.stderr
                }
            
            return {
                'success': True,
                'output': stdout,
                'error': None
            }
        
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'error': 'Timeout: execution exceeded limit'
            }
        
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': f"Execution error: {str(e)}"
            }
        
        finally:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass