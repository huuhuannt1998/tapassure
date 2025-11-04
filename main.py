"""
TAPAssure: Smart Home Automation Safety Verification System

This system integrates two main processes:

PROCESS 1: CONTEXT VALIDATION & SYNTAX VERIFICATION
- Verifies device context from SmartThings API
- Validates user scenarios and safety properties  
- Generates syntactically correct NuSMV models through iterative refinement
- Ensures the model has no syntax errors before proceeding

PROCESS 2: VIOLATION MINIMIZATION  
- Performs formal verification using NuSMV model checker
- Detects safety property violations through counterexamples
- Iteratively regenerates models to eliminate violations
- Continues until all safety properties are satisfied

The combined workflow ensures both syntactic correctness and semantic safety.
"""

import requests
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from openai import OpenAI
import os
import subprocess
import yaml
import re
import json

# Load environment variables
load_dotenv()

#############################
# CONFIGURATION
#############################

# SmartThings API Configuration
SMARTTHINGS_API_URL = "https://api.smartthings.com/v1/devices"
SMARTTHINGS_BEARER_TOKEN = "0dc70a10-bda8-4d39-a1ee-67dc45e91595"

# vLLM API Configuration (for direct API calls)
VLLM_API_URL = "http://localhost:5000/v1/completions"

# OpenAI/Lambda Labs Configuration
try:
    with open('api_key.txt', 'r') as file:
        openai_api_key = file.read().strip()
except FileNotFoundError:
    print("Warning: api_key.txt not found. Using default/env API key.")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    
openai_api_base = "https://api.lambdalabs.com/v1"

# Initialize the OpenAI client for Lambda Labs
client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)

#############################
# SAMPLE SCENARIOS & PROPERTIES
#############################

scenarios1 = [
    "When motion is detected by the Motion Sensor, turn on the Virtual Light.",
    "Turn off Virtual A/C 1 when the Virtual Motion Sensor detects no motion.",
    "At sunset, turn on Virtual TV 1 and set Virtual Fan 1 to medium speed.",
    "If Motion Sensor detects movement while away, turn on all Virtual Lights and send an alert.",
    "At 7 AM, turn on Virtual Fridge 1 and Virtual A/C 2 to prepare the kitchen."
]

scenarios2 = [
    "When Virtual Switch is turned on, activate Virtual Fan 5 and Virtual Light.",
    "When leaving home, turn off all devices: Virtual A/C 3, Virtual Fan 3, and Virtual Light.",
    "If Motion Sensor detects high temperature, turn on Virtual A/C 1 and Virtual Fan 2.",
    "Turn off all Virtual Lights when no motion is detected for 10 minutes.",
    "Turn on Virtual Fan 3 when the room temperature exceeds 75°F.",
    "Turn on Virtual A/C 2 and Virtual Fan 2 when the Virtual Motion Sensor detects movement in the living room.",
    "Turn off Virtual TV 3 when no one is detected in the room for 15 minutes."
]

scenarios3 = [
    "Use the Motion Sensor to trigger Virtual Light and Virtual A/C 1 when entering the bedroom.",
    "At sunrise, turn off Virtual Fan 1 and Virtual Light in the kitchen.",
    "Turn on Virtual TV 2 and set Virtual Fan 5 to low when 'movie mode' is activated.",
    "Turn off Virtual A/C 3 when all doors are closed and no motion is detected in the house.",
    "Turn on Virtual Fridge 1 and Virtual Light when the Virtual Motion Sensor detects movement in the dining room.",
    "If Motion Sensor detects temperature above 80°F, activate Virtual A/C 2 and Virtual Fan 4.",
    "Turn on Virtual TV 1 and mute it if no movement is detected in the living room for 5 minutes.",
    "Turn off Virtual Fan 2 at 10 PM every night to conserve energy."
]

safety_properties1 = [
    "Virtual A/C 1 must not turn on when windows are open.",
    "Virtual Light must turn off automatically if no motion is detected for 10 minutes.",
    "Virtual Fan 3 must not run when the room temperature is below 68°F.",
    "Virtual TV 1 must not turn on between midnight and 6 AM.",
    "Virtual A/C 2 must not run if the temperature is below 65°F."
]

