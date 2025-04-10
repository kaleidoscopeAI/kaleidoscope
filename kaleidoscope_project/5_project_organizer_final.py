#!/usr/bin/env python3
# 5_project_organizer_final.py - Organizes files into the target structure, moving them.

import os
import shutil
import logging
import re
import json
from pathlib import Path

# --- Configuration ---
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ProjectOrganizerFinal")

# --- ADAPT THIS SECTION ---

# Target Project Directory Name
PROJECT_DIR_NAME = "quantum_kaleidoscope"

# Target Directory Structure (Review and adjust as needed)
# True indicates it's a Python package and needs __init__.py
DIRECTORIES = {
    "backend": True,
    "backend/core": True,
    "backend/nodes": True,
    "backend/engines": True,
    "backend/llm": True,
    "backend/quantum": True,
    "backend/visualization_backend": True,
    "backend/utils": True,
    "backend/security": True,
    "backend/pipeline": True,
    "backend/memory": True,
    "backend/tests": True,
    "backend/supernode": True, # Added supernode package
    "backend/chatbot": True, # Added chatbot package
    "config": False,
    "data": False,
    "logs": False,
    "infrastructure": False,
    "infrastructure/scripts": False, # Subdir for deploy scripts
    "infrastructure/dockerfiles": False, # Subdir for specific dockerfiles
    "scripts": False,
    "docs": False,
    "frontend": False,
    "frontend/public": False,
    "frontend/src": False,
    "frontend/src/components": False, # Example frontend structure
    "nginx": False,
    # Add other necessary directories
}

