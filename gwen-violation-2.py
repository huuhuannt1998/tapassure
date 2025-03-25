import requests
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
# from langchain_openai import OpenAI
from openai import OpenAI
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
# with open('api_key.txt', 'r') as file:
#     openai_api_key = file.read().strip()
    
# openai_api_base = "https://api.lambdalabs.com/v1"

from openai import OpenAI  # Import the updated OpenAI class

# Initialize the OpenAI client
# client = OpenAI(
#     api_key=openai_api_key,
#     base_url=openai_api_base,
# )

def invoke_llm(prompt):
    import re

    url = 'http://cci-siscluster1.charlotte.edu:8080/api/chat/completions'
    headers = {
        'Authorization': 'Bearer sk-a6af2053d49649d2925ff91fef71cb65',
        'Content-Type': 'application/json'
    }
    data = {
        "model": "Qwen/Qwen2.5-14B-Instruct-1M",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant that strictly follows the user's instructions."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)

        # Safety check
        if response.status_code != 200:
            print(f"❌ Error: Received status code {response.status_code}")
            print(response.text)
            return None

        # Extract the message content from the response
        response_json = response.json()
        generated_content = response_json["choices"][0]["message"]["content"]

        # Clean the content
        cleaned_content = re.sub(r"```(?:nusmv|smv|plaintext)?\n", "", generated_content)
        cleaned_content = re.sub(r"\n```", "", cleaned_content)

        # Validate NuSMV structure (your existing function)
        if not is_valid_nusmv_code(cleaned_content):
            print("❌ LLM returned invalid NuSMV code after cleaning. Retrying...")
            return None

        return cleaned_content.strip()

    except Exception as e:
        print(f"❌ Error invoking LLM: {e}")
        return None


    
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

def scenarios_validation(devices):
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
            result = invoke_llm(prompt)

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

def safety_property_validation(devices):
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
            result = invoke_llm(prompt)

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
    You are an expert assistant for validating IoT automation rules. 
    Cross-check the given scenario against all the provided safety properties and determine:
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
        result = invoke_llm(prompt)

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

def extract_code_block(content):
    content = re.sub(r"```(?:smv|plaintext)?\n", "", content)
    content = re.sub(r"\n```", "", content)

    return content.strip()

def validate_ltl_formula(formula):
    return "G" in formula or "F" in formula or "X" in formula

def parse_scenario_to_ltl(scenario):
    prompt = f"""
    Convert the following IoT scenario into an LTL formula:
    Scenario: "{scenario}"
    """
    response = invoke_llm(prompt)
    ltl_formula = response.strip()
    
    if not validate_ltl_formula(ltl_formula):
        raise ValueError(f"Invalid LTL formula: {ltl_formula}")

    print(f"\n🔍 LTL Formula for Scenario: {scenario}\n➡️ {ltl_formula}\n")  
    return ltl_formula


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
        response = invoke_llm(prompt)
        ltl_formula = response.strip()
        if not validate_ltl_formula(ltl_formula):
            raise ValueError(f"Invalid LTL formula: {ltl_formula}")
        return ltl_formula
    except Exception as e:
        raise ValueError(f"Failed to parse safety property: {safety_property}. Error: {str(e)}")
    
# Function to refine only the erroneous lines in the NuSMV model using LLM
def refine_nusmv_model(nusmv_model, error_log):
    prompt = f"""
        The following NuSMV model contains syntax errors:

        **Errors:**
        {error_log}

        **Incorrect NuSMV Model:**
        {nusmv_model}

        **Fix Instructions:**
        - Correct the syntax errors in the `TRANS` section.
        - Ensure all `next(variable) :=` statements are properly formatted.
        - Ensure all `case` blocks end with `esac;`.
        - Do not introduce new syntax errors.
        - Follow the strict NuSMV syntax rules provided in the prompt.

        **Example of Correct NuSMV Syntax:**
        ```smv
        MODULE main
        VAR
        device1 : boolean;
        device2 : {{off, low, medium, high}};

        ASSIGN
        init(device1) := FALSE;
        init(device2) := off;

        next(device1) := 
            case
            condition1 : TRUE;
            condition2 : FALSE;
            TRUE : device1;
            esac;

        LTLSPEC
        G(!(device1 & device2 != off))

    **Return only the corrected NuSMV model.**
    """

    try:
        response = invoke_llm(prompt)
        corrected_model = response.strip()
        return corrected_model
    except Exception as e:
        print(f"❌ Error refining NuSMV model: {e}")
        return nusmv_model  # Return the original model if refinement fails


def is_valid_nusmv_model(model_content):
    # Check for markdown formatting
    if "```" in model_content:
        return False
    # Add other checks if necessary
    return True

# def clean_nusmv_model(model_content):
#     """
#     Clean the NuSMV model by removing markdown formatting and repeated sections.
#     """
#     # Remove markdown formatting
#     model_content = re.sub(r"```(?:smv|plaintext)?\n", "", model_content)
#     model_content = re.sub(r"\n```", "", model_content)

#     # Remove unnecessary text
#     model_content = re.sub(r"Here is the corrected code:", "", model_content)
#     model_content = re.sub(r"Here is the corrected code in the format you requested:", "", model_content)

#     # Remove duplicate sections
#     lines = model_content.split("\n")
#     unique_lines = []
#     for line in lines:
#         if line.strip() not in unique_lines:
#             unique_lines.append(line.strip())
#     cleaned_model = "\n".join(unique_lines)

#     # Ensure the model starts with MODULE main and ends with LTLSPEC
#     if not cleaned_model.startswith("MODULE main"):
#         cleaned_model = "MODULE main\n" + cleaned_model
#     if not cleaned_model.strip().endswith("LTLSPEC"):
#         cleaned_model += "\nLTLSPEC"

#     return cleaned_model

import re

def clean_nusmv_model(model_content):
    """
    Cleans the NuSMV model by:
    - Removing markdown formatting (` ```smv `)
    - Fixing incorrect `TRANS` keyword (should be `ASSIGN`)
    - Ensuring boolean conditions explicitly check `= TRUE`
    - Fixing `!=` in logical conditions (`device2 != off` -> `!(device2 = off)`)
    - Adding necessary parentheses for logical conditions
    """

    # Remove markdown formatting if present
    model_content = re.sub(r"```(?:smv|plaintext)?\n", "", model_content)
    model_content = re.sub(r"\n```", "", model_content)

    # Replace incorrect `TRANS` with `ASSIGN`
    model_content = re.sub(r"\bTRANS\b", "ASSIGN", model_content)

    # Fix boolean conditions in `case` blocks (avoid modifying already correct conditions)
    model_content = re.sub(r"(\bnext\(\w+\)\s*:=\s*case\s*)(\w+)\s*:", r"\1\2 = TRUE :", model_content)

    # Fix logical conditions: Ensure `!=` is properly formatted (`device2 != off` -> `!(device2 = off)`)
    model_content = re.sub(r"(\w+)\s*!=\s*(\w+)", r"!(\1 = \2)", model_content)

    # Ensure proper case block endings with `esac;`
    model_content = re.sub(r"(esac)(?!;)", r"\1;", model_content)

    # Ensure proper LTL logical formatting (avoid nested `!(...)` errors)
    model_content = re.sub(r"(LTLSPEC\s+G\s*\(\s*)!(\w+\s*&\s*\w+\s*=\s*\w+)\)", r"\1(!\2))", model_content)

    return model_content.strip()


nusmv_generation_prompt = """
You are an expert in NuSMV model generation. Your task is to create a **fully correct and NuSMV-compliant** model **without syntax errors**.

**Input Details:**
- Scenarios: {scenarios}
- Safety Properties: {safety_properties}

**Strict NuSMV Requirements:**
1. Use `MODULE main` as the root module.
2. Define all necessary variables under the `VAR` section.
3. Initialize all variables correctly under the `ASSIGN` section.
4. Use `ASSIGN` for state transitions instead of `TRANS`:
   - Use `next(variable) := value;` for assignments.
   - Use `case` blocks for conditional transitions, and ensure each `case` block ends with `esac;`.
   - Do not use `:=` outside of `next(variable) :=` assignments.
5. Safety properties must be in `LTLSPEC` format with valid LTL syntax.
6. Use boolean (`TRUE/FALSE`) and integer variables properly.
7. Use `low, medium, high` notation for multi-valued states.
8. Ensure no missing variables or undefined references.
9. **DO NOT** include explanations, comments, or markdown formatting (e.g., backticks, ```smv).
10. **DO NOT** include text like "Here is your NuSMV model:".
11. **DO NOT** repeat sections or generate invalid syntax.
12. **DO NOT** include any text outside the NuSMV model (e.g., no "Here is the corrected code" or similar).
13. **DO NOT** generate multiple `MODULE main` sections. Only one `MODULE main` is allowed.
14. **Generate only the `LTLSPEC` statements that correspond to the provided safety properties.**

**Example of Correct NuSMV Syntax:**
MODULE main
VAR
    motion_sensor : boolean;
    time : 0..24;
    temperature : 60..100;
    movie_mode : boolean;
    doors_closed : boolean;
    no_motion : boolean;
    
    Virtual_Light : boolean;
    Virtual_AC1 : boolean;
    Virtual_AC2 : boolean;
    Virtual_AC3 : boolean;
    Virtual_Fan1 : boolean;
    Virtual_Fan2 : boolean;
    Virtual_Fan4 : {{off, low, medium, high}};  -- Ensuring valid enum type
    Virtual_Fan5 : {{off, low, high}};  -- Ensuring valid enum type
    Virtual_TV1 : {{off, on, muted}};
    Virtual_TV2 : boolean;
    Virtual_Fridge1 : boolean;

ASSIGN
    -- Scenario rules
    init(Virtual_Light) := FALSE;
    init(Virtual_AC1) := FALSE;
    init(Virtual_AC2) := FALSE;
    init(Virtual_AC3) := FALSE;
    init(Virtual_Fan1) := FALSE;
    init(Virtual_Fan2) := FALSE;
    init(Virtual_Fan4) := off;
    init(Virtual_Fan5) := off;
    init(Virtual_TV1) := off;
    init(Virtual_TV2) := FALSE;
    init(Virtual_Fridge1) := FALSE;
    
    next(Virtual_Light) := case
        motion_sensor = TRUE : TRUE;
        time = 6 : FALSE;
        TRUE : Virtual_Light;
    esac;
    
    next(Virtual_AC1) := case
        motion_sensor = TRUE : TRUE;
        TRUE : Virtual_AC1;
    esac;
    
    next(Virtual_AC2) := case
        temperature > 80 : TRUE;
        TRUE : Virtual_AC2;
    esac;

    next(Virtual_AC3) := case
        (doors_closed & no_motion) = TRUE : FALSE;
        TRUE : Virtual_AC3;
    esac;

    next(Virtual_Fan1) := case
        time = 6 : FALSE;
        TRUE : Virtual_Fan1;
    esac;

    next(Virtual_Fan2) := case
        time = 22 : FALSE;
        TRUE : Virtual_Fan2;
    esac;

    next(Virtual_Fan4) := case
        temperature > 85 : medium;  -- Matching enum type
        temperature > 80 : low;  -- Matching enum type
        TRUE : Virtual_Fan4;
    esac;

    next(Virtual_Fan5) := case
        movie_mode = TRUE : low;  -- Matching enum type
        TRUE : Virtual_Fan5;
    esac;

    next(Virtual_TV1) := case
        no_motion = TRUE : muted;
        TRUE : Virtual_TV1;
    esac;

    next(Virtual_TV2) := case
        movie_mode = TRUE : TRUE;
        TRUE : Virtual_TV2;
    esac;

    next(Virtual_Fridge1) := case
        motion_sensor = TRUE : TRUE;
        TRUE : Virtual_Fridge1;
    esac;

LTLSPEC G (temperature < 70 -> !Virtual_AC3);
LTLSPEC G (Virtual_AC2 -> temperature <= 78);
LTLSPEC G ((Virtual_Fan5 != off) -> F motion_sensor);
LTLSPEC G (temperature > 85 -> Virtual_Fan4 = medium);

### Key Adjustments for Scenario-to-NuSMV Mapping

1. **Scenario Parsing**:
   - Each scenario should be parsed into a `next(variable) :=` or `case` statement in the `ASSIGN` section.
   - For example:
     - Scenario: "When motion is detected by the Motion Sensor, turn on the Virtual Light."
     - NuSMV Logic:
       next(Virtual_Light) :=
           case
               motion_sensor = TRUE : TRUE;
               TRUE : Virtual_Light;
           esac;

2. **Safety Property Integration**:
   - The safety properties should be translated into `LTLSPEC` statements.
   - For example:
     - Safety Property: "Virtual Light must turn off automatically if no motion is detected for 10 minutes."
     - NuSMV Logic:
       LTLSPEC G (no_motion_for_10_minutes -> next(Virtual_Light) = FALSE);

3. **Variable Definitions**:
   - Ensure all variables used in the scenarios and safety properties are defined in the `VAR` section.
   - For example:
     VAR
         motion_sensor : boolean;
         Virtual_Light : boolean;
         no_motion_for_10_minutes : boolean;
     
**Final Output**:  
Return **only** the correctly formatted NuSMV model, with no extra text.
"""

def generate_nusmv_model(scenarios, safety_properties):
    prompt = nusmv_generation_prompt.format(
        scenarios="\n- ".join(scenarios),
        safety_properties="\n- ".join(safety_properties))
    response = invoke_llm(prompt)
    cleaned_model = clean_nusmv_model(response.strip())
    
    return cleaned_model

def generate_valid_nusmv_model(scenarios, safety_properties, output_file="generated_model.smv"):
    iteration = 0
    last_error_log = None
    nusmv_model = None

    while True:  # Run indefinitely until no syntax errors
        iteration += 1
        print(f"\n=== Iteration {iteration}: Generating & Validating NuSMV Model ===")

        if iteration == 1:
            # Generate the initial NuSMV model
            nusmv_model = generate_nusmv_model(scenarios, safety_properties)
        else:
            # Refine the model based on the last error log
            nusmv_model = refine_nusmv_model(nusmv_model, last_error_log)

        # Print the NuSMV model for debugging
        print(f"\n🔍 NuSMV Model (Iteration {iteration}):\n{nusmv_model}\n")

        # Save the generated model to the specified output file
        with open(output_file, "w") as file:
            file.write(nusmv_model)

        # Validate the NuSMV model
        is_valid, error_log = validate_nusmv_model(output_file)

        if is_valid:
            print(f"\n✅ NuSMV model validated successfully after {iteration} iterations.\n")
            return nusmv_model  # Exit the loop and return the valid model

        # If there are syntax errors, log them and continue refining
        print("\n Syntax error detected:")
        print(error_log)

        # Extract the exact line causing the error
        error_lines = extract_nusmv_errors(error_log, nusmv_model)
        if error_lines:
            print("\n🔧 Error Details:")
            for line_num, failed_code, error_msg in error_lines:
                print(f"Line {line_num}: {failed_code} -> {error_msg}")

        last_error_log = error_log


def extract_nusmv_errors(nusmv_output, model_content):
    errors = re.findall(r"file generated_model.smv: line (\d+): (.+)", nusmv_output)
    if not errors:
        return None  # No errors found

    failed_lines = []
    for line_num, error_msg in errors:
        try:
            line_num = int(line_num)
            failed_code = model_content.split("\n")[line_num - 1]  # Extract that line
            failed_lines.append((line_num, failed_code, error_msg))
        except IndexError:
            failed_lines.append((line_num, "UNKNOWN (line not found)", error_msg))

    return failed_lines

# =============================================
# Process 2: Iterative Model Regeneration to Minimize Violations
# =============================================

def validate_nusmv_model(model_file):
    try:
        result = subprocess.run(
            ["NuSMV", model_file],
            capture_output=True,
            text=True
        )

        # If the command succeeds, return True and the output
        if result.returncode == 0:
            return True, result.stdout  # Return the standard output

        # If the command fails, return False and the error message
        return False, result.stderr

    except FileNotFoundError:
        error_message = "NuSMV not found. Ensure it is installed and available in your PATH."
        print(error_message)
        return False, error_message

    except Exception as e:
        error_message = f"Error running NuSMV: {e}"
        print(error_message)
        return False, error_message

def extract_nusmv_violations(nusmv_output):
    if nusmv_output is None:
        print("⚠️ No NuSMV output provided. Cannot extract violations.")
        return []

    # Extract all lines where an LTLSPEC is false
    violation_pattern = r"-- specification .*? is false"
    violations = re.findall(violation_pattern, nusmv_output)

    return violations

def is_valid_nusmv_code(content):
    """
    Checks if the content is a valid NuSMV model.
    """
    # Basic validation: Ensure the content contains key NuSMV components
    required_keywords = ["MODULE main", "VAR", "ASSIGN", "LTLSPEC"]
    return all(keyword in content for keyword in required_keywords)

def minimize_violations_with_llm(input_model_path, output_model_path, scenarios, safety_properties, max_iterations=50):
    print("\n🔄 Starting iterative violation minimization...")

    iteration = 0
    violations = []
    current_model_path = input_model_path

    while iteration < max_iterations:
        iteration += 1
        print(f"\n=== Iteration {iteration} ===")

        # Step 1: Validate the current model file
        is_valid, validation_output = validate_nusmv_model(current_model_path)

        if not is_valid:
            print("\n❌ Model contains syntax errors. Attempting correction first.")

            # ✅ Read model content from file
            with open(current_model_path, "r") as file:
                model_content = file.read()

            # ✅ Pass content to LLM for syntax correction
            syntax_fixed_model = refine_nusmv_model(model_content, validation_output)

            print("\n📄 Syntax-corrected model:\n")
            print(syntax_fixed_model)

            # Save syntax-fixed model
            with open(output_model_path, "w") as file:
                file.write(syntax_fixed_model)

            print("\n✅ Syntax errors corrected. Retrying validation.")
            current_model_path = output_model_path
            continue

        # Step 2: Check for violations
        violations = extract_nusmv_violations(validation_output)

        if not violations:
            print("\n✅ No violations detected. Model is now valid.")
            return True

        print(f"\n🚨 **Detected {len(violations)} failing LTL properties.**")
        for v in violations:
            print(f" - {v}")

        # Step 3: Load model content for prompt
        with open(current_model_path, "r") as file:
            model_content = file.read()

        # Step 4: Build LLM prompt
        prompt = f"""
        **Task: Fix All LTL Violations in NuSMV Model**

        **Current Model:**
        ```
        {model_content}
        ```

        **Violations:**
        {violations}

        **Scenarios:**
        ```
        {"; ".join(scenarios)}
        ```

        **Safety Properties:**
        ```
        {"; ".join(safety_properties)}
        ```

        - Modify the `ASSIGN` section to fix all violations.
        - Each `case` block must end with `esac;`.
        - Do not introduce new syntax errors or undefined variables.
        - Return **only** the corrected NuSMV model—no extra text or formatting.
        """

        try:
            response = invoke_llm(prompt)

            if response is None:
                print("\n❌ No response received from LLM.")
                continue

            response = response.strip()

            print("\n🔄 LLM Response (Regenerated Model):")
            print(response)

            if not is_valid_nusmv_code(response):
                print("\n❌ LLM returned invalid NuSMV code. Retrying...")
                continue

            # Save regenerated model
            with open(output_model_path, "w") as file:
                file.write(response)

            print(f"\n✅ Model successfully regenerated and saved to `{output_model_path}`.")

            # Validate regenerated model
            is_valid, validation_output = validate_nusmv_model(output_model_path)

            if not is_valid:
                print("\n❌ Model still contains syntax errors. Will retry.")
                current_model_path = output_model_path
                continue

            # Check updated violations
            new_violations = extract_nusmv_violations(validation_output)
            if len(new_violations) < len(violations):
                print(f"\n✅ Violations reduced from {len(violations)} to {len(new_violations)}.")
                violations = new_violations
            else:
                print("\n⚠️ No reduction in violations. Continuing...")

            current_model_path = output_model_path

            if not violations:
                print("\n✅ **All LTL properties satisfied. Final model is valid.**")
                return True

        except Exception as e:
            print(f"\n❌ Error regenerating model: {e}")
            continue

    print(f"\n❌ Failed to minimize violations after {max_iterations} iterations.")
    return False



def regenerate_transition_rules(scenarios, nusmv_error):
    prompt = f"""
    The following NuSMV model has detected violations:
    {nusmv_error}

    Modify the transition rules to reduce violations.
    """
    try:
        response = invoke_llm(prompt)
        return eval(response.strip())
    except Exception as e:
        print(f"❌ Error regenerating transition rules: {e}")
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
    response = invoke_llm(prompt)
    return response.strip()  # Clean the output

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
    # devices = get_smartthings_devices()
    # if not devices:
    #     print("No devices retrieved from SmartThings. Exiting.")
    #     exit()

    # Step 2: Collect and validate scenarios
    validated_scenarios = scenarios1

    # Step 3: Collect safety properties
    validated_safety_properties = safety_properties3

    # Step 4: Prompt-Based Validation

    # prompt_violations, compliant_scenarios = prompt_based_validation(
    #     validated_scenarios, validated_safety_properties
    # )

    # Display prompt-based validation results
    # if prompt_violations:
    #     print("\nConflicts detected in prompt-based validation:")
    #     for i, violation in enumerate(prompt_violations, 1):
    #         print(f"\nConflict {i}:")
    #         print(f"Scenario: {violation['scenario']}")
    #         print(f"Safety Property: {violation['property']}")
    #         print(f"Response: {violation['response']}")
    # else:
    #     print("\nNo conflicts detected in prompt-based validation.")

    # model_file = "./Ground-Truth-NuSMV-test/1-1.smv"
    model_file = "generated_model.smv"
    # Generate the NuSMV model using the LLM
    # iteration_count, success, final_nusmv_model = nusmv_syntax_regeneration(validated_scenarios, validated_safety_properties, model_file)

    # if success:
    #     print(f"\n NuSMV model validated successfully after {iteration_count} iterations.")
    # else:
    #     print(f"\n Failed to generate a valid NuSMV model after {iteration_count} iterations.")
    #     print("Error details:", final_nusmv_model)
    # valid_nusmv_model = generate_valid_nusmv_model(validated_scenarios, validated_safety_properties, model_file)

    # if valid_nusmv_model:
    #     print("\n✅ Process 1 completed successfully. Ready for Process 2!")
    # else:
    #     print("\n❌ Failed to generate a valid NuSMV model. Exiting.")
    

    # Step 5: NuSMV Validation with Infinite Retry Mechanism

    # print("\nGenerating NuSMV model and running formal verification...")

    # model_file = "generated_model.smv"
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
    # final_scenarios = minimize_violations_with_llm(model_file, validated_scenarios, validated_safety_properties)
    # Input and output NuSMV files
    input_model = "./Ground-Truth-NuSMV-gwen/3-4.smv"
    output_model = "./Ground-Truth-NuSMV-gwen/3-4-8-regen.smv"

    # Run the iterative violation minimization
    minimize_violations_with_llm(input_model, output_model, scenarios3, safety_properties4)


    # Step 6: Convert scenarios to YAML
    # yaml_file = scenarios_to_yaml(validated_scenarios)

    # Step 7: Apply scenarios via SmartThings API
    # apply_scenarios_to_smartthings(yaml_file)


