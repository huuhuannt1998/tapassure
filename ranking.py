import subprocess
import re

def run_nusmv(file_path):
    """
    Runs the NuSMV model checker on the given file and captures its output.
    
    Args:
        file_path (str): Path to the NuSMV file.
        
    Returns:
        str: Output of the NuSMV command.
    """
    try:
        result = subprocess.run(
            ["nusmv", file_path],
            text=True,
            capture_output=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print("Error running NuSMV:")
        print(e.stderr)
        return None

def parse_nusmv_results(nusmv_output):
    """
    Parse NuSMV output to extract specifications and their statuses.
    """
    results = []
    spec_pattern = r"-- specification\s+(.*?)\s+is\s+(true|false)"
    
    for match in re.finditer(spec_pattern, nusmv_output):
        spec, status = match.groups()
        results.append({
            "specification": spec.strip(),
            "status": status.strip()
        })
    
    return results

def main():
    # Path to your NuSMV file
    smv_file_path = "form_model.smv"
    
    # Step 1: Run NuSMV
    nusmv_output = run_nusmv(smv_file_path)
    if nusmv_output is None:
        return
    
    # Step 2: Parse the results
    parsed_results = parse_nusmv_results(nusmv_output)
    
    # Step 3: Print results
    for result in parsed_results:
        print(f"Specification: {result['specification']}, Status: {result['status']}")

# Run the main function
if __name__ == "__main__":
    main()