# Explicit File Mappings (CRITICAL: Review and complete for ALL relevant files)
# Maps FILENAME (as it exists now after script 1 ran) -> TARGET DIRECTORY relative to PROJECT_DIR_NAME
# Use "./" for the root of PROJECT_DIR_NAME. Use None to explicitly ignore a file.
FILE_MAPPINGS = {
    # --- Core Backend ---
    "app.py": "backend",
    "main.py": "backend", # Assuming this is the FastAPI entry
    "common.py": "backend/utils",
    "system_bus.py": "backend/core",
    "system_orchestrator.py": "backend/core",
    "core-components.py": "backend/core",
    "system_consciousness.py": "backend/core",
    "node_manager.py": "backend/core", # Or backend/nodes? Decide.
    "cluster_manager.py": "backend/core",

    # --- Nodes ---
    "node.py": "backend/nodes",
    "BaseNode.py": "backend/nodes",
    "TextNode.py": "backend/nodes",
    "VisualNode.py": "backend/nodes",
    "CapabilityNode.py": "backend/nodes",
    "node_types.py": "backend/nodes", # From Nodes_1.txt
    "living_node.py": "backend/nodes",
    "node-core.py": "backend/nodes", # Assumed node core logic
    "node_dna_module.py": "backend/nodes",
    "node_energy_module.py": "backend/nodes",
    "node_neuralcore_module.py": "backend/nodes",
    "node_communication.py": "backend/nodes",

    # --- Engines ---
    "kaleidoscope_engine.py": "backend/engines",
    "mirror_engine.py": "backend/engines",
    "perspective_engine.py": "backend/engines",
    "engine-system.py": "backend/engines",
    "PatternRecognition.py": "backend/engines", # Assumed related
    "insight_generator.py": "backend/engines", # Assumed related
    "speculation_engine.py": "backend/engines",
    "advanced_algorithms.py": "backend/engines", # From info2.txt

    # --- LLM / Chatbot ---
    "ollama_client.py": "backend/llm",
    "chatbot.py": "backend/chatbot", # Put all chatbot variations here for now
    "enhanced_chatbot.py": "backend/chatbot",
    "learning_chatbot.py": "backend/chatbot",
    "chatbot_core.py": "backend/chatbot",
    "chatbot-learning.py": "backend/chatbot",
    "chatbot-integration.py": "backend/chatbot",
    "complete-chatbot-integration.py": "backend/chatbot",
    "llm_integration.py": "backend/llm",
    "GPTProcessor.py": "backend/llm",

    # --- SuperNode / Clustering ---
    "super_node.py": "backend/supernode",
    "supernode_core.py": "backend/supernode",
    "supernode_cluster.py": "backend/supernode", # If you have this
    "supernode-manager.py": "backend/supernode",
    "supernode-processor.py": "backend/supernode",
    "evolution_system.py": "backend/supernode",

    # --- Cube / Router ---
    "cube_router.py": "backend/cube",
    "hypercube_router.py": "backend/cube",
    "cube_core.py": "backend/cube",
    "cube_consciousness.py": "backend/cube",
    "intelligence_cube.py": "backend/cube",

    # --- Quantum ---
    "quantum_engine.py": "backend/quantum",
    "quantum-enhanced-core.py": "backend/quantum", # Assuming .py now
    "quantum-molecular-engine.py": "backend/quantum", # Assuming .py now
    "quantum-bio-system.py": "backend/quantum",
    "quantum-molecular-system.py": "backend/quantum",
    "quantum-drug.py": "backend/quantum",
    "avogadro-quantum-integration.py": "backend/quantum",
    "quantum-topology-optimizer.py": "backend/quantum", # Assuming .py now
    "quantum-resonance.py": "backend/quantum",
    "quantum-harmonics.py": "backend/quantum",
    "quantum-error-correction.py": "backend/quantum",
    "quantum-interface.py": "backend/quantum", # Interface with quantum systems
    "quantum-sync-protocol.py": "backend/quantum",
    "quantum_pimd.py": "backend/quantum", # Renamed from .txt

    # --- Visualization Backend ---
    "visualizer.py": "backend/visualization_backend",
    "hypercube_viz.py": "backend/visualization_backend",
    "quantum_cube_vis.py": "backend/visualization_backend",
    "visualization_system.py": "backend/visualization_backend",
    "advanced_cube_vis.py": "backend/visualization_backend",
    "molecular_viewer.py": "backend/visualization_backend",
    "visualization_integration.py": "backend/visualization_backend",
    "qsin-network-visualizer.py": "backend/visualization_backend",

     # --- Pipeline & Memory ---
    "data_pipeline.py": "backend/pipeline",
    "pipeline_integration.py": "backend/pipeline",
    "advanced-streaming.py": "backend/pipeline",
    "persistence-system.py": "backend/memory",
    "node_memory_module.py": "backend/memory",

    # --- Monitoring ---
    "monitoring_system.py": "backend/monitoring",
    "advanced-metrics.py": "backend/monitoring",
    "complete-metrics.py": "backend/monitoring",
    "deployment-monitor.py": "backend/monitoring",
    "monitoring-setup.py": "backend/monitoring",
    "telemetry_manager.py": "backend/monitoring",

    # --- Security ---
    "secure_pipeline.py": "backend/security",
    "godaddy-credentials.py": "backend/security",
    "godaddy-integration.py": "backend/security",
    "kaleidoscope_auth.py": "backend/security", # Authentication

    # --- Utils ---
    "utils.py": "backend/utils",
    "error_handler.py": "backend/utils", # Error handling utility
    "helper.py": "backend/utils", # Generic helper

    # --- Tests ---
    "test_ollama_client.py": "backend/tests",
    # Add other test files...

    # --- Config Files ---
    "config.json": "config",
    "config.yml": "config",
    "llm_config.json": "config",
    "base.yml": "config",
    "launch.json": "./.vscode", # Typically IDE config
    "monitoring-rules.yml": "config", # Renamed from .txt

    # --- Infrastructure ---
    "main.tf": "infrastructure",
    "variables.tf": "infrastructure",
    "outputs.tf": "infrastructure",
    "terraform_infra.tf": "infrastructure",
    "complete-docker-aws.tf": "infrastructure", # Needs clearer name
    "terraform-enhancements.tf": "infrastructure",
    "cloudformation_template.yml": "infrastructure", # Renamed from .txt
    "Dockerfile": "./Dockerfile", # Keep root Dockerfile for backend
    "Dockerfile.ai-engine": "infrastructure/dockerfiles",
    "Dockerfile.chatbot": "infrastructure/dockerfiles",
    "docker-compose.yml": "./docker-compose.yml",
    "docker-compose.debug.yml": "./docker-compose.debug.yml",
    "aws-deployment.py": "infrastructure/scripts",
    "environment-deployment.py": "infrastructure/scripts",
    "dns-https-automation.py": "infrastructure/scripts",
    "automation-app.py": "infrastructure/scripts",

    # --- Scripts ---
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
    "fix-script.py": "scripts",
    "run.sh": "scripts",
    "start_kaleidoscope.sh": "scripts",
    "finish_kaleidoscope_setup.sh": "scripts",


    # --- Documentation & Root Files ---
    "README.md": "./README.md",
    "cube_theory.md": "docs", # Renamed from info1.txt
    "OLLAMA_INTEGRATION.md": "docs",
    "LICENSE": "./LICENSE",
    "setup.py": "./setup.py", # Keeping setup.py in root
    ".gitignore": "./.gitignore",
    "requirements.txt": "./requirements.txt",
    "Code Citations.html": "docs", # Assumed rename and location
    "External Tools Setup GuideKaleidoscope.md": "docs", # Assumed rename and location
    "External Tools Setup Guide.md": "docs",
    "Kaleidoscope AI.md": "docs",

    # --- Files to IGNORE (set value to None) ---
    "file_rename_mapping.log": None,
    "import_analysis.json": None, # Will be regenerated if needed
    "GDCREDZ.txt": None, # Ignore sensitive data file
    "super_node_dna.json": None,
    "membrane_results.json": None,
    # Ignore Untitled files explicitly unless you rename them first
    "Untitled-1.py": None, "Untitled-2.py": None, "Untitled-3.py": None,
    "Untitled-7.py": None, "Untitled-8.py": None, "Untitled-10.py": None,
    "Untitled-11.py": None, "Untitled-12.py": None, "Untitled-13.py": None,
    "Untitled-14.py": None, "Untitled-15.py": None, "Untitled-17.py": None,
    "Untitled-18.py": None,
    # Ignore other miscellaneous/unclear files
    "configjson.md": None, "kaleidoscope_web.md": None, "__init__.md": None,
    "requirements.md": None, "sys.md": None, "advanced-quantum-cube.html": None,
    "create_templates.html": None, "indexhtml.html": None, "mimicked_filesc.md": None,
    "mimicked_files.js": None, "novelanomolydetection.md": None,
    "result[\"target_language\"] = task.py": None, "visualization.html": None,
    "'exe', 'dll', 'so', 'dylib', 'bin', # Bi.md": None, # Ignore this malformed name
    "Multi-stage build for Kaleidoscope AIdockerfile.md": None,
    "unified_quantum_kaleidoscope.py": None, #Likely combined into others
    "unified_llm.py": None, #Likely combined into others
    ".unified_quantum_kaleidoscope.md":None,

}

