#!/usr/bin/env python3
# 2_directory_organizer.py - Organizes files into a proper directory structure

import os
import shutil
import logging
import re
import json
from pathlib import Path # Use pathlib

# Configure logging
# Assume logger is configured externally or remove if running standalone
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- ADAPT THIS SECTION ---

# Project root directory name (Change if desired)
PROJECT_DIR_NAME = "quantum_kaleidoscope"

# Define the target directory structure (Review, add, remove as needed)
# Keys are the subdirectory names within PROJECT_DIR_NAME
# Values indicate if __init__.py should be created (True for Python packages)
DIRECTORIES = {
    "backend": True,             # Main backend code
    "backend/core": True,        # Core system components
    "backend/nodes": True,       # Node implementations
    "backend/engines": True,     # Processing engines
    "backend/llm": True,         # LLM integration
    "backend/quantum": True,     # Quantum-specific logic
    "backend/visualization_backend": True, # Visualization backend logic
    "backend/utils": True,       # Utility functions
    "backend/security": True,    # Security related code
    "backend/pipeline": True,    # Data pipeline
    "backend/memory": True,      # Memory components
    "backend/tests": True,       # Backend tests
    "config": False,             # Configuration files (YAML, JSON) - Moved to root for easier access
    "data": False,               # Data files (e.g., sample data) - Moved to root
    "logs": False,               # Log files - Moved to root
    "infrastructure": False,     # Terraform, CloudFormation, Dockerfiles for deployment
    "scripts": False,            # Utility scripts (setup, deployment)
    "docs": False,               # Documentation files (.md)
    "frontend": False,           # Root for React frontend project
    "frontend/public": False,
    "frontend/src": False,
    "nginx": False,              # Nginx specific configuration
    # Add any other top-level directories you need
}


