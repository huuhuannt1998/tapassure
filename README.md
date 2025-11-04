# TAPAssure: Safe Automation in Smart Homes with LLMs and Formal Verification

[![Conference](https://img.shields.io/badge/SmartSP-2025-blue)](https://smartsp2025.github.io/)
[![Paper](https://img.shields.io/badge/Paper-Accepted-success)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)]()

**TAPAssure** is a novel framework that combines Large Language Models (LLMs) with formal verification to ensure the safety and correctness of Trigger-Action Programming (TAP) rules in smart home environments. By integrating LLM-based rule generation with NuSMV model checking, TAPAssure systematically eliminates syntax errors and safety violations through iterative refinement.

**📄 Published at:** SmartSP 2025 (International Workshop on Security, Privacy, and Trust in the IoT)

**👥 Authors:** Huan Bui¹, Chenglong Fu¹, and Fei Zuo²
- ¹ The University of North Carolina at Charlotte
- ² The University of Central Oklahoma

This repository contains the source code, evaluation dataset, and experimental results for our accepted paper:

> **TAPAssure: Safe Automation in Smart Homes with LLMs and Formal Verification**  
> Huan Bui, Chenglong Fu, and Fei Zuo  
> *Proceedings of SmartSP 2025*

## 🎯 Key Contributions

1. **Novel Architecture:** First framework combining LLMs with formal verification specifically for smart home automation, addressing the fundamental tension between usability and safety.

2. **Iterative Refinement Mechanism:** Uses NuSMV model checker counterexamples to guide LLM-based rule regeneration, ensuring convergence to safe configurations.

3. **Comprehensive Evaluation:** Demonstrated effectiveness across 120 test cases using Meta Llama 3.3 70B and Qwen2.5-14B, achieving up to 100% success in finding safe, verifiable configurations.

4. **Practical Insights:** Provides empirical evidence on the strengths and limitations of different LLMs for safety-critical rule generation.

## ✨ Features

* **Two-Phase Verification:** 
  - **Phase 1:** Context validation and syntax verification (iterative syntax error correction)
  - **Phase 2:** Safety violation detection and minimization (iterative refinement based on counterexamples)

* **Formal Safety Guarantees:** Uses NuSMV symbolic model checker to verify Linear Temporal Logic (LTL) safety properties.

* **Counterexample-Guided Refinement:** Automatically translates formal counterexamples into natural language prompts to guide LLM corrections.

* **Context-Aware Generation:** Integrates with SmartThings API to resolve ambiguous device references and ground rules in real-world IoT context.

* **Multiple LLM Support:** Evaluated with state-of-the-art open-weight models (Meta Llama 3.3 70B, Qwen2.5-14B) for reproducible experimentation.

## 🏗️ Architecture

TAPAssure operates through a two-phase architecture that ensures both syntactic correctness and semantic safety:

```
┌─────────────────────────────────────────────────────────────────┐
│                   USER INPUT (Natural Language)                  │
│              Scenarios + Safety Properties                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 1: CONTEXT VALIDATION & SYNTAX CHECK          │
├─────────────────────────────────────────────────────────────────┤
│  1. Device Context Verification (SmartThings API)               │
│  2. Scenario Validation (completeness & device references)       │
│  3. Safety Property Validation                                   │
│  4. NuSMV Model Generation (LLM)                                │
│  5. Iterative Syntax Refinement (until valid)                   │
│     • Qwen2.5: Median 3.5 iterations, Avg 9.92                  │
│     • Llama 3.3: Consistent performance                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ✓ Syntactically Valid Model
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         PHASE 2: VIOLATION MINIMIZATION & REFINEMENT            │
├─────────────────────────────────────────────────────────────────┤
│  1. Formal Verification (NuSMV Model Checker)                   │
│  2. LTL Safety Property Checking                                │
│  3. Counterexample Generation (when violations found)            │
│  4. Counterexample → Natural Language Translation               │
│  5. Iterative Model Regeneration (LLM-guided)                   │
│     • Llama 3.3: Avg 5.48 iterations, 100% success rate         │
│     • Qwen2.5: Effective with occasional outliers               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ✓ Safe & Verified Model
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT (Optional)                         │
│           Generate TAP Rules → SmartThings Platform              │
└─────────────────────────────────────────────────────────────────┘
```

### Why Two Phases?

**Traditional LLM-only approach** (Figure 1, left): Users interact directly with LLMs, which may generate unsafe or incomplete rules without verification.

**Manual rule creation** (Figure 1, middle): Users manually write rules through platforms like IFTTT, requiring technical expertise and offering no safety guarantees.

**TAPAssure approach** (Figure 1, right): Combines the usability of natural language interaction with formal safety guarantees through systematic verification and refinement.

## 📊 Evaluation Results

TAPAssure was evaluated on **120 test cases** using two state-of-the-art LLMs:

### Model Performance

| Model | Phase | Median Iterations | Average Iterations | Success Rate |
|-------|-------|-------------------|-------------------|--------------|
| **Qwen2.5-14B** | Syntax Correction | 3.5 | 9.92* | High |
| **Llama 3.3 70B** | Violation Minimization | ~5 | 5.48 | **100%** |

*Note: Qwen2.5 average is higher due to occasional outliers (e.g., 53 iterations in complex cases)

### Key Findings

✅ **Qwen2.5-14B Instruct:**
- Excels at resolving syntax errors efficiently
- Median of 3.5 iterations for syntax correction
- Occasional outliers increase average to 9.92 iterations
- Effective for Phase 1 (syntax verification)

✅ **Meta Llama 3.3 70B Instruct:**
- Superior performance in minimizing safety violations
- Consistent average of 5.48 iterations
- **100% pass rate** in achieving safe configurations
- Excels in Phase 2 (violation minimization)

✅ **Overall Success:**
- Both models successfully converge to safe, verifiable configurations
- Demonstrates effectiveness of counterexample-guided refinement
- Validates the two-phase architecture approach

### Test Case Composition

The evaluation includes:
- **3 scenario sets** with varying complexity (5-8 scenarios each)
- **4 safety property sets** (4-5 properties each)
- **12 unique combinations** tested 10 times each
- Coverage of basic automation, temperature control, multi-room setups, and complex constraints

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+**
- **NuSMV Model Checker** (must be in system PATH)
- **SmartThings Account** (for device context validation)
- **LLM API Access** (Lambda Labs, OpenAI, or compatible endpoint)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/huuhuannt1998/tapassure.git
    cd tapassure
    ```

2.  **Set up the environment:**
    It is recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    
    Required packages:
    - `requests` - API communication
    - `python-dotenv` - Environment configuration
    - `langchain` - LLM orchestration
    - `langchain-openai` - OpenAI integration
    - `openai` - OpenAI client
    - `pyyaml` - YAML processing

4.  **Install NuSMV:**
    Download and install NuSMV from http://nusmv.fbk.eu/
    Ensure `NuSMV` is in your system PATH:
    ```bash
    NuSMV --help  # Should display help information
    ```

5.  **Configure API Keys:**
    Create an `api_key.txt` file with your LLM API key:
    ```bash
    echo "your-api-key-here" > api_key.txt
    ```
    
    Or use environment variables:
    ```bash
    export OPENAI_API_KEY="your-api-key-here"
    ```

6.  **Configure SmartThings (Optional):**
    Update `SMARTTHINGS_BEARER_TOKEN` in `main.py` with your SmartThings API token.

### Quick Start

Run TAPAssure with predefined test cases:

```bash
python main.py
```

**Interactive Prompts:**
1. Choose to use predefined test data (recommended for first run)
2. Select a test case (1-4) with varying complexity
3. Monitor Phase 1: Syntax verification progress
4. Monitor Phase 2: Violation minimization progress
5. Optionally deploy verified rules to SmartThings

**Expected Output:**
```
======================================================================
TAPASSURE: SMART HOME AUTOMATION SAFETY VERIFICATION SYSTEM
======================================================================

PHASE 1: GENERATING SYNTACTICALLY VALID NUSMV MODEL
--- Iteration 1 ---
✅ SUCCESS! Syntactically valid model generated after 1 iteration(s)

PHASE 2: MINIMIZING VIOLATIONS THROUGH ITERATIVE REFINEMENT
--- Iteration 1 ---
❌ 3 violation(s) detected
--- Iteration 2 ---
✅ SUCCESS! All safety properties satisfied after 2 iteration(s)

✅ TAPASSURE COMPLETED SUCCESSFULLY
✓ Safe and verified model: final_safe_model.smv
```

## 📁 Repository Structure

```
tapassure/
├── main.py                          # Combined two-phase system
├── llama-syntax.py                  # Phase 1: Syntax verification
├── llama-violation.py               # Phase 2: Violation minimization
├── MAIN_COMBINED_README.md          # Detailed documentation
├── INTEGRATION_SUMMARY.md           # Integration explanation
├── QUICK_REFERENCE.md               # Quick reference guide
│
├── Ground-Truth/                    # Test cases and ground truth models
│   ├── 1-1.smv, 1-2.smv, ...       # Scenario-property combinations
│   └── analyze.py                   # Analysis scripts
│
├── Ground-Truth-NuSMV-llama/        # Llama 3.3 test results
├── Ground-Truth-NuSMV-qwq/          # Qwen2.5 test results
├── Llama-Violation-Result/          # Violation minimization results
│
├── scenarios.yaml                   # Sample TAP rules
├── safety_properties.text           # Safety property examples
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## 🔬 Reproducing Experiments

### Running Evaluation

To reproduce the paper's experiments:

```bash
# Test with Qwen2.5 (Phase 1 - Syntax)
python qwq-syntax.py

# Test with Llama 3.3 (Phase 2 - Violations)
python llama-violation.py

# Run complete pipeline
python main.py
```

### Test Cases

The repository includes 12 test case combinations:
- **Scenarios:** scenarios1, scenarios2, scenarios3 (5-8 rules each)
- **Safety Properties:** properties1, properties2, properties3, properties4 (4-5 constraints each)

Each combination is tested 10 times to measure consistency.

### Analyzing Results

```bash
cd Ground-Truth
python analyze.py
```

This generates statistics on:
- Iteration counts per test case
- Success rates
- Average and median performance
- Convergence patterns

## 🔍 Key Components

### Phase 1: Syntax Verification

**Files:** `llama-syntax.py`, integrated in `main.py`

**Process:**
1. Validates device context via SmartThings API
2. Checks scenario completeness (trigger, condition, action)
3. Validates safety property references
4. Generates initial NuSMV model from natural language
5. Iteratively fixes syntax errors until valid

**LLM Usage:** Translates natural language to formal NuSMV code

### Phase 2: Violation Minimization

**Files:** `llama-violation.py`, integrated in `main.py`

**Process:**
1. Runs NuSMV model checker on syntactically valid model
2. Detects LTL safety property violations
3. Extracts counterexamples showing violation traces
4. Translates counterexamples to natural language prompts
5. Regenerates model with LLM guidance
6. Repeats until all safety properties satisfied

**LLM Usage:** Regenerates models based on counterexample feedback

### Model Checking with NuSMV

TAPAssure uses **NuSMV**, a symbolic model checker that:
- Verifies Linear Temporal Logic (LTL) properties
- Generates counterexamples for violations
- Provides formal safety guarantees
- Handles complex state spaces efficiently

**Example Safety Property:**
```
LTLSPEC G (!(window_open & heater_on))
```
*"Globally, it should never be the case that the window is open and the heater is on."*

## ⚠️ Known Limitations

As discussed in the paper, TAPAssure has some limitations:

### 1. Privacy Concerns
- Current prototype uses cloud-based LLM inference
- Sensitive smart home data is sent to external APIs
- **Future work:** Local deployment of smaller models or secure execution environments

### 2. Scalability Challenges
- Some complex cases require many iterations (e.g., 53 with Qwen2.5)
- Iteration count can vary significantly
- **Future work:** More efficient prompting strategies and constrained decoding

### 3. Model Dependency
- Performance varies between different LLMs
- Qwen2.5 better for syntax, Llama 3.3 better for violations
- Proprietary models (GPT-4, Claude) not evaluated due to reproducibility concerns

### 4. Context Window Limitations
- Large models with extensive counterexamples may exceed context limits
- Complex scenarios may require prompt compression

## 🚀 Future Work

Based on the paper's discussion and experimental insights:

1. **Local Model Deployment**
   - Deploy smaller open-weight models locally
   - Implement secure execution environments for privacy

2. **Improved Prompting Strategies**
   - More efficient prompt engineering
   - Constrained decoding to reduce iteration counts
   - Few-shot learning with successful examples

3. **Hybrid Approaches**
   - Combine multiple LLMs (Qwen for syntax, Llama for violations)
   - Ensemble methods for improved reliability

4. **Extended Evaluation**
   - Test with more LLMs (including proprietary models in controlled settings)
   - Larger-scale real-world deployments
   - User studies on usability

5. **Enhanced Verification**
   - Support for more complex temporal properties
   - Probabilistic model checking
   - Runtime verification capabilities

## 📖 Citation

If you use TAPAssure in your research, please cite our paper:

```bibtex
@inproceedings{bui2025tapassure,
  title={TAPAssure: Safe Automation in Smart Homes with LLMs and Formal Verification},
  author={Bui, Huan and Fu, Chenglong and Zuo, Fei},
  booktitle={Proceedings of the International Workshop on Security, Privacy, and Trust in the IoT (SmartSP)},
  year={2025},
  organization={IEEE}
}
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👥 Authors

- **Huan Bui** - The University of North Carolina at Charlotte - [hbui11@charlotte.edu](mailto:hbui11@charlotte.edu)
- **Chenglong Fu** - The University of North Carolina at Charlotte - [chenglong.fu@charlotte.edu](mailto:chenglong.fu@charlotte.edu)
- **Fei Zuo** - The University of Central Oklahoma - [fzuo@uco.edu](mailto:fzuo@uco.edu)

## 🙏 Acknowledgments

- SmartSP 2025 workshop organizers and reviewers
- NuSMV development team for the model checker
- Meta AI for Llama 3.3 70B Instruct
- Alibaba Cloud for Qwen2.5-14B-Instruct
- SmartThings platform for API access

## 📞 Contact

For questions, issues, or collaborations:
- Open an issue on GitHub
- Email: hbui11@charlotte.edu

## 🔗 Related Work

TAPAssure builds upon research in:
- **Formal Verification:** Model checking, LTL verification
- **Smart Home Security:** TAP rule safety, IoT automation
- **LLM Applications:** Code generation, iterative refinement
- **Human-AI Interaction:** Natural language interfaces for IoT

## 📚 Additional Resources

- **Paper:** [Link to SmartSP 2025 proceedings when available]
- **NuSMV Documentation:** http://nusmv.fbk.eu/
- **SmartThings API:** https://developer.smartthings.com/
- **Llama 3.3:** https://ai.meta.com/llama/
- **Qwen2.5:** https://github.com/QwenLM/Qwen2.5

---

**Note:** This is research software. While TAPAssure demonstrates the effectiveness of combining LLMs with formal verification for smart home automation, it should be thoroughly tested before production deployment. Always review generated rules before deploying them to actual smart home systems.

**Conference Publication:** This work has been accepted for publication at SmartSP 2025 (International Workshop on Security, Privacy, and Trust in the IoT).


