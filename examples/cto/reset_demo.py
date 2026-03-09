import os
import shutil


def reset_demo():
    print("=== ClawGraph Demo Reset ===")

    # Path to generated artifacts
    base_dir = os.path.dirname(os.path.abspath(__file__))
    generated_dir = os.path.join(base_dir, "artifacts", "generated")

    if os.path.exists(generated_dir):
        print(f"Clearing generated artifacts in: {generated_dir}")
        shutil.rmtree(generated_dir)
        os.makedirs(generated_dir)
        print("Done.")
    else:
        print("No generated artifacts found to clear.")
        os.makedirs(generated_dir, exist_ok=True)

    # Clear any __pycache__ in the cto folder
    for root, dirs, _files in os.walk(base_dir):
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            print(f"Removing {pycache_path}")
            shutil.rmtree(pycache_path)

    print("Demo reset successfully.")


if __name__ == "__main__":
    reset_demo()