# Files/Dirs to KEEP in the original directory (e.g., setup scripts)
KEEP_IN_SOURCE = [
    "1_file_renamer.py",
    "2_directory_organizer.py", # This script itself (will be skipped anyway)
    "3_ollama_integration.py",
    "4_fill_missing_modules.py",
    "5_project_organizer_final.py", # This new script
    "file_rename_mapping.log",
    ".git", # Don't move git directory
    "quantum_kaleidoscope", # Don't try to move the target dir into itself
    # Add any other specific files/dirs to keep in the original location
]

# --- END ADAPTATION SECTION ---

def create_project_structure(project_base_path: Path):
    """Create the project directory structure."""
    if project_base_path.exists() and any(project_base_path.iterdir()):
         logger.warning(f"Project directory '{project_base_path}' already exists and is not empty. Files might be overwritten or skipped.")
    else:
        project_base_path.mkdir(exist_ok=True) # Create if not exists
        logger.info(f"Created/Verified project directory: {project_base_path}")

    # Create subdirectories and __init__.py files
    for directory, create_init in DIRECTORIES.items():
        # Handle nested paths like 'web/static'
        dir_path = project_base_path.joinpath(*directory.split('/'))
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            if create_init:
                init_file = dir_path / '__init__.py'
                if not init_file.exists():
                    init_file.touch()
                    logger.debug(f"Created __init__.py in: {dir_path}")
        except Exception as e:
            logger.error(f"Failed to create directory or __init__.py for {dir_path}: {e}")
    logger.info("Project directory structure created/verified.")

