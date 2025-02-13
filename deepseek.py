import requests
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
import subprocess
import yaml
import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from huggingface_hub import login

# Authenticate with Hugging Face
login(token="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")

# Load environment variables from .env
load_dotenv()

scenarios = [
    "When motion is detected by the Motion Sensor, turn on the Virtual Light.",
    "Turn off Virtual A/C 1 when the Virtual Motion Sensor detects no motion.",
    "At sunset, turn on Virtual TV 1 and set Virtual Fan 1 to medium speed.",
    "If Motion Sensor detects movement while away, turn on all Virtual Lights and send an alert.",
    "At 7 AM, turn on Virtual Fridge 1 and Virtual A/C 2 to prepare the kitchen.",
    "When Virtual Switch is turned on, activate Virtual Fan 5 and Virtual Light.",
    "When leaving home, turn off all devices: Virtual A/C 3, Virtual Fan 3, and Virtual Light.",
    "If Motion Sensor detects high temperature, turn on Virtual A/C 1 and Virtual Fan 2.",
    "Turn off all Virtual Lights when no motion is detected for 10 minutes.",
    "Turn on Virtual Fan 3 when the room temperature exceeds 75°F.",
    "Turn on Virtual A/C 2 and Virtual Fan 2 when the Virtual Motion Sensor detects movement in the living room.",
    "Turn off Virtual TV 3 when no one is detected in the room for 15 minutes.",
    "Use the Motion Sensor to trigger Virtual Light and Virtual A/C 1 when entering the bedroom.",
    "At sunrise, turn off Virtual Fan 1 and Virtual Light in the kitchen.",
    "Turn on Virtual TV 2 and set Virtual Fan 5 to low when 'movie mode' is activated.",
    "Turn off Virtual A/C 3 when all doors are closed and no motion is detected in the house.",
    "Turn on Virtual Fridge 1 and Virtual Light when the Virtual Motion Sensor detects movement in the dining room.",
    "If Motion Sensor detects temperature above 80°F, activate Virtual A/C 2 and Virtual Fan 4.",
    "Turn on Virtual TV 1 and mute it if no movement is detected in the living room for 5 minutes.",
    "Turn off Virtual Fan 2 at 10 PM every night to conserve energy."
]

# Predefined list of safety properties
safety_properties = [
    "Virtual A/C 1 must not turn on when windows are open.",
    "Virtual Light must turn off automatically if no motion is detected for 10 minutes.",
    "Virtual Fan 3 must not run when the room temperature is below 68°F.",
    "Virtual TV 1 must not turn on between midnight and 6 AM.",
    "Virtual A/C 2 must not run if the temperature is below 65°F.",
    "Virtual Motion Sensor must not trigger devices in 'away mode'.",
    "Virtual Light must not turn on during daylight hours unless motion is detected.",
    "Multiple Virtual Fans must not run in the same room simultaneously.",
    "Virtual TV 4 must turn off if no activity is detected for 30 minutes.",
    "Virtual Fridge 1 must not remain open for more than 2 minutes.",
    "Virtual A/C 3 must deactivate if the room temperature drops below 70°F.",
    "Virtual A/C 2 must not exceed 78°F.",
    "Virtual Fan 5 must not remain on for more than 1 hour without activity detection.",
    "Virtual Fan 4 must operate at medium speed if the temperature exceeds 85°F.",
    "Virtual TV 3 must mute automatically if no activity is detected for 15 minutes.",
    "Virtual A/C 1 must switch to 'eco mode' when no one is home.",
    "Virtual Motion Sensor must activate Virtual Light only in occupied rooms.",
    "Virtual Light must activate only when motion is detected in dark areas.",
    "Virtual Fan 1 must deactivate when Virtual A/C 2 is running."
]

# SmartThings API Configuration
SMARTTHINGS_API_URL = "https://api.smartthings.com/v1/devices"
SMARTTHINGS_BEARER_TOKEN = "0dc70a10-bda8-4d39-a1ee-67dc45e91595"

# Load the DeepSeek-R1 model and tokenizer
MODEL_NAME = "deepseek-ai/DeepSeek-R1"  # Replace with the correct Deepseek model name
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)

