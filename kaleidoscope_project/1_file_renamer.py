#!/usr/bin/env python3
# 1_file_renamer.py - Renames .txt files to appropriate types

import os
import re
import logging
import shutil
from pathlib import Path # Use pathlib for better path handling

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- ADAPT THIS SECTION ---

# Specific file mappings (Review and update!)
# Maps original .txt filename to the desired NEW filename (including extension)
FILE_MAPPINGS = {
    # Examples - ADD YOUR SPECIFIC MAPPINGS HERE
    "quantum_kaleidoscope_core.txt": "core.py",
    "quantum_kaleidoscope_cli.txt": "cli.py",
    "quantum_kaleidoscope_visualizer.txt": "visualizer.py",
    "advanced_quantum_cubehtml.txt": "quantum_cube.html", # Corrected typo
    "info1.txt": "cube_theory.md",
    "info2.txt": "advanced_algorithms.py",
    "info3.txt": "system_analysis.py",
    "Nodes_1.txt": "node_types.py",
    "quantum-pimd.txt": "quantum_pimd.py", # Example: Decide extension
    "quantum-drug-discovery-gui.txt": "quantum_drug_discovery_gui.tsx", # Example: Decide extension based on content
    "chatbot-integration-continued.txt": "chatbot_integration_notes.md", # Example
    "aws-cloudformation.txt": "cloudformation_template.yml", # Example
    "complete-deployment.txt": "deployment_steps.md", # Example
    "github-cicd.txt": "github_cicd.yml", # Example
    "monitoring-rules.txt": "monitoring_rules.yml", # Example
    "terraform.txt": "infrastructure.tf", # Example
    "YAML.txt": "configuration.yaml", # Example
    # Add ALL other specific .txt files that need exact renaming
}

# File type patterns (Review and adjust if needed)
# These regex patterns try to guess the file type based on content
PYTHON_PATTERN = re.compile(r'(?:^|\n)(?:import\s+|from\s+\w+\s+import|def\s+\w+\s*\(|class\s+\w+\s*[(:])|\bif\s+__name__\s*==\s*[\'"]__main__[\'"]')
HTML_PATTERN = re.compile(r'<!DOCTYPE html>|<html|<head|<body|\s*<div', re.IGNORECASE)
JS_PATTERN = re.compile(r'(?:function\s+\w+\s*\(|const\s+\w+\s*=|let\s+\w+\s*=|document\.get|\=\>\s*\{)') # Added =>
YAML_PATTERN = re.compile(r'^\w+:\s+.*$|^-+\s+\w+:') # Basic YAML detection
JSON_PATTERN = re.compile(r'^\s*\{[\s\S]*\}\s*$|^\s*\[[\s\S]*\]\s*$') # Basic JSON detection
TERRAFORM_PATTERN = re.compile(r'^\s*(?:provider|resource|variable|output|terraform)\s+[\'"]\w+[\'"]\s+\{')
SHELL_PATTERN = re.compile(r'^#!/bin/(?:bash|sh|zsh|ksh)')

# Default extension for non-code .txt files (Change if needed)
DEFAULT_EXTENSION = '.md'

# --- END ADAPTATION SECTION ---

def identify_file_type(file_path):
    """Determine the appropriate file extension based on content."""
    try:
        # Prioritize checking if it looks like JSON/YAML first as they might contain code keywords
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
             content_start = f.read(50) # Check start for JSON/YAML structure
        if JSON_PATTERN.match(content_start.strip()):
            return '.json'
        if YAML_PATTERN.search(content_start):
             return '.yml'

        # Read more content for code detection
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(5000)

        if PYTHON_PATTERN.search(content):
            return '.py'
        elif HTML_PATTERN.search(content):
            return '.html'
        elif JS_PATTERN.search(content):
            return '.js'
        elif TERRAFORM_PATTERN.search(content):
            return '.tf'
        elif SHELL_PATTERN.search(content):
            return '.sh'
        else:
            return DEFAULT_EXTENSION
    except Exception as e:
        logger.error(f"Error reading or identifying type for {file_path}: {e}")
        return None

def rename_file(file_path: Path): # Use Path object
    """Rename a file based on its content type or predefined mapping."""
    file_name = file_path.name
    dir_path = file_path.parent # Use parent attribute

    # 1. Check predefined mappings first
    if file_name in FILE_MAPPINGS:
        new_name = FILE_MAPPINGS[file_name]
        new_path = dir_path / new_name # Use / operator for paths
        if new_path == file_path: # Avoid renaming to itself
            return file_path, file_path
        try:
            # ** Using MOVE **
            shutil.move(str(file_path), str(new_path)) # Moves the file (replaces original)
            # *****************
            logger.info(f"Renamed/Moved via mapping: '{file_name}' -> '{new_name}'")
            return file_path, new_path # Return both old and new path
        except Exception as e:
            logger.error(f"Error renaming/moving '{file_name}' via mapping: {e}")
            return file_path, None # Indicate failure but return original

    # 2. If no mapping, try content-based renaming only for .txt files
    if file_name.endswith('.txt'):
        file_type = identify_file_type(file_path)
        if file_type:
            base_name = file_path.stem # Get name without extension
            new_name = f"{base_name}{file_type}"

            # Prevent renaming to itself or if already correct
            if new_name == file_name:
                return file_path, file_path # No change needed

            new_path = dir_path / new_name
            try:
                # ** Using MOVE **
                shutil.move(str(file_path), str(new_path))
                # *****************
                logger.info(f"Renamed/Moved based on content: '{file_name}' -> '{new_name}'")
                return file_path, new_path
            except Exception as e:
                logger.error(f"Error renaming/moving '{file_name}' based on content: {e}")
                return file_path, None # Indicate failure

    # If it's not a .txt or couldn't be typed/mapped, return original path
    return file_path, file_path

def process_directory(directory):
    """Process all files in a directory."""
    rename_map = {} # Store old_path -> new_path mapping
    processed_files = set()

    # Use pathlib for robust iteration
    base_path = Path(directory).resolve() # Get absolute path

    # Iterate using rglob to find all files recursively
    for file_path in base_path.rglob('*'):
        if file_path.is_file() and file_path not in processed_files:
            # Skip files within known non-code directories early
            if any(part in file_path.parts for part in ['node_modules', '.git', '__pycache__']):
                continue

            original_path_str = str(file_path)
            original_path_obj, new_path_obj = rename_file(file_path) # Rename happens here

            if new_path_obj and str(new_path_obj) != original_path_str:
                rename_map[original_path_str] = str(new_path_obj)
                processed_files.add(new_path_obj) # Track processed files by their *new* path
            processed_files.add(original_path_obj) # Add original path too, in case no rename occured


    return rename_map

def main():
    """Main function to process the current directory."""
    logger.info("Starting file renaming process...")
    current_dir = os.getcwd()

    rename_map = process_directory(current_dir)

    logger.info(f"Processed files. {len(rename_map)} files were renamed/moved.")

    # Create a mapping file for reference
    mapping_file = Path(current_dir) / 'file_rename_mapping.log' # Changed name
    try:
        with open(mapping_file, 'w') as f:
            f.write("Original File Path -> New File Path\n")
            f.write("-" * 60 + "\n")
            if rename_map:
                for old_path, new_path in rename_map.items():
                    f.write(f"{old_path} -> {new_path}\n")
            else:
                f.write("No files were renamed/moved.\n")
        logger.info(f"File rename mapping saved to: {mapping_file}")
    except Exception as e:
        logger.error(f"Error writing mapping file: {e}")

    logger.info("File renaming script finished.")

if __name__ == "__main__":
    main()