# File to specific directory mappings (VERY IMPORTANT - Review and update!)
# Maps FILENAME (after potential renaming by script 1) to the TARGET DIRECTORY
# Paths are relative to the PROJECT_DIR_NAME created by this script.
FILE_MAPPINGS = {
    # Backend Core Logic
    "app.py": "backend", # Main application entry point
    "common.py": "backend/utils",
    "system_bus.py": "backend/core", # Communication
    "system_orchestrator.py": "backend/core",
    "system_consciousness.py": "backend/core", # If you keep this structure
    "node_manager.py": "backend/core", # Manages node lifecycle
    "cluster_manager.py": "backend/core", # Manages clusters of nodes/supernodes

    # Nodes
    "node.py": "backend/nodes",
    "node_types.py": "backend/nodes", # Renamed from Nodes_1.txt
    "living_node.py": "backend/nodes",
    "node_dna_module.py": "backend/nodes", # DNA logic
    "node_energy_module.py": "backend/nodes",
    "node_memory_module.py": "backend/memory", # Moved memory here
    "node_neuralcore_module.py": "backend/nodes", # Neural core for node
    "node_communication.py": "backend/nodes", # Specific node comms

    # Engines
    "quantum_engine.py": "backend/quantum", # Moved quantum logic
    "kaleidoscope_engine.py": "backend/engines",
    "mirror_engine.py": "backend/engines",
    "perspective_engine.py": "backend/engines",
    "engine_system.py": "backend/engines",
    "advanced_algorithms.py": "backend/engines", # Renamed from info2.txt

    # LLM Integration
    "ollama_client.py": "backend/llm",
    "chatbot.py": "backend/llm", # Group all chatbot logic here
    "enhanced_chatbot.py": "backend/llm",
    "learning_chatbot.py": "backend/llm",
    "chatbot_core.py": "backend/llm",
    "chatbot_learning.py": "backend/llm",
    "chatbot-integration.py": "backend/llm", # Keep related files together

    # SuperNode / Clustering
    "super_node.py": "backend/supernode", # New package for clarity
    "supernode_core.py": "backend/supernode",
    "supernode_cluster.py": "backend/supernode", # Added
    "pipelines_integration.py": "backend/pipeline", # Belongs in pipeline
    "evolution_system.py": "backend/supernode", # Related to node evolution

    # Cube / Router
    "cube_router.py": "backend/cube", # New package
    "hypercube_router.py": "backend/cube",
    "cube_core.py": "backend/cube",
    "cube_consciousness.py": "backend/cube",
    "intelligence_cube.py": "backend/cube", # From later scripts

    # Visualization (Backend Python part)
    "visualizer.py": "backend/visualization_backend",
    "hypercube_viz.py": "backend/visualization_backend",
    "quantum_cube_vis.py": "backend/visualization_backend",
    "visualization_system.py": "backend/visualization_backend",
    "advanced_cube_vis.py": "backend/visualization_backend",
    "molecular_viewer.py": "backend/visualization_backend",

    # Data Pipeline
    "data_pipeline_manager.py": "backend/pipeline",
    "data_pipeline.py": "backend/pipeline",
    "pipeline_integration.py": "backend/pipeline",
    "advanced-streaming.py": "backend/pipeline", # Streaming logic

    # Persistence
    "persistence-system.py": "backend/memory", # Renamed for consistency

    # Knowledge
    "knowledge-system.py": "backend/knowledge",
    "ml-optimization.py": "backend/knowledge",

    # Monitoring
    "monitoring_system.py": "backend/monitoring",
    "advanced-metrics.py": "backend/monitoring",
    "complete-metrics.py": "backend/monitoring",
    "deployment-monitor.py": "backend/monitoring",
    "monitoring-setup.py": "backend/monitoring",
    "telemetry_manager.py": "backend/monitoring", # Assuming this is monitoring related

    # Security
    "secure_pipeline.py": "backend/security",
    "godaddy-credentials.py": "backend/security", # Keep cred related code together
    "godaddy-integration.py": "backend/security",

    # Infrastructure Files (Place in 'infrastructure' folder)
    "main.tf": "infrastructure",
    "variables.tf": "infrastructure",
    "outputs.tf": "infrastructure",
    "terraform_infra.tf": "infrastructure",
    "complete-docker-aws.tf": "infrastructure", # Rename to something meaningful?
    "terraform-enhancements.tf": "infrastructure",
    "cloudformation.yml": "infrastructure", # Renamed from .txt if needed
    "Dockerfile": "./Dockerfile", # Main App Dockerfile often in root or backend
    "Dockerfile.ai-engine": "infrastructure/dockerfiles", # Suggest subdirectory
    "Dockerfile.chatbot": "infrastructure/dockerfiles",
    "docker-compose.yml": "./docker-compose.yml", # Keep compose in root
    "docker-compose.debug.yml": "./docker-compose.debug.yml", # Keep compose in root
    "aws-deployment.py": "infrastructure/scripts", # Deployment automation scripts
    "environment-deployment.py": "infrastructure/scripts",
    "dns-https-automation.py": "infrastructure/scripts",
    "automation-app.py": "infrastructure/scripts", # Or maybe root scripts?

    # Scripts (Utility / Setup) - Place in 'scripts' folder
    "deployment-script.sh": "scripts",
    "domain_setup.sh": "scripts",
    "godaddy-workaround.sh": "scripts",
    "launch-script.py": "scripts",
    "complete-launch.sh": "scripts",
    "deploy_aws.sh": "scripts",
    "deployment-script-continued.sh": "scripts",
    "environment-automation.sh": "scripts",
    "full-deployment.sh": "scripts",
    "project-structure.sh": "scripts",
    "cleanup_project.py": "scripts",
    "final_cleanup.py": "scripts",
    "fix_init__.py": "scripts",
    "1_file_renamer.py": "./", # Keep setup scripts in original root for now
    "2_directory_organizer.py": "./",
    "3_ollama_integration.py": "./",
    "4_fill_missing_modules.py": "./",
    "organize_project.py": "./",
    "organize_project_.py": "./", # Will be deleted if exists

    # Config Files - Place in 'config' folder
    "config.json": "config",
    "config.yml": "config", # If you create this
    "llm_config.json": "config",
    "base.yml": "config",
    "launch.json": "config", # Often IDE config, maybe root .vscode?
    "file-structure.txt": "docs", # Move to docs
    "github-cicd.yml": "./.github/workflows", # Standard location for GH Actions
    "monitoring-rules.yml": "config", # Renamed from .txt

    # Data Files - Place in 'data' folder
    "dataset.csv": "data",

    # Documentation / Root files
    "README.md": "./README.md", # Keep in project root
    "cube_theory.md": "docs", # Renamed from info1.txt
    "OLLAMA_INTEGRATION.md": "docs",
    "LICENSE": "./LICENSE", # Keep license in root
    "setup.py": "./setup.py", # Keep setup.py in root
    ".gitignore": "./.gitignore", # Keep .gitignore in root
    "requirements.txt": "./requirements.txt", # Keep requirements in root

    # Files to IGNORE (e.g., logs, specific generated files)
    "file_rename_mapping.log": None, # Ignore the log file from script 1
    "import_analysis.json": None, # Ignore the analysis file generated here
    "GDCREDZ.txt": None, # Ignore sensitive data file
    "super_node_dna.json": None, # Ignore generated output
    "membrane_results.json": None, # Ignore generated output
}

