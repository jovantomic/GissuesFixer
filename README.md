# GissuesFixer - LLM-based Python Code Repair

AI agent for automatically fixing buggy Python code, evaluated on HumanEvalFix benchmark.

## Results

**Direct Agent: 63.8% Pass@1** (104/163 fixed, 19.01s avg)

I also tried a ReAct-style agent that uses iterative reasoning (Thought → Action → Observation loops), but it performed worse at 56.4% Pass@1. I initially experimented with tool calling as well, but that was even worse, so I removed it. The simple direct approach with a single LLM call turned out most reliable.

## Setup

```bash
git clone https://github.com/jovantomic/GissuesFixer.git
cd gissuesfixer
pip install -r requirements.txt
echo "GEMINI_API_KEY=your_key_here" > .env
python data/download_dataset.py
```

## Running

```bash
python run_evaluation.py
```


## Structure

```
src/
├── agents/
│   ├── direct_agent.py      # Single-shot prompting (main)
│   ├── react_agent.py       # ReAct reasoning loops
│   └── orchestrator.py      
├── evaluator.py             # Runs benchmark
├── executor.py              # Sandboxed code execution
└── pipeline.py              

data/
├── humaneval_fix.jsonl      
└── download_dataset.py      
```

## Approach

**Direct Agent** sends the buggy code to Gemini Flash with a structured prompt (understand → analyze → fix) and gets back the fixed code in one shot.

**ReAct Agent** implements the ReAct pattern - the model iteratively reasons about the problem, decides on actions, observes results, and refines its approach. In practice, this multi-step process introduced more failure points without improving fix quality.

Both use subprocess isolation for safe code execution.

## Tech

- Gemini Flash (via langchain-google-genai)
- LangGraph for ReAct agent implementation
- HumanEvalFix dataset (164 Python problems)
