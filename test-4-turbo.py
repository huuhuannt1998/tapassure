import requests
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import os
import subprocess
import yaml
import re

# Load environment variables from .env
load_dotenv()

# SmartThings API Configuration
SMARTTHINGS_API_URL = "https://api.smartthings.com/v1/devices"
SMARTTHINGS_BEARER_TOKEN = "0dc70a10-bda8-4d39-a1ee-67dc45e91595"


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
# Predefined list of safety properties
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

# Initialize ChatOpenAI Model
# model = ChatOpenAI(model="gpt-4o")
OPENAI_API_KEY = "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"  # Load API Key from .env

# Initialize ChatOpenAI with Organization ID
model = ChatOpenAI(
    model="gpt-4-turbo",
    openai_api_key = OPENAI_API_KEY,
)

#############################
# SCENARIOS VALIDATION
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
            # Validate the scenario with the LLM
            prompt = device_validation_template.invoke({
                "scenario": scenario,
                "device_list": ", ".join(devices)
            })
            result = model.invoke(prompt)

            print("\nAssistant Response:")
            print(result.content)

            if "valid and complete" in result.content.lower():
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
            # Validate the safety property with the assistant
            prompt = safety_validation_template.invoke({
                "property": safety_property,
                "device_list": ", ".join(devices)
            })
            result = model.invoke(prompt)

            print("\nAssistant Response:")
            print(result.content)

            # Check if the assistant marked the property as valid and complete
            if "valid and complete" in result.content.lower():
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
# PROMPT-BASED VALIDATION
#############################

def prompt_based_validation(scenarios, safety_properties):

    prompt_based_validation_template = """
    You are an expert assistant for validating IoT automation rules. Cross-check the given scenario against all the provided safety properties and determine:
    1. Whether the scenario violates any of the safety properties.
    2. If a violation exists, explain why and suggest modifications to the scenario.

    Scenario: "{scenario}"

    Safety Properties:
    {properties}

    Your response should include: Whether a violation exists (yes/no)
    """

    validation_template = ChatPromptTemplate.from_template(prompt_based_validation_template)
    violations = []  # Store detected conflicts
    compliant_scenarios = []  # Store scenarios that pass validation

    for scenario in scenarios:
        # Combine all safety properties into one string
        combined_properties = "\n- " + "\n- ".join(safety_properties)
        
        # Validate the scenario against all safety properties at once
        prompt = validation_template.invoke({
            "scenario": scenario,
            "properties": combined_properties
        })
        result = model.invoke(prompt)

        print(f"\nValidating Scenario: {scenario}")
        print("\nAssistant Response:")
        print(result.content)

        # Check if any violations exist
        if "violation exists" in result.content.lower() or "conflict" in result.content.lower():
            violations.append({
                "scenario": scenario,
                "response": result.content
            })
        else:
            compliant_scenarios.append(scenario)

    # Report results
    if violations:
        print("\nConflicts detected during cross-validation:")
        for i, violation in enumerate(violations, 1):
            print(f"\nConflict {i}:")
            print(f"Scenario: {violation['scenario']}")
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

#############################
# PROCESS 1: FIXING SYNTAX ERRORS
#############################

def generate_smv_with_ltl(scenarios, safety_properties, output_file="model.smv"):
    """
    Generate an initial NuSMV model with LTL formulas based on provided scenarios and safety properties.
    """
    print("\nGenerating NuSMV model with LTL formulas...\n")
    with open(output_file, "w") as file:
        file.write("MODULE main\n")
        file.write("VAR\n")
        file.write("  time : 0..24;\n")  # Example variable for temporal logic

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

def validate_ltl_formula(formula):
    return "G" in formula or "F" in formula or "X" in formula

def parse_scenario_to_ltl(scenario):

    prompt = f"""
    Convert the following IoT scenario into an LTL formula:
    Scenario: "{scenario}"

    Example:
    Scenario: "When motion is detected, turn on the light."
    Formula: G (motion_detected -> F light_on)

    Ensure the formula uses valid NuSMV syntax.
    """
    try:
        response = model.invoke(prompt)
        ltl_formula = response.content.strip()
        if not validate_ltl_formula(ltl_formula):
            raise ValueError(f"Invalid LTL formula: {ltl_formula}")
        return ltl_formula
    except Exception as e:
        raise ValueError(f"Failed to parse scenario: {scenario}. Error: {str(e)}")

