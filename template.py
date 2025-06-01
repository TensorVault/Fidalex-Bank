import os

project_root = "Fidalex-Bank"  # Use exact folder name as per Windows

structure = {
    ".vscode": ["settings.json", "launch.json"],
    "services": {
        "auth_service": {
            "auth_service": [
                "__init__.py", "main.py",
                "models/", "routes/", "schemas/", "services/", "utils/"
            ],
            "tests/": [],
            "Dockerfile": "",
            "requirements.txt": "",
            "setup.py": "",
            ".env": ""
        },
        "account_service": {},
        "transaction_service": {},
        "payment_service": {},
        "loan_credit_service": {},
        "chatbot_service": {},
        "insights_service": {}
    },
    "api-gateway": ["main.py", "routes/", "requirements.txt"],
    "streamlit-ui": ["main.py", "pages/", "assets/", "requirements.txt", ".env"],
    "common": ["models/", "schemas/", "config.py", "utils/"],
    "scripts": ["migrate.sh", "seed_data.py", "init_db.py"],
    "deployments": ["docker-compose.yml", "k8s/", "terraform/"],
    "tests": ["integration/", "e2e/"],
    "env/": [],
    "": [".env.dev", ".env.test", ".env.staging", ".env.prod", "requirements.txt", "pyproject.toml", "README.md", ".gitignore"]
}

def create_structure(base_path, struct):
    for name, content in struct.items():
        if isinstance(content, dict):
            dir_path = os.path.join(base_path, name)
            os.makedirs(dir_path, exist_ok=True)
            create_structure(dir_path, content)
        elif isinstance(content, list):
            dir_path = os.path.join(base_path, name)
            os.makedirs(dir_path, exist_ok=True)
            for item in content:
                full_path = os.path.join(dir_path, item.strip("/"))
                if item.endswith("/"):
                    if not os.path.exists(full_path):
                        os.makedirs(full_path)
                else:
                    if not os.path.exists(full_path):
                        with open(full_path, "w") as f:
                            f.write("")
        elif isinstance(content, str):
            file_path = os.path.join(base_path, name)
            if not os.path.exists(file_path):
                with open(file_path, "w") as f:
                    f.write("")

# 🔍 Locate the project path correctly (where this script runs)
base_path = os.path.join(os.getcwd(), project_root)

if os.path.exists(base_path):
    print(f"🔄 Adding missing folders/files to existing '{project_root}' at: {base_path}")
else:
    os.makedirs(base_path)
    print(f"🆕 Created new '{project_root}' at: {base_path}")

create_structure(base_path, structure)
print("✅ Project structure is now complete (without duplication).")
