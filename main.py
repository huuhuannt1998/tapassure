import requests
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import subprocess
import yaml
import re

# Load environment variables from .env
load_dotenv()

# SmartThings API Configuration
SMARTTHINGS_API_URL = "https://api.smartthings.com/v1/devices"
SMARTTHINGS_BEARER_TOKEN = "0dc70a10-bda8-4d39-a1ee-67dc45e91595"

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
model = ChatOpenAI(model="o1-mini", temperature=1.0)

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
            result = model.invoke(prompt)

            print(f"\nValidating Scenario: {scenario}")
            print(f"Against Safety Property: {property}")
            print("\nAssistant Response:")
            print(result.content)

            # Check if a violation exists
            if "violation exists" in result.content.lower() or "conflict" in result.content.lower():
                violations.append({
                    "scenario": scenario,
                    "property": property,
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
    Parse a validated scenario into an LTL formula using the LLM.
    """
    prompt = f"""
    Convert the following IoT scenario into an LTL formula that complies with NuSMV syntax:
    Scenario: "{scenario}"
    Ensure the formula uses variables declared in NuSMV and follows NuSMV's LTL rules.
    """
    try:
        response = model.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        raise ValueError(f"Failed to parse scenario to LTL: {scenario}. Error: {str(e)}")


def parse_safety_property_to_ltl(safety_property):
    """
    Parse a validated safety property into an LTL formula using the LLM.
    """
    prompt = f"""
    Convert the following IoT safety property into an LTL formula:
    Safety Property: "{safety_property}"
    Your output must be a single valid LTL formula.
    """
    try:
        response = model.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        raise ValueError(f"Failed to parse safety property to LTL: {safety_property}. Error: {str(e)}")


def feed_error_to_llm(model_file, nusmv_error, scenarios, safety_properties):
    """
    Use the LLM to correct the NuSMV model based on the error message,
    including user-provided scenarios, safety properties, and the last model output.
    """
    with open(model_file, "r") as file:
        model_content = file.read()

    prompt = f"""
    The following NuSMV model has errors:
    Error Message:
    {nusmv_error}

    User-Provided Scenarios:
    {', '.join(scenarios)}

    User-Provided Safety Properties:
    {', '.join(safety_properties)}

    Current Model:
    {model_content}

    Correct this model with the following instructions:
    - Ensure all `LTLSPEC` formulas are valid and properly formatted for NuSMV.
    - Fix all syntax errors, especially the issues indicated in the error message.
    - Only return the corrected NuSMV model as plain text. Do not include any explanations or comments.
    """
    try:
        # Invoke the LLM with the prompt
        response = model.invoke(prompt)
        response_content = response.content.strip()

        # Extract only the NuSMV code while removing markdown formatting like ```smv and ```
        if "```" in response_content:
            code_block_match = re.search(r"```(?:smv)?\n(.*?)\n```", response_content, re.DOTALL)
            if code_block_match:
                corrected_model = code_block_match.group(1).strip()
                return corrected_model
        else:
            return response_content
    except Exception as e:
        print(f"Error feeding the NuSMV error to the LLM: {e}")
        return None



def run_nusmv_validation_until_success(model_file, scenarios, safety_properties):
    """
    Run NuSMV on the given model file, retrying corrections indefinitely until the model is valid.
    Returns the number of attempts it took to generate a valid model.
    """
    attempt_count = 0

    while True:
        attempt_count += 1
        print(f"=====================================================")
        print(f"Attempt {attempt_count}: Running NuSMV validation...")
        print(f"=====================================================")

        try:
            # Run NuSMV on the model file
            result = subprocess.run(["nusmv", model_file], capture_output=True, text=True)

            if result.returncode == 0:
                # Validation succeeded
                print("NuSMV Validation Completed Successfully:\n", result.stdout)
                return attempt_count, True, result.stdout
            else:
                # Log the error and file content for debugging
                print("NuSMV Error:\n", result.stderr)
                with open(model_file, "r") as file:
                    print("\nGenerated NuSMV File Content:\n")
                    print(file.read())

                # Feed the error back to the LLM for correction
                corrected_model = feed_error_to_llm(model_file, result.stderr, scenarios, safety_properties)

                if corrected_model:
                    # Save the corrected model to the file
                    with open(model_file, "w") as file:
                        file.write(corrected_model)
                    print("\nCorrected NuSMV model generated. Re-running NuSMV...")
                else:
                    print("Failed to correct the NuSMV model. Exiting.")
                    return attempt_count, False, result.stderr

        except FileNotFoundError:
            print("NuSMV is not installed or not in your PATH. Please install it and try again.")
            return attempt_count, False, "Error: NuSMV not found."



def cross_validate_with_nusmv(scenarios, safety_properties):
    """
    Perform cross-validation using both prompt-based validation and NuSMV validation.
    """
    print("\nStarting comprehensive cross-validation...\n")

    # Step 1: Prompt-based validation
    print("Running prompt-based validation...\n")
    prompt_violations, compliant_scenarios = cross_validate_scenarios_and_properties(scenarios, safety_properties)

    # Step 2: NuSMV-based validation
    print("\nGenerating NuSMV model and running formal verification...\n")
    model_file = "generated_model.smv"
    generate_smv_with_ltl(scenarios, safety_properties, model_file)
    nusmv_results = run_nusmv_validation_until_success(model_file, validated_scenarios, validated_safety_properties)

    # Step 3: Consolidate results
    results = {
        "Prompt-Based Validation": {
            "violations": prompt_violations,
            "compliant_scenarios": compliant_scenarios,
            "status": "Conflicts Detected" if prompt_violations else "No Conflicts"
        },
        "NuSMV Validation": {
            "output": nusmv_results,
            "status": "Conflicts Detected" if "is false" in nusmv_results else "No Conflicts"
        }
    }

    # Display results summary
    print("\n--- Validation Results Summary ---\n")
    print("Prompt-Based Validation:")
    print(f"Status: {results['Prompt-Based Validation']['status']}")
    if results['Prompt-Based Validation']['violations']:
        print("Violations:")
        for i, violation in enumerate(results['Prompt-Based Validation']['violations'], 1):
            print(f"{i}. Scenario: {violation['scenario']}")
            print(f"   Property: {violation['property']}")
            print(f"   Response: {violation['response']}")

    print("\nNuSMV Validation:")
    print(f"Status: {results['NuSMV Validation']['status']}")
    print(f"Output:\n{results['NuSMV Validation']['output']}")

    return results

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
while True:
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

    # Step 5: NuSMV Validation with Infinite Retry Mechanism
    print("\nGenerating NuSMV model and running formal verification...")
    model_file = "generated_model.smv"
    generate_smv_with_ltl(validated_scenarios, validated_safety_properties, model_file)

    attempt_count, success, nusmv_results = run_nusmv_validation_until_success(model_file, validated_scenarios, validated_safety_properties)

    if success:
        print(f"\nNuSMV model validated successfully after {attempt_count} attempts.")
    else:
        print(f"\nFailed to generate a valid NuSMV model after {attempt_count} attempts.")
        print("Error details:", nusmv_results)

    # Final Results Summary
    print("\n--- Final Validation Results ---\n")
    if not prompt_violations and "is false" not in nusmv_results:
        print("All validations passed. Proceeding to YAML generation...")
        break  # Exit the loop as all validations have passed
    else:
        print("\nConflicts detected in one or both validation steps.")
        print("Please revise your scenarios and safety properties.\n")
        print("Restarting the validation process...\n")

    # Step 6: Convert scenarios to YAML
    yaml_file = scenarios_to_yaml(validated_scenarios)

    # Step 7: Apply scenarios via SmartThings API
    apply_scenarios_to_smartthings(yaml_file)