# Load the model with custom quantization support
try:
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
        torch_dtype=torch.float16,  # Use FP16 as a fallback
        device_map="auto"
    )
except ValueError as e:
    print(f"Error loading model: {e}")
    print("Falling back to FP16 quantization.")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
        torch_dtype=torch.float16,  # Fallback to FP16
        device_map="auto"
    )

# Function to generate responses using the DeepSeek-R1 model
def generate_response(prompt, max_length=512):
    """
    Generate a response using the DeepSeek-R1 model.
    """
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(
        inputs.input_ids,
        max_length=max_length,
        num_return_sequences=1,
        temperature=0.7,
        top_p=0.9,
        do_sample=True,
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response

# Function to retrieve devices from SmartThings API
def get_smartthings_devices():
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
# TAP RULES VALIDATION
#############################

# Template for validating scenarios with device validation
template = """
You are an AI assistant for creating IoT automation rules. Your task is to validate the user's scenario and ensure it contains all the necessary information:
1. Which device or devices are involved.
2. If condition that triggers the rule.
3. Then action to be performed.

Additionally, validate the devices mentioned in the scenario against the available devices from the user's SmartThings account:
Available Devices: {device_list}

Step 1: Analyze the provided scenario.
- If it is valid and complete, acknowledge it and proceed.
- If it mentions a device not in the available devices list, request a correction and suggest valid devices.

Scenario: "{scenario}"

Your response should include:
1. Feedback on the scenario's completeness.
2. If a device is missing, a request for correction with recommendations.
"""

# Create a ChatPromptTemplate using the defined template
device_validation_template = ChatPromptTemplate.from_template(template)

def interactive_device_validation(devices):
    print("Welcome to the TAPChecker!")
    print("You can input multiple scenarios. The assistant will validate each one.")
    print("Type 'done' when you have finished entering your scenarios.\n")
    
    saved_scenarios = []  # List to store validated scenarios
    print(f"Devices retrieved from SmartThings: {', '.join(devices)}\n")
    
    while True:
        scenario = input("Enter your IoT scenario (or type 'done' to finish): ").strip()
        # Explicitly handle 'done' input
        if scenario.lower() == 'done':
            print("\nYou have finished entering scenarios.")
            break  # Exit the loop when the user is finished

        if not scenario or len(scenario.split()) < 3:
            print("\nInvalid scenario. Please provide a detailed input including devices, conditions, and actions.\n")
            continue

        while True:
            # Validate the scenario with the DeepSeek-R1 model
            prompt = device_validation_template.invoke({
                "scenario": scenario,
                "device_list": ", ".join(devices)
            })
            result = generate_response(prompt.content)

            print("\nAssistant Response:")
            print(result)

            if "valid and complete" in result.lower():
                print("\nThe scenario is valid and has been saved.")
                saved_scenarios.append(scenario)
                break  # Move to the next scenario

            # Prompt user to refine the scenario
            scenario = input("\nPlease update your scenario based on the assistant's suggestions: ").strip()

    if saved_scenarios:
        print("\nHere are the validated scenarios:")
        for i, sc in enumerate(saved_scenarios, 1):
            print(f"{i}. {sc}")
    else:
        print("\nNo valid scenarios were provided.")
    
    return saved_scenarios

#############################
# SAFETY PROPERTIES VALIDATION
#############################
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

Step 2: Suggest improvements to make the property more robust and actionable. Provide examples for clarity.

Your response must explicitly include:
1. Whether the safety property is "valid and complete."
2. Feedback on its validity and completeness.
3. Suggestions for improvement (if needed).
"""

def interactive_safety_property_validation(devices):
    print("\nNow, let's define the safety properties for your IoT automation rules.")
    print("Type 'done' when you have finished entering safety properties.\n")

    saved_properties = []
    safety_validation_template = ChatPromptTemplate.from_template(safety_template)

    while True:
        safety_property = input("Enter your safety property (or type 'done' to finish): ").strip()

        # Handle 'done' input
        if safety_property.lower() == 'done':
            print("\nYou have finished entering safety properties.")
            break

        # Basic input validation
        if not safety_property or len(safety_property.split()) < 3:
            print("\nInvalid safety property. Please provide more details, including devices, conditions, and actions.\n")
            continue

        while True:
            # Validate the safety property with the DeepSeek-R1 model
            prompt = safety_validation_template.invoke({
                "property": safety_property,
                "device_list": ", ".join(devices)
            })
            result = generate_response(prompt.content)

            print("\nAssistant Response:")
            print(result)

            # Check if the assistant marked the property as valid and complete
            if "valid and complete" in result.lower():
                print("\nThe safety property is valid and has been saved.")
                saved_properties.append(safety_property)
                break

            # Prompt the user to refine the safety property
            safety_property = input("\nPlease update your safety property based on the assistant's suggestions: ").strip()

    if saved_properties:
        print("\nHere are the validated safety properties:")
        for i, sp in enumerate(saved_properties, 1):
            print(f"{i}. {sp}")
    else:
        print("\nNo valid safety properties were provided.")
    
    return saved_properties

#############################
# CROSS-VALIDATION
#############################

def cross_validate_scenarios_and_properties(scenarios, safety_properties):
    cross_validation_template = """
    You are an expert assistant for validating IoT automation rules. Cross-check the given scenario against the provided safety property and determine:
    1. Whether the scenario violates the safety property.
    2. If a violation exists, explain why and suggest modifications to the scenario or the safety property.

    Scenario: "{scenario}"
    Safety Property: "{property}"

    Your response should include:
    1. Whether a violation exists (yes/no).
    2. An explanation if a violation exists.
    3. Suggestions for resolving the conflict with specific examples.
    """

    validation_template = ChatPromptTemplate.from_template(cross_validation_template)

    violations = []  # Store detected conflicts
    compliant_scenarios = []  # Store scenarios that pass validation

    for scenario in scenarios:
        for property in safety_properties:
            # Validate the scenario against the safety property
            prompt = validation_template.invoke({
                "scenario": scenario,
                "property": property
            })
            result = generate_response(prompt.content)

            print(f"\nValidating Scenario: {scenario}")
            print(f"Against Safety Property: {property}")
            print("\nAssistant Response:")
            print(result)

            # Check if a violation exists
            if "violation exists" in result.lower() or "conflict" in result.lower():
                violations.append({
                    "scenario": scenario,
                    "property": property,
                    "response": result
                })
            else:
                compliant_scenarios.append(scenario)

    # Report results
    if violations:
        print("\nConflicts detected during cross-validation:")
        for i, violation in enumerate(violations, 1):
            print(f"\nConflict {i}:")
            print(f"Scenario: {violation['scenario']}")
            print(f"Safety Property: {violation['property']}")
            print(f"Assistant Response: {violation['response']}")
    else:
        print("\nNo conflicts detected. All scenarios comply with the defined safety properties.")

    # Display compliant scenarios
    if compliant_scenarios:
        print("\nCompliant Scenarios:")
        for i, scenario in enumerate(compliant_scenarios, 1):
            print(f"{i}. {scenario}")

    return violations, compliant_scenarios

#############################
# NUSMV
#############################

def generate_smv_with_ltl(scenarios, safety_properties, output_file="model.smv"):
    """
    Generate a NuSMV model dynamically from validated scenarios and safety properties.
    """
    print("\nGenerating NuSMV model with LTL formulas...\n")
    with open(output_file, "w") as file:
        # Define the module and variables
        file.write("MODULE main\n")
        file.write("VAR\n")
        file.write("  time : 0..24;\n")  # Example time variable for temporal logic

        # Write LTL formulas for scenarios
        file.write("\n-- LTL Specifications for Scenarios\n")
        for idx, scenario in enumerate(scenarios, 1):
            try:
                ltl_formula = parse_scenario_to_ltl(scenario)
                file.write(f"LTLSPEC name scenario_{idx}: {ltl_formula};\n")
            except Exception as e:
                print(f"Error parsing scenario {idx}: {scenario} -> {str(e)}")

        # Write LTL formulas for safety properties
        file.write("\n-- LTL Specifications for Safety Properties\n")
        for idx, safety_property in enumerate(safety_properties, 1):
            try:
                ltl_formula = parse_safety_property_to_ltl(safety_property)
                file.write(f"LTLSPEC name safety_{idx}: {ltl_formula};\n")
            except Exception as e:
                print(f"Error parsing safety property {idx}: {safety_property} -> {str(e)}")

    print(f"NuSMV model generated: {output_file}")

def parse_scenario_to_ltl(scenario):
    """
    Parse a validated scenario into an LTL formula using the DeepSeek-R1 model.
    """
    prompt = f"""
    Convert the following IoT scenario into an LTL formula for NuSMV:
    Scenario: "{scenario}"

    Example:
    - Scenario: "When motion is detected, turn on the light."
      Formula: G (motion_detected -> F light_on)

    Ensure the formula uses variables declared in NuSMV and adheres to NuSMV syntax.
    Your output must only contain the LTL formula.
    """
    try:
        response = generate_response(prompt)
        ltl_formula = response.strip()
        return ltl_formula
    except Exception as e:
        raise ValueError(f"Failed to parse scenario to LTL: {scenario}. Error: {str(e)}")

def parse_safety_property_to_ltl(safety_property):
    """
    Parse a validated safety property into an LTL formula using the DeepSeek-R1 model.
    """
    prompt = f"""
    Convert the following IoT safety property into an LTL formula for NuSMV:
    Safety Property: "{safety_property}"

    Example:
    - Safety Property: "The heater should not be on when the window is open."
      Formula: G (!(window_open & heater_on))

    Ensure the formula is valid for NuSMV.
    Your output must only contain the LTL formula.
    """
    try:
        response = generate_response(prompt)
        ltl_formula = response.strip()
        return ltl_formula
    except Exception as e:
        raise ValueError(f"Failed to parse safety property to LTL: {safety_property}. Error: {str(e)}")

def feed_error_to_llm(model_file, nusmv_error, scenarios, safety_properties):
    with open(model_file, "r") as file:
        model_content = file.read()

    prompt = f"""
    The following NuSMV model has errors:
    Error Message:
    {nusmv_error}

    Scenarios:
    {', '.join(scenarios)}

    Safety Properties:
    {', '.join(safety_properties)}

    Model:
    {model_content}

    Correct the model by:
    1. Fixing syntax errors in `LTLSPEC` formulas.
    2. Ensuring all variables are declared in the `VAR` section.
    3. Verifying temporal operators are used properly.
    4. Returning only the corrected model as plain text.
    """
    try:
        response = model.invoke(prompt)
        corrected_model = extract_code_block(response.content)
        if not corrected_model:
            raise ValueError("Failed to extract corrected model from response.")
        return corrected_model
    except Exception as e:
        print(f"Error during model correction: {e}")
        return None

def extract_code_block(content):
    """
    Extract the code block from the LLM response.
    """
    match = re.search(r"```(?:smv)?\n(.*?)\n```", content, re.DOTALL)
    return match.group(1).strip() if match else content.strip()


def run_nusmv_validation_until_success(model_file, scenarios, safety_properties):
    """
    Run NuSMV validation and retry corrections until the model is valid.
    """
    attempt_count = 0

    while True:
        attempt_count += 1
        print(f"=====================================================")
        print(f"Attempt {attempt_count}: Running NuSMV validation...")
        print(f"=====================================================")

        try:
            result = subprocess.run(["nusmv", model_file], capture_output=True, text=True)

            if result.returncode == 0:
                print("\nNuSMV validation successful.")
                return attempt_count, True, result.stdout
            else:
                print(f"\nNuSMV error: {result.stderr}")
                corrected_model = feed_error_to_llm(model_file, result.stderr, scenarios, safety_properties)

                if corrected_model:
                    with open(model_file, "w") as file:
                        file.write(corrected_model)
                    print("\nCorrected NuSMV model saved. Retrying...")
                else:
                    print("\nFailed to correct the model.")
                    return attempt_count, False, result.stderr

        except FileNotFoundError:
            print("\nNuSMV is not installed or not in PATH. Please install NuSMV.")
            return attempt_count, False, "NuSMV not found."
        
#############################
# YAML
#############################


def scenarios_to_yaml(validated_scenarios, output_file="scenarios.yaml"):
    """
    Converts validated scenarios into a YAML format and saves them to a file.
    """
    print("\nConverting validated scenarios to YAML format...\n")
    scenarios_yaml = []
    
    for idx, scenario in enumerate(validated_scenarios, 1):
        scenario_yaml = {
            "id": f"scenario_{idx}",
            "description": scenario,
            "condition": f"Parsed condition for scenario {idx}",  # Placeholder, extract actual condition
            "action": f"Parsed action for scenario {idx}",  # Placeholder, extract actual action
            "devices": f"Parsed devices for scenario {idx}"  # Placeholder, extract actual devices
        }
        scenarios_yaml.append(scenario_yaml)

    with open(output_file, "w") as yaml_file:
        yaml.dump({"scenarios": scenarios_yaml}, yaml_file)

    print(f"Scenarios have been saved in YAML format: {output_file}")
    return output_file

def parse_scenario_to_components(scenario):
    """
    Parse a scenario into its condition, action, and devices using the LLM.
    """
    prompt = f"""
    Parse the following IoT scenario into its components:
    Scenario: "{scenario}"
    
    Your output must include:
    1. Condition: The triggering condition.
    2. Action: The action to be performed.
    3. Devices: The devices involved in the scenario.
    """
    response = model.invoke(prompt)
    return response.content.strip()  # Clean the output

def apply_scenarios_to_smartthings(yaml_file):
    """
    Apply scenarios defined in the YAML file to SmartThings API as automations.
    """
    print("\nApplying scenarios to SmartThings...\n")
    try:
        # Load scenarios from YAML file
        with open(yaml_file, "r") as file:
            scenarios = yaml.safe_load(file)["scenarios"]

        for scenario in scenarios:
            # Define the payload for SmartThings API
            payload = {
                "name": scenario["id"],
                "description": scenario["description"],
                "condition": scenario["condition"],  # Needs actual parsing
                "action": scenario["action"],  # Needs actual parsing
                "devices": scenario["devices"]  # Needs actual parsing
            }

            # Send the automation to SmartThings API
            response = requests.post(
                f"{SMARTTHINGS_API_URL}/automations",
                headers={"Authorization": f"Bearer 0dc70a10-bda8-4d39-a1ee-67dc45e91595"},
                json=payload
            )

            if response.status_code == 201:
                print(f"Scenario {scenario['id']} applied successfully.")
            else:
                print(f"Failed to apply scenario {scenario['id']}. Error: {response.json()}")

    except Exception as e:
        print(f"Error applying scenarios: {str(e)}")
        
#############################
# MAIN WORKFLOW
#############################

# Main Workflow
if __name__ == "__main__":
    # Step 1: Fetch SmartThings devices
    devices = get_smartthings_devices()
    if not devices:
        print("No devices retrieved from SmartThings. Exiting.")
        exit()

    # Step 2: Collect and validate scenarios
    validated_scenarios = interactive_device_validation(devices)

    # Step 3: Collect safety properties
    validated_safety_properties = interactive_safety_property_validation(devices)

    # Step 4: Prompt-Based Validation
    prompt_violations, compliant_scenarios = cross_validate_scenarios_and_properties(
        validated_scenarios, validated_safety_properties
    )

    # Step 5: NuSMV Validation
    print("\nGenerating NuSMV model and running formal verification...")
    model_file = "generated_model.smv"
    generate_smv_with_ltl(validated_scenarios, validated_safety_properties, model_file)

    # Step 6: Run NuSMV validation
    attempt_count, success, nusmv_results = run_nusmv_validation_until_success(model_file, validated_scenarios, validated_safety_properties)

    if success:
        print(f"\nNuSMV model validated successfully after {attempt_count} attempts.")
    else:
        print(f"\nFailed to generate a valid NuSMV model after {attempt_count} attempts.")
        print("Error details:", nusmv_results)

    # Step 7: Convert scenarios to YAML
    yaml_file = scenarios_to_yaml(validated_scenarios)

    # Step 8: Apply scenarios via SmartThings API
    apply_scenarios_to_smartthings(yaml_file)