import subprocess
import re
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import PPOTrainer, PPOConfig

# Load the model and tokenizer
model_name = "meta-llama/LLaMA-7b"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name).cuda()

# Function to generate multiple candidate outputs
def generate_candidates(input_prompt, num_samples=5):
    inputs = tokenizer(f"Input: {input_prompt}", return_tensors="pt").to("cuda")
    outputs = model.generate(
        **inputs,
        max_length=512,
        num_return_sequences=num_samples,
        do_sample=True
    )
    return [tokenizer.decode(output, skip_special_tokens=True) for output in outputs]

# Function to run NuSMV on a candidate
def run_nusmv(candidate, file_name="temp.smv"):
    # Write the candidate to a temporary SMV file
    with open(file_name, "w") as f:
        f.write(candidate)

    # Run NuSMV on the file
    try:
        result = subprocess.run(
            ["nusmv", file_name],
            text=True,
            capture_output=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return e.stderr

# Function to parse NuSMV results
def parse_nusmv_results(output):
    spec_pattern = r"-- specification\s+(.*?)\s+is\s+(true|false)"
    results = []
    for match in re.finditer(spec_pattern, output):
        spec, status = match.groups()
        results.append({"specification": spec.strip(), "status": status.strip()})
    return results

# Function to compute rewards based on satisfied specifications
def compute_rewards(parsed_results):
    return sum(1 for result in parsed_results if result["status"] == "true")

# Function to rank candidates based on rewards
def rank_candidates(candidates, rewards):
    ranked = sorted(zip(candidates, rewards), key=lambda x: x[1], reverse=True)
    return ranked

# Set up PPO fine-tuning configuration
ppo_config = PPOConfig(
    model_name=model_name,
    learning_rate=5e-6,
    batch_size=4,
    mini_batch_size=2
)

# Instantiate PPO trainer
ppo_trainer = PPOTrainer(
    model=model,
    tokenizer=tokenizer,
    config=ppo_config
)

# Training loop
input_prompts = [  # Replace with your actual prompts
    "If the time is 6pm, turn off the Centralite Outlet 1.",
    "Ensure all devices are turned off by 11:30pm."
]

for input_prompt in input_prompts:
    # Step 1: Generate candidates
    candidates = generate_candidates(input_prompt)

    # Step 2: Verify and compute rewards
    rewards = []
    for candidate in candidates:
        nusmv_output = run_nusmv(candidate)
        parsed_results = parse_nusmv_results(nusmv_output)
        rewards.append(compute_rewards(parsed_results))

    # Step 3: Rank candidates
    ranked_candidates = rank_candidates(candidates, rewards)

    # Step 4: Use the best candidate to fine-tune
    best_candidate = ranked_candidates[0][0]
    reward = ranked_candidates[0][1]

    # Fine-tune using PPO
    ppo_trainer.step(input_prompt, [best_candidate], [reward])

# Save the fine-tuned model
model.save_pretrained("./fine_tuned_model")
tokenizer.save_pretrained("./fine_tuned_model")

# Print ranked outputs for reference
for rank, (output, score) in enumerate(ranked_candidates, 1):
    print(f"Rank {rank}: {output} (Satisfied Specs: {score})")