# Keywords to guess directory (Use cautiously - MAPPINGS are better)
# This is less reliable, prioritize explicit FILE_MAPPINGS
GUESS_MAPPINGS = {
    # Add keywords if needed, but explicit mapping is preferred
}

# Files to KEEP in the original directory (e.g., setup scripts themselves)
KEEP_IN_ORIGINAL_DIR = [
    "1_file_renamer.py",
    "2_directory_organizer.py",
    "3_ollama_integration.py",
    "4_fill_missing_modules.py",
    "file_rename_mapping.log",
    # Add any other files you specifically want to leave untouched in the source dir
]


# --- END ADAPTATION SECTION ---

def create_project_structure(project_base_path: Path):
    """Create the project directory structure."""
    if project_base_path.exists():
        logger.warning(f"Project directory '{project_base_path}' already exists. Files might be overwritten or skipped.")
    else:
        project_base_path.mkdir()
        logger.info(f"Created project directory: {project_base_path}")

    # Create subdirectories and __init__.py files
    for directory, create_init in DIRECTORIES.items():
        dir_path = project_base_path / directory # Use Path object directly
        try:
            dir_path.mkdir(parents=True, exist_ok=True) # Create parent dirs if needed
            if create_init:
                init_file = dir_path / '__init__.py'
                if not init_file.exists():
                    init_file.touch() # Create empty __init__.py
                    logger.debug(f"Created __init__.py in: {dir_path}")
        except Exception as e:
            logger.error(f"Failed to create directory or __init__.py for {dir_path}: {e}")
    logger.info("Project directory structure created/verified.")