def parse_safety_property_to_ltl(safety_property):

    prompt = f"""
    Convert the following IoT safety property into an LTL formula:
    Safety Property: "{safety_property}"

    Example:
    Safety Property: "The heater should not be on when the window is open."
    Formula: G (!(window_open & heater_on))

    Ensure the formula uses valid NuSMV syntax.
    """
    try:
        response = model.invoke(prompt)
        ltl_formula = response.content.strip()
        if not validate_ltl_formula(ltl_formula):
            raise ValueError(f"Invalid LTL formula: {ltl_formula}")
        return ltl_formula
    except Exception as e:
        raise ValueError(f"Failed to parse safety property: {safety_property}. Error: {str(e)}")
    

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

def nusmv_syntax_regeneration(scenarios, safety_properties, output_file="model.smv"):
    """
    Generate and refine an NuSMV model using LLM until there are no syntax errors.

    """
    iteration = 0
    while True:
        iteration += 1
        print(f"\n=== Process 1: Iteration {iteration} - Generating and Validating NuSMV Model ===")

        # Generate the initial or refined NuSMV model
        if iteration == 1:
            print("📝 Generating initial NuSMV model...")
            nusmv_model = generate_nusmv_model_with_llm(scenarios, safety_properties, output_file)
        else:
            print("🔄 Refining NuSMV model based on syntax error...")

        if not nusmv_model:
            print(f"❌ Failed to generate NuSMV model in iteration {iteration}. Retrying...\n")
            continue

        # Save the generated model to a file
        with open(output_file, "w") as file:
            file.write(nusmv_model)

        # Display the generated NuSMV model
        print("\n=== Generated NuSMV Model ===")
        print(nusmv_model)

        # Validate the NuSMV model for syntax errors
        is_valid, validation_output = validate_nusmv_model(output_file)

        if is_valid:
            print(f"\n✅ NuSMV model is valid and generated successfully after {iteration} iterations.\n")
            return iteration, True, nusmv_model
        else:
            # Display the syntax error
            print("\n⚠️ Syntax error detected:")
            print(validation_output)

            # Refine the model using the syntax error
            nusmv_model = feed_error_to_llm(output_file, validation_output, scenarios, safety_properties)
            if not nusmv_model:
                print("❌ Failed to refine the model. Retrying...\n")
                continue



def generate_nusmv_model_with_llm(scenarios, safety_properties, output_file="model.smv"):
    """
    Generate a complete NuSMV model using the LLM.
    """
    print("\nGenerating NuSMV model using the LLM...\n")

    # Prepare the prompt for the LLM
    prompt = f"""
    Generate a complete NuSMV model based on the following scenarios and safety properties.

    Scenarios:
    {', '.join(scenarios)}

    Safety Properties:
    {', '.join(safety_properties)}

    Your task is to generate a valid NuSMV model that includes:
    1. A `MODULE main` declaration.
    2. A `VAR` section with all necessary variables and their types.
    3. An `ASSIGN` section with initial states for all variables.
    4. Transition rules for the scenarios.
    5. LTLSPECs for the safety properties.

    Ensure the model adheres to NuSMV syntax and is ready for verification.

    Your output must only contain the NuSMV model as plain text.
    """

    try:
        # Invoke the LLM to generate the model
        response = model.invoke(prompt)
        nusmv_model = response.content.strip()

        # Remove triple backticks if present
        if "```" in nusmv_model:
            nusmv_model = re.sub(r"```(?:nusmv)?\n(.*?)\n```", r"\1", nusmv_model, flags=re.DOTALL)

        # Save the generated model to a file
        with open(output_file, "w") as file:
            file.write(nusmv_model)

        print(f"NuSMV model generated: {output_file}")
        return nusmv_model
    except Exception as e:
        print(f"Error generating NuSMV model: {e}")
        return None

def extract_code_block(content):
    """
    Extract the code block from the LLM response.
    """
    match = re.search(r"```(?:smv)?\n(.*?)\n```", content, re.DOTALL)
    return match.group(1).strip() if match else content.strip()


# =============================================
# Process 2: Iterative Model Regeneration to Minimize Violations
# =============================================


