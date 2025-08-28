"""Requirements:

GitPython
"""
import yaml

# Reading YAML file
with open("config.yaml", "r") as f:
    data = yaml.safe_load(f)
print(data)

# Writing YAML file
with open("output.yaml", "w") as f:
    yaml.dump(data, f, default_flow_style=False)
from git import Repo


repo = Repo(".")
diff_text = repo.git.diff("HEAD~1", "HEAD")  # last commit diff
print(diff_text)

files = {}
current_file = None
for line in diff_text.splitlines():
    if line.startswith("diff --git"):
        parts = line.split(" ")
        current_file = parts[-1]
        files[current_file] = {"added": [], "removed": []}
    elif line.startswith("+") and not line.startswith("+++"):
        files[current_file]["added"].append(line[1:])
    elif line.startswith("-") and not line.startswith("---"):
        files[current_file]["removed"].append(line[1:])

print(files)