def organize_files(source_dir: Path, project_base_path: Path):
    """Organize files according to mappings and create import analysis."""
    moved_files_count = 0
    skipped_files = []
    processed_sources = set() # Keep track of files already moved/copied

    # Use rglob to find all files, then process
    all_files = list(source_dir.rglob('*'))

    for file_path in all_files:
         # Skip directories and files already processed
        if not file_path.is_file() or file_path in processed_sources:
            continue

        # Skip files within the target project directory if it exists in source
        if project_base_path.resolve() in file_path.resolve().parents:
            logger.debug(f"Skipping file already inside target structure: '{file_path}'")
            processed_sources.add(file_path)
            continue

        file_name = file_path.name

        # Skip files designated to be kept in the original directory
        if file_name in KEEP_IN_ORIGINAL_DIR:
             logger.info(f"Skipping file intended to stay in source: '{file_name}'")
             processed_sources.add(file_path)
             continue

        target_dir_name = None
        target_path = None

        # 1. Check explicit mappings first
        mapped_to = FILE_MAPPINGS.get(file_name)

        if mapped_to is None and file_name.endswith(".py"):
             # Special case: check if it's one of the setup scripts by content
             try:
                 with open(file_path, 'r') as f_check:
                     content_check = f_check.read(100) # Read beginning
                     if '# 1_file_renamer.py' in content_check or \
                        '# 2_directory_organizer.py' in content_check or \
                        '# 3_ollama_integration.py' in content_check or \
                        '# 4_fill_missing_modules.py' in content_check:
                         logger.info(f"Identified setup script by content, keeping: '{file_name}'")
                         processed_sources.add(file_path)
                         continue
             except Exception:
                 pass # Ignore read errors here

        if mapped_to is not None:
             target_dir_name = mapped_to
        else:
            # 2. Try guessing based on keywords (Less reliable)
            for keyword, target_dir_key in GUESS_MAPPINGS.items():
                if re.search(rf'\b{re.escape(keyword)}\b', file_name, re.IGNORECASE):
                    target_dir_name = target_dir_key
                    logger.debug(f"Guessed target '{target_dir_key}' for '{file_name}' based on keyword '{keyword}'")
                    break # Use the first keyword match

        # Handle special locations (root, None for ignore)
        if target_dir_name == "./": # Root of the new project dir
             target_path = project_base_path / file_name
        elif target_dir_name is None: # Explicitly ignored
             logger.info(f"Ignoring file based on mapping: '{file_name}'")
             processed_sources.add(file_path)
             continue
        elif target_dir_name:
             target_path = project_base_path / target_dir_name / file_name
        else:
             logger.warning(f"No mapping or guess for '{file_name}'. Skipping.")
             skipped_files.append(file_name)
             processed_sources.add(file_path)
             continue

        # Move the file
        try:
            # Ensure the target subdirectory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # ** Using MOVE **
            logger.debug(f"Attempting to move '{file_path}' to '{target_path}'")
            shutil.move(str(file_path), str(target_path))
            # *****************

            logger.info(f"Moved '{file_name}' to '{target_path.relative_to(project_base_path.parent)}'")
            moved_files_count += 1
            processed_sources.add(file_path) # Mark original as processed
            processed_sources.add(target_path) # Mark destination as processed

        except FileNotFoundError:
             logger.error(f"Source file not found (maybe moved already or incorrect path?): {file_path}")
        except Exception as e:
             logger.error(f"Error moving '{file_name}' to '{target_path}': {e}")
             skipped_files.append(file_name) # Add to skipped if move fails
             processed_sources.add(file_path) # Mark original as processed


    logger.info(f"Organization attempt finished. Moved {moved_files_count} files.")
    if skipped_files:
        logger.warning("The following files were skipped or could not be moved:")
        for fname in skipped_files:
            logger.warning(f"  - {fname}")


def main():
    """Main function to organize files."""
    logger.info("Starting file organization process...")
    current_dir = Path.cwd() # Get current working directory as Path object
    project_target_path = current_dir / PROJECT_DIR_NAME

    # 1. Create the target project structure
    create_project_structure(project_target_path)

    # 2. Organize files from the current directory into the new structure
    organize_files(current_dir, project_target_path)

    # Note: Script 3 (Ollama) and Script 4 (Missing Modules) should be run *after* this
    # script, as they place files *within* the PROJECT_DIR_NAME structure.
    # Note: Script 2 used to create requirements.txt. This is better done *after*
    # organization based on actual imports, or manually maintained.

    logger.info(f"File organization complete. Project created in '{project_target_path}'")
    logger.warning("Original setup scripts and specified root files remain in the source directory.")
    logger.warning("Please review the structure in '%s' and manually move any skipped files.", PROJECT_DIR_NAME)
    logger.info("Next steps: Run script 3 (Ollama setup) and script 4 (Missing modules), then update import statements in your Python code.")


if __name__ == "__main__":
    main()