def validate_nusmv_model(model_file):
    """
    Validate the NuSMV model using the NuSMV model checker.
    """
    try:
        result = subprocess.run(["nusmv", model_file], capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except FileNotFoundError:
        print("NuSMV not found.")
        return False, "NuSMV not found."


def minimize_violations_with_llm(model_file, scenarios, safety_properties):
    """
    Iteratively refine scenarios to minimize violations.
    """
    attempt_count = 0
    while True:
        attempt_count += 1
        print(f"\nIteration {attempt_count}: Minimizing violations...")
        is_valid, validation_output = validate_nusmv_model(model_file)
        
        if is_valid:
            print(f"\n✅ Model validated successfully after {attempt_count} attempts.")
            return scenarios
        violations = extract_nusmv_violations(validation_output)
        if violations:
            print(f"\n⚠️ Detected {len(violations)} violations. Regenerating scenarios...")
            scenarios = regenerate_transition_rules(scenarios, validation_output)
        else:
            print("\nNo specific violations found. Stopping iteration.")
            return None

def extract_nusmv_violations(nusmv_output):
    """
    Extract violated LTL specifications from NuSMV output.
    """
    violation_pattern = r"LTLSPEC.*?is false"
    return re.findall(violation_pattern, nusmv_output)

def regenerate_transition_rules(scenarios, nusmv_error):
    """
    Regenerate transition rules using the LLM to minimize violations.
    """
    prompt = f"""
    The following NuSMV model has detected violations:
    {nusmv_error}

    Modify the transition rules to reduce violations.
    """
    try:
        response = model.invoke(prompt)
        return eval(response.content.strip())
    except Exception as e:
        print(f"Error regenerating transition rules: {e}")
        return None

    
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
                headers={"Authorization": f"Bearer {SMARTTHINGS_BEARER_TOKEN}"},
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
while True:
    # Step 1: Fetch SmartThings devices
    devices = get_smartthings_devices()
    if not devices:
        print("No devices retrieved from SmartThings. Exiting.")
        exit()

    # Step 2: Collect and validate scenarios
    validated_scenarios = scenarios1

    # Step 3: Collect safety properties
    validated_safety_properties = safety_properties1

    # Step 4: Prompt-Based Validation

    prompt_violations, compliant_scenarios = prompt_based_validation(
        validated_scenarios, validated_safety_properties
    )

    # Display prompt-based validation results
    if prompt_violations:
        print("\nConflicts detected in prompt-based validation:")
        for i, violation in enumerate(prompt_violations, 1):
            print(f"\nConflict {i}:")
            print(f"Scenario: {violation['scenario']}")
            print(f"Safety Property: {violation['property']}")
            print(f"Response: {violation['response']}")
    else:
        print("\nNo conflicts detected in prompt-based validation.")

    model_file = "generated_model.smv"

    # Generate the NuSMV model using the LLM
    iteration_count, success, final_nusmv_model = nusmv_syntax_regeneration(validated_scenarios, validated_safety_properties, model_file)

    if success:
        print(f"\n✅ NuSMV model validated successfully after {iteration_count} iterations.")
    else:
        print(f"\n❌ Failed to generate a valid NuSMV model after {iteration_count} iterations.")
        print("Error details:", final_nusmv_model)

    

    # Step 5: NuSMV Validation with Infinite Retry Mechanism

    print("\nGenerating NuSMV model and running formal verification...")
    model_file = "generated_model.smv"
    # generate_smv_with_ltl(validated_scenarios, validated_safety_properties, model_file)

    # attempt_count, success, nusmv_results = run_nusmv_validation_until_success(model_file, validated_scenarios, validated_safety_properties)

    # if success:
    #     print(f"\nNuSMV model validated successfully after {attempt_count} attempts.")
    # else:
    #     print(f"\nFailed to generate a valid NuSMV model after {attempt_count} attempts.")
    #     print("Error details:", nusmv_results)

    # # Final Results Summary
    # print("\n--- Final Validation Results ---\n")
    # if not prompt_violations and "is false" not in nusmv_results:
    #     print("All validations passed. Proceeding to YAML generation...")
    #     break  # Exit the loop as all validations have passed
    # else:
    #     print("\nConflicts detected in one or both validation steps.")
    #     print("Please revise your scenarios and safety properties.\n")
    #     print("Restarting the validation process...\n")

    print("\nStarting iterative violation minimization...")
    final_scenarios = minimize_violations_with_llm(model_file, validated_scenarios, validated_safety_properties)

    if not final_scenarios:
        print("Failed to minimize violations. Exiting.")
        exit()

    # Step 6: Convert scenarios to YAML
    # yaml_file = scenarios_to_yaml(validated_scenarios)

    # Step 7: Apply scenarios via SmartThings API
    # apply_scenarios_to_smartthings(yaml_file)

    break