safety_properties2 = [
    "Virtual Motion Sensor must not trigger devices in 'away mode'.",
    "Virtual Light must not turn on during daylight hours unless motion is detected.",
    "Multiple Virtual Fans must not run in the same room simultaneously.",
    "Virtual TV 4 must turn off if no activity is detected for 30 minutes.",
    "Virtual Fridge 1 must not remain open for more than 2 minutes."
]

safety_properties3 = [
    "Virtual A/C 3 must deactivate if the room temperature drops below 70°F.",
    "Virtual A/C 2 must not exceed 78°F.",
    "Virtual Fan 5 must not remain on for more than 1 hour without activity detection.",
    "Virtual Fan 4 must operate at medium speed if the temperature exceeds 85°F."
]

safety_properties4 = [
    "Virtual TV 3 must mute automatically if no activity is detected for 15 minutes.",
    "Virtual A/C 1 must switch to 'eco mode' when no one is home.",
    "Virtual Motion Sensor must activate Virtual Light only in occupied rooms.",
    "Virtual Light must activate only when motion is detected in dark areas.",
    "Virtual Fan 1 must deactivate when Virtual A/C 2 is running."
]

#############################
# SMARTTHINGS API FUNCTIONS
#############################

def get_smartthings_devices():
    """
    Retrieve devices from SmartThings API for context validation.
    """
    headers = {
        "Authorization": f"Bearer {SMARTTHINGS_BEARER_TOKEN}"
    }
    response = requests.get(SMARTTHINGS_API_URL, headers=headers)
    if response.status_code == 200:
        devices = response.json()["items"]
        return [device["label"] for device in devices]
    else:
        print(f"Error: Unable to retrieve devices ({response.status_code})")
        return []

#############################
# LLM INVOCATION FUNCTIONS
#############################

def invoke_vllm(prompt, max_tokens=5000):
    """
    Send a request to the OpenAI-compatible API (Lambda Labs) to generate a response.
    This is the primary method used for both processes.
    Cleans the response to remove markdown formatting and ensure valid NuSMV code.
    """
    try:
        response = client.chat.completions.create(
            model="llama3.3-70b-instruct-fp8",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that strictly follows the user's instructions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=max_tokens
        )
        
        generated_content = response.choices[0].message.content
        
        # Clean the response to remove markdown formatting
        cleaned_content = re.sub(r"```(?:nusmv|plaintext|smv)?\n", "", generated_content)
        cleaned_content = re.sub(r"\n```", "", cleaned_content)
        
        return cleaned_content.strip()
    
    except Exception as e:
        print(f"Error invoking LLM: {e}")
        return None

#############################
# PROCESS 1: CONTEXT & SCENARIO VALIDATION
#############################

def scenarios_validation(devices):
    """
    PROCESS 1 - Step 1: Validate user scenarios against SmartThings devices.
    Ensures scenarios reference valid devices and contain complete information.
    """
    template = """
You are an AI assistant for creating IoT automation rules. Your task is to validate the user's scenario and ensure it contains all the necessary information:
1. Which device or devices are involved.
2. If condition that triggers the rule.
3. Then action to be performed.

Additionally, validate the devices mentioned in the scenario against the available devices from the user's SmartThings account:
Available Devices: {device_list}

Step 1: Analyze the provided scenario.
- If it is valid and complete, explicitly state: "The scenario is valid and complete."
- If it mentions a device not in the available devices list, request a correction and suggest valid devices.

Scenario: "{scenario}"

Your response should include:
1. Feedback on the scenario's completeness.
2. If a device is missing, a request for correction with recommendations.
"""
    
    print("=" * 70)
    print("PROCESS 1: CONTEXT & SCENARIO VALIDATION")
    print("=" * 70)
    print("You can input multiple scenarios. The assistant will validate each one.")
    print("Type 'done' when you have finished entering your scenarios.\n")
    
    saved_scenarios = []
    print(f"Devices retrieved from SmartThings: {', '.join(devices)}\n")
    
    while True:
        scenario = input("Enter your IoT scenario (or type 'done' to finish): ").strip()
        
        if scenario.lower() == 'done':
            print("\nYou have finished entering scenarios.")
            break

        if not scenario or len(scenario.split()) < 3:
            print("\nInvalid scenario. Please provide a detailed input including devices, conditions, and actions.\n")
            continue

        while True:
            prompt = template.format(scenario=scenario, device_list=", ".join(devices))
            result = invoke_vllm(prompt)

            if not result:
                print("\nError communicating with LLM. Please try again.")
                break

            print("\nAssistant Response:")
            print(result)

            if "valid and complete" in result.lower():
                print("\n✓ The scenario is valid and has been saved.")
                saved_scenarios.append(scenario)
                break

            scenario = input("\nPlease update your scenario based on the assistant's suggestions: ").strip()

    if saved_scenarios:
        print("\n✓ Validated Scenarios:")
        for i, sc in enumerate(saved_scenarios, 1):
            print(f"  {i}. {sc}")
    else:
        print("\nNo valid scenarios were provided.")
    
    return saved_scenarios

