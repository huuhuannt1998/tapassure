import requests
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

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
model = ChatOpenAI(model="gpt-4o")

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
    print("Welcome to the IoT Automation Rule Assistant!")
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
    print("\nStarting cross-validation of scenarios and safety properties...")
    print("This step ensures no scenario violates any defined safety property.\n")

    # Template for cross-validation
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
# MAIN WORKFLOW
#############################

# Step 1: Fetch SmartThings devices
devices = get_smartthings_devices()
if not devices:
    print("No devices retrieved from SmartThings. Exiting.")

# Step 2: Collect and validate scenarios
print("Welcome to the IoT Automation Assistant!")
validated_scenarios = interactive_device_validation(devices)

# Step 3: Transition to collecting safety properties
print("\nNow, let's define the safety properties for your IoT automation rules.")
validated_safety_properties = interactive_safety_property_validation(devices)

# Step 4: Cross-validation of scenarios and safety properties
print("\nStarting cross-validation of scenarios and safety properties...")
violations = cross_validate_scenarios_and_properties(validated_scenarios, validated_safety_properties)

# Step 5: Final result and next steps
if not violations:
    print("\nAll validations passed. Proceeding to YAML generation...")
    # Add YAML generation step here if needed
else:
    print("\nPlease resolve conflicts before proceeding to YAML generation.")