def organize_files(source_dir: Path, project_base_path: Path):
    """Move files from source_dir to the project_base_path structure."""
    moved_files_count = 0
    skipped_files = []
    processed_sources = set()

    logger.info(f"Scanning source directory: {source_dir}")

    # Iterate only through items directly in the source_dir first
    for item_path in source_dir.iterdir():
        if item_path.is_dir():
            # Skip the target directory itself and .git
            if item_path.name == PROJECT_DIR_NAME or item_path.name == ".git":
                processed_sources.add(item_path)
                continue
            # If you have other directories in the root you want to handle, add logic here
            # Otherwise, they will be ignored by this simple iteration.
            # For a full recursive move, you'd need os.walk or Path.rglob
            # but that's risky if the structure is messy.
            logger.warning(f"Skipping subdirectory in source: '{item_path.name}'. Manual review needed.")
            processed_sources.add(item_path)
            continue

        if not item_path.is_file():
            continue

        file_name = item_path.name

        # Skip files designated to be kept in the source directory
        if file_name in KEEP_IN_SOURCE:
             logger.info(f"Keeping file in source directory: '{file_name}'")
             processed_sources.add(item_path)
             continue

        target_rel_dir = FILE_MAPPINGS.get(file_name) # Use get for safer lookup

        if target_rel_dir is None:
            logger.warning(f"No explicit mapping for '{file_name}'. Skipping.")
            skipped_files.append(file_name)
            processed_sources.add(item_path)
            continue

        # Handle root mapping vs subdirectory mapping
        if target_rel_dir == "./":
            target_path = project_base_path / file_name
        else:
            target_path = project_base_path / target_rel_dir / file_name

        # Move the file
        try:
            # Ensure the target subdirectory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # ** Using MOVE **
            logger.debug(f"Attempting to move '{item_path}' to '{target_path}'")
            shutil.move(str(item_path), str(target_path))
            # *****************

            logger.info(f"Moved '{file_name}' to '{target_path.relative_to(project_base_path.parent)}'")
            moved_files_count += 1
            processed_sources.add(item_path) # Mark original as processed (it's gone)
            # No need to add target_path to processed_sources as we don't iterate into it

        except FileNotFoundError:
             logger.error(f"Source file not found (programmer error?): {item_path}")
        except Exception as e:
             logger.error(f"Error moving '{file_name}' to '{target_path}': {e}")
             skipped_files.append(file_name) # Add to skipped if move fails
             processed_sources.add(item_path) # Mark original as processed but failed


    logger.info(f"Organization attempt finished. Moved {moved_files_count} files.")
    if skipped_files:
        logger.warning("The following files were skipped or could not be moved:")
        for fname in skipped_files:
            logger.warning(f"  - {fname}")

def main():
    """Main function to organize files."""
    logger.info("Starting final file organization process...")
    current_dir = Path.cwd()
    project_target_path = current_dir / PROJECT_DIR_NAME

    # 1. Create/Verify the target project structure
    create_project_structure(project_target_path)

    # 2. Organize files from the current directory into the new structure
    # This will MOVE files based on FILE_MAPPINGS
    organize_files(current_dir, project_target_path)

    logger.info("-" * 60)
    logger.info(f"File organization complete. Organized project is in '{project_target_path}'")
    logger.warning("Original setup scripts and any unmapped/skipped files remain in the source directory: '%s'", current_dir)
    logger.warning("Please review the structure in '%s' and manually handle any remaining/skipped files.", PROJECT_DIR_NAME)
    logger.info("NEXT STEPS:")
    logger.info(f"1. Navigate into the new directory: cd {PROJECT_DIR_NAME}")
    logger.info("2. Run script 3 (python ../3_ollama_integration.py) to set up LLM files.")
    logger.info("3. Run script 4 (python ../4_fill_missing_modules.py) to create placeholder core modules.")
    logger.info("4. Review the 'requirements.txt' file and install dependencies (`pip install -r requirements.txt`).")
    logger.info("5. Begin integrating the actual AI logic into the Python modules.")
    logger.info("6. Manually clean up the original directory once satisfied.")

if __name__ == "__main__":
    main()