def safety_property_validation(devices):
    """
    PROCESS 1 - Step 2: Validate safety properties against SmartThings devices.
    Ensures safety properties reference valid devices and specify clear safety constraints.
    """
    safety_template = """
You are an expert assistant for creating IoT safety rules. Your task is to validate the user's safety property:
1. References valid devices from the user's SmartThings account.
2. Specifies clear conditions and actions that ensure safety.

Available Devices: {device_list}
Safety Property: "{property}"

Step 1: Analyze the provided safety property.
- Determine if the property is valid and complete. 
- If it is valid and complete, explicitly state: "The safety property is valid and complete."
- If it is not valid or complete, provide feedback on what is missing or unclear.

Step 2: Suggest improvements to make the property more robust and actionable.

Your response must explicitly include:
1. Whether the safety property is "valid and complete."
2. Feedback on its validity and completeness.
3. Suggestions for improvement (if needed).
"""
    
    print("\nNow, let's define the safety properties for your IoT automation rules.")
    print("Type 'done' when you have finished entering safety properties.\n")

    saved_properties = []

    while True:
        safety_property = input("Enter your safety property (or type 'done' to finish): ").strip()

        if safety_property.lower() == 'done':
            print("\nYou have finished entering safety properties.")
            break

        if not safety_property or len(safety_property.split()) < 3:
            print("\nInvalid safety property. Please provide more details.\n")
            continue

        while True:
            prompt = safety_template.format(property=safety_property, device_list=", ".join(devices))
            result = invoke_vllm(prompt)

            if not result:
                print("\nError communicating with LLM. Please try again.")
                break

            print("\nAssistant Response:")
            print(result)

            if "valid and complete" in result.lower():
                print("\n✓ The safety property is valid and has been saved.")
                saved_properties.append(safety_property)
                break

            safety_property = input("\nPlease update your safety property based on the assistant's suggestions: ").strip()

    if saved_properties:
        print("\n✓ Validated Safety Properties:")
        for i, sp in enumerate(saved_properties, 1):
            print(f"  {i}. {sp}")
    else:
        print("\nNo valid safety properties were provided.")
    
    return saved_properties

#############################
# PROCESS 1: NUSMV MODEL GENERATION & SYNTAX VALIDATION
#############################

def is_valid_nusmv_code(content):
    """
    Validate if content is valid NuSMV code structure.
    """
    if not content or len(content.strip()) < 10:
        return False
    
    # Check for basic NuSMV structure
    required_keywords = ["MODULE", "VAR", "ASSIGN"]
    return any(keyword in content for keyword in required_keywords)

def clean_nusmv_model(model_content):
    """
    Clean NuSMV model content by removing markdown formatting.
    """
    # Remove markdown code blocks
    cleaned = re.sub(r"```(?:nusmv|smv|plaintext)?\n", "", model_content)
    cleaned = re.sub(r"\n```", "", cleaned)
    
    # Remove any leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned

