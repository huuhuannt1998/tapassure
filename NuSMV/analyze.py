import subprocess
import re

def run_nusmv_and_analyze(nusmv_path, smv_file):
    spec_results = []
    spec_true_count = 0
    spec_false_count = 0

    try:
        process = subprocess.run(
            [nusmv_path, smv_file],
            capture_output=True,
            text=True
        )
        output = process.stdout
        error_output = process.stderr

        print("NuSMV Output:\n", output)
        if error_output.strip():
            print("NuSMV Errors:\n", error_output)

        if process.returncode != 0:
            print(f"NuSMV failed with error:\n{error_output}")
            return None

        spec_true_pattern = re.compile(r"-- specification.*is true", re.IGNORECASE)
        spec_false_pattern = re.compile(r"-- specification.*is false", re.IGNORECASE)

        for line in output.splitlines():
            true_match = spec_true_pattern.match(line.strip())
            if true_match:
                spec_results.append({"spec": true_match.group(), "result": "true"})
                spec_true_count += 1
                continue

            false_match = spec_false_pattern.match(line.strip())
            if false_match:
                spec_results.append({"spec": false_match.group(), "result": "false"})
                spec_false_count += 1

        return {
            "total_specs": spec_true_count + spec_false_count,
            "true_count": spec_true_count,
            "false_count": spec_false_count,
            "details": spec_results,
        }

    except subprocess.CalledProcessError as e:
        print(f"Error running NuSMV: {e}")
        return None

if __name__ == "__main__":
    nusmv_path = r"C:\Program Files\NuSMV\NuSMV-2.7.0-win64\bin\NuSMV.exe" 

    smv_file = "scenario10.smv"

    summary = run_nusmv_and_analyze(nusmv_path, smv_file)

    if summary:
        print(f"Total SPECs: {summary['total_specs']}")
        print(f"True SPECs: {summary['true_count']}")
        print(f"False SPECs: {summary['false_count']}")
        print("\nDetails:")
        for spec in summary["details"]:
            print(f"  - {spec['spec']} : {spec['result']}")