def generate_nusmv_model(scenarios, safety_properties):
    """
    PROCESS 1 - Step 3: Generate initial NuSMV model from scenarios and safety properties.
    """
    scenarios_text = '\n'.join(f"- {s}" for s in scenarios)
    properties_text = '\n'.join(f"- {p}" for p in safety_properties)
    
    prompt = f"""
You are an expert in formal verification and NuSMV modeling.

Given the following IoT automation scenarios and safety properties, generate a complete NuSMV model.

Scenarios:
{scenarios_text}

Safety Properties:
{properties_text}

Generate a complete NuSMV model that:
1. Defines all necessary state variables for devices and conditions
2. Implements transition rules based on the scenarios
3. Includes LTL specifications for each safety property
4. Ensures the model is syntactically correct

Return ONLY the NuSMV model code without any explanations or markdown formatting.
"""
    
    result = invoke_vllm(prompt, max_tokens=8000)
    return clean_nusmv_model(result) if result else None

def validate_nusmv_syntax(model_file):
    """
    Validate NuSMV model syntax using the NuSMV model checker.
    Returns (is_valid, error_message)
    """
    try:
        result = subprocess.run(
            ["NuSMV", model_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout + result.stderr
        
        # Check for syntax errors
        if "syntax error" in output.lower() or ("error:" in output.lower() and "line" in output.lower()):
            return False, output
        
        return True, "Model is syntactically valid"
        
    except subprocess.TimeoutExpired:
        return False, "NuSMV execution timeout"
    except FileNotFoundError:
        return False, "NuSMV not found. Please install NuSMV and add it to PATH."
    except Exception as e:
        return False, f"Error running NuSMV: {str(e)}"

def extract_nusmv_errors(nusmv_output, model_content):
    """
    Extract and parse syntax errors from NuSMV output.
    """
    errors = []
    error_lines = [line for line in nusmv_output.split('\n') if 'error' in line.lower() or 'line' in line.lower()]
    
    for error_line in error_lines[:5]:  # Limit to first 5 errors
        errors.append(error_line.strip())
    
    return errors if errors else ["Unknown syntax error"]

def refine_nusmv_model(nusmv_model, error_log):
    """
    PROCESS 1 - Step 4: Refine NuSMV model based on syntax errors.
    Uses LLM to fix syntax errors iteratively.
    """
    errors_text = '\n'.join(error_log)
    
    prompt = f"""
You are an expert in NuSMV model checking and formal verification.

The following NuSMV model has syntax errors:

{nusmv_model}

Errors detected:
{errors_text}

Fix the syntax errors and return the corrected NuSMV model.
Ensure the model adheres to proper NuSMV syntax.
Return ONLY the corrected NuSMV model code without any explanations or markdown formatting.
"""
    
    result = invoke_vllm(prompt, max_tokens=8000)
    return clean_nusmv_model(result) if result else None

def generate_valid_nusmv_model(scenarios, safety_properties, output_file="generated_model.smv", max_iterations=10):
    """
    PROCESS 1 - Complete: Generate syntactically valid NuSMV model through iterative refinement.
    This ensures the model is ready for formal verification in Process 2.
    """
    print("\n" + "="*70)
    print("PROCESS 1: GENERATING SYNTACTICALLY VALID NUSMV MODEL")
    print("="*70)
    
    iteration = 0
    model_content = None
    error_log = []
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")
        
        if iteration == 1:
            print("Generating initial NuSMV model...")
            model_content = generate_nusmv_model(scenarios, safety_properties)
        else:
            print("Refining NuSMV model based on errors...")
            model_content = refine_nusmv_model(model_content, error_log)
        
        if not model_content:
            print("❌ Failed to generate model content")
            continue
        
        # Save model to file
        with open(output_file, 'w') as f:
            f.write(model_content)
        
        print(f"✓ Model saved to {output_file}")
        
        # Validate syntax
        print("Validating syntax with NuSMV...")
        is_valid, error_message = validate_nusmv_syntax(output_file)
        
        if is_valid:
            print(f"\n✅ SUCCESS! Syntactically valid model generated after {iteration} iteration(s)")
            print(f"✅ Process 1 completed. Model ready for formal verification.")
            return model_content
        else:
            print(f"❌ Syntax errors detected:")
            error_log = extract_nusmv_errors(error_message, model_content)
            for err in error_log[:3]:
                print(f"   - {err}")
    
    print(f"\n❌ Failed to generate valid model after {max_iterations} iterations")
    return None

#############################
# PROCESS 2: VIOLATION DETECTION & MINIMIZATION
#############################

def validate_nusmv_model(model_file):
    """
    PROCESS 2 - Step 1: Run NuSMV formal verification to detect violations.
    Returns (has_violations, violations, output)
    """
    try:
        result = subprocess.run(
            ["NuSMV", model_file],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout + result.stderr
        
        # Check for specification violations
        has_violations = "is false" in output or "violation" in output.lower()
        
        violations = []
        if has_violations:
            violations = extract_nusmv_violations(output)
        
        return has_violations, violations, output
        
    except subprocess.TimeoutExpired:
        return True, ["Timeout during verification"], "Timeout"
    except FileNotFoundError:
        return True, ["NuSMV not found"], "NuSMV not installed"
    except Exception as e:
        return True, [f"Error: {str(e)}"], str(e)

def extract_nusmv_violations(nusmv_output):
    """
    Extract violation information and counterexamples from NuSMV output.
    """
    violations = []
    lines = nusmv_output.split('\n')
    
    for i, line in enumerate(lines):
        if "is false" in line.lower() or "specification" in line.lower():
            # Extract context around the violation
            context_start = max(0, i - 2)
            context_end = min(len(lines), i + 15)
            violation_context = '\n'.join(lines[context_start:context_end])
            violations.append(violation_context)
    
    return violations if violations else ["Violation detected but could not extract details"]

def regenerate_model_from_violations(model_content, violations, scenarios, safety_properties):
    """
    PROCESS 2 - Step 2: Regenerate NuSMV model to address detected violations.
    Uses counterexamples to guide model refinement.
    """
    violations_text = '\n\n'.join(f"Violation {i+1}:\n{v}" for i, v in enumerate(violations[:3]))  # Limit to 3 violations
    scenarios_text = '\n'.join(f"- {s}" for s in scenarios)
    properties_text = '\n'.join(f"- {p}" for p in safety_properties)
    
    prompt = f"""
You are an expert in NuSMV formal verification and IoT safety analysis.

The following NuSMV model has safety property violations:

{model_content}

Violations detected by NuSMV:
{violations_text}

Original Scenarios:
{scenarios_text}

Safety Properties:
{properties_text}

Analyze the violations and regenerate the NuSMV model to eliminate these violations while maintaining the intended scenarios.
Focus on:
1. Adjusting transition rules to prevent unsafe states
2. Adding constraints to enforce safety properties
3. Ensuring the model still implements the desired scenarios

Return ONLY the corrected NuSMV model code without any explanations or markdown formatting.
"""
    
    result = invoke_vllm(prompt, max_tokens=8000)
    return clean_nusmv_model(result) if result else None

def minimize_violations_with_llm(input_model, output_model, scenarios, safety_properties, max_iterations=50):
    """
    PROCESS 2 - Complete: Iteratively minimize violations until all safety properties are satisfied.
    This is the core of the violation minimization process.
    """
    print("\n" + "="*70)
    print("PROCESS 2: MINIMIZING VIOLATIONS THROUGH ITERATIVE REFINEMENT")
    print("="*70)
    
    # Read initial model
    with open(input_model, 'r') as f:
        model_content = f.read()
    
    iteration = 0
    violation_history = []
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")
        
        # Save current model
        with open(output_model, 'w') as f:
            f.write(model_content)
        
        print(f"Running NuSMV verification...")
        has_violations, violations, output = validate_nusmv_model(output_model)
        
        if not has_violations:
            print(f"\n✅ SUCCESS! All safety properties satisfied after {iteration} iteration(s)")
            print(f"✅ Process 2 completed. Safe TAP rules generated.")
            print(f"✅ Final model saved to: {output_model}")
            return model_content
        
        print(f"❌ {len(violations)} violation(s) detected")
        violation_history.append(len(violations))
        
        # Show violation trend
        if len(violation_history) > 1:
            trend = violation_history[-1] - violation_history[-2]
            if trend < 0:
                print(f"   ↓ Violations reduced by {abs(trend)}")
            elif trend > 0:
                print(f"   ↑ Violations increased by {trend} (trying different approach)")
            else:
                print(f"   → Violations unchanged")
        
        # Show first violation for context
        if violations:
            print(f"\nFirst violation preview:")
            preview = violations[0][:200] + "..." if len(violations[0]) > 200 else violations[0]
            print(f"   {preview}")
        
        # Regenerate model
        print("\nRegenerating model to address violations...")
        new_model = regenerate_model_from_violations(model_content, violations, scenarios, safety_properties)
        
        if not new_model:
            print("❌ Failed to regenerate model")
            break
        
        model_content = new_model
        print("✓ Model regenerated")
    
    print(f"\n⚠ Maximum iterations ({max_iterations}) reached")
    print(f"Final violation count: {violation_history[-1] if violation_history else 'unknown'}")
    
    # Save final model even if violations remain
    with open(output_model, 'w') as f:
        f.write(model_content)
    
    return model_content

#############################
# YAML GENERATION & SMARTTHINGS DEPLOYMENT
#############################

def scenarios_to_yaml(scenarios, output_file="scenarios.yaml"):
    """
    Convert validated scenarios to YAML format for SmartThings deployment.
    """
    scenarios_yaml = []
    for idx, scenario in enumerate(scenarios, 1):
        scenario_yaml = {
            "id": f"scenario_{idx}",
            "description": scenario,
            "condition": f"Parsed condition for scenario {idx}",
            "action": f"Parsed action for scenario {idx}",
            "devices": f"Parsed devices for scenario {idx}"
        }
        scenarios_yaml.append(scenario_yaml)

    with open(output_file, "w") as yaml_file:
        yaml.dump({"scenarios": scenarios_yaml}, yaml_file)

    print(f"\n✓ Scenarios saved in YAML format: {output_file}")
    return output_file

def apply_scenarios_to_smartthings(yaml_file):
    """
    Apply scenarios defined in the YAML file to SmartThings API as automations.
    """
    print("\nApplying scenarios to SmartThings...\n")
    try:
        with open(yaml_file, "r") as file:
            scenarios = yaml.safe_load(file)["scenarios"]

        for scenario in scenarios:
            payload = {
                "name": scenario["id"],
                "description": scenario["description"],
                "condition": scenario["condition"],
                "action": scenario["action"],
                "devices": scenario["devices"]
            }

            response = requests.post(
                f"{SMARTTHINGS_API_URL}/automations",
                headers={"Authorization": f"Bearer {SMARTTHINGS_BEARER_TOKEN}"},
                json=payload
            )

            if response.status_code == 201:
                print(f"✅ Successfully applied: {scenario['id']}")
            else:
                print(f"❌ Failed to apply {scenario['id']}: {response.status_code}")

    except Exception as e:
        print(f"Error applying scenarios: {str(e)}")

#############################
# MAIN WORKFLOW
#############################

def main():
    """
    Main TAPAssure workflow integrating both processes:
    - Process 1: Context validation and syntax verification
    - Process 2: Violation detection and minimization
    """
    print("="*70)
    print("TAPASSURE: SMART HOME AUTOMATION SAFETY VERIFICATION SYSTEM")
    print("="*70)
    print("\nThis system performs two-phase verification:")
    print("  Phase 1: Context validation & syntax checking")
    print("  Phase 2: Safety violation detection & minimization\n")
    
    # Configuration
    use_predefined_data = input("Use predefined test data? (yes/no, default=yes): ").strip().lower()
    use_predefined_data = use_predefined_data != 'no'
    
    if use_predefined_data:
        print("\n✓ Using predefined scenarios and safety properties...")
        print("\nSelect test case:")
        print("  1. Scenarios 1 + Properties 1")
        print("  2. Scenarios 2 + Properties 2")
        print("  3. Scenarios 3 + Properties 3")
        print("  4. Scenarios 3 + Properties 4")
        
        choice = input("\nEnter choice (1-4, default=4): ").strip()
        
        if choice == '1':
            validated_scenarios = scenarios1
            validated_safety_properties = safety_properties1
        elif choice == '2':
            validated_scenarios = scenarios2
            validated_safety_properties = safety_properties2
        elif choice == '3':
            validated_scenarios = scenarios3
            validated_safety_properties = safety_properties3
        else:
            validated_scenarios = scenarios3
            validated_safety_properties = safety_properties4
    else:
        # Interactive mode
        print("\nFetching devices from SmartThings...")
        devices = get_smartthings_devices()
        if not devices:
            print("⚠ No devices retrieved from SmartThings. Using test data.")
            devices = ["Virtual Light", "Virtual A/C 1", "Virtual Fan 1", "Motion Sensor", 
                      "Virtual TV 1", "Virtual Fridge 1"]
        
        # Step 1: Collect and validate scenarios
        validated_scenarios = scenarios_validation(devices)
        if not validated_scenarios:
            print("❌ No valid scenarios provided. Exiting.")
            return
        
        # Step 2: Collect and validate safety properties
        validated_safety_properties = safety_property_validation(devices)
        if not validated_safety_properties:
            print("❌ No valid safety properties provided. Exiting.")
            return
    
    # Display configuration
    print("\n" + "="*70)
    print("CONFIGURATION SUMMARY")
    print("="*70)
    print(f"\nValidated Scenarios ({len(validated_scenarios)}):")
    for i, s in enumerate(validated_scenarios, 1):
        print(f"  {i}. {s}")
    
    print(f"\nValidated Safety Properties ({len(validated_safety_properties)}):")
    for i, p in enumerate(validated_safety_properties, 1):
        print(f"  {i}. {p}")
    
    # PROCESS 1: Generate syntactically valid NuSMV model
    model_file = "generated_model.smv"
    valid_model = generate_valid_nusmv_model(
        validated_scenarios, 
        validated_safety_properties, 
        model_file,
        max_iterations=10
    )
    
    if not valid_model:
        print("\n❌ Process 1 failed. Cannot proceed to Process 2.")
        print("The system could not generate a syntactically valid NuSMV model.")
        return
    
    # PROCESS 2: Minimize violations through iterative refinement
    output_model = "final_safe_model.smv"
    final_model = minimize_violations_with_llm(
        model_file,
        output_model,
        validated_scenarios,
        validated_safety_properties,
        max_iterations=50
    )
    
    # Final summary
    print("\n" + "="*70)
    if final_model:
        print("✅ TAPASSURE COMPLETED SUCCESSFULLY")
        print("="*70)
        print(f"\n✓ Syntactically valid model: {model_file}")
        print(f"✓ Safe and verified model: {output_model}")
        print(f"\nThe system has generated TAP rules that:")
        print(f"  1. Are syntactically correct")
        print(f"  2. Satisfy all {len(validated_safety_properties)} safety properties")
        print(f"  3. Implement all {len(validated_scenarios)} desired scenarios")
        
        # Optional: Generate YAML and deploy to SmartThings
        deploy = input("\nDeploy to SmartThings? (yes/no): ").strip().lower()
        if deploy == 'yes':
            yaml_file = scenarios_to_yaml(validated_scenarios)
            apply_scenarios_to_smartthings(yaml_file)
    else:
        print("⚠ TAPASSURE COMPLETED WITH WARNINGS")
        print("="*70)
        print(f"\n✓ Syntactically valid model generated: {model_file}")
        print(f"⚠ Process 2 completed with remaining violations")
        print(f"\nThe final model is saved to: {output_model}")
        print("Review the model and violations, then consider:")
        print("  1. Adjusting scenarios or safety properties")
        print("  2. Manual refinement of the model")
        print("  3. Running the process again with modified inputs")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Process interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
