import os
import shutil
import argparse
import logging
import json
from pathlib import Path
import datetime
import re  # Added for config.txt parsing

# --- Configuration ---
# NOTE: Consider moving FILE_MAPPING and DIRECTORIES to an external JSON/YAML
#       for easier modification without changing the script code.

# Desired structure mapping: {current_file: (target_sub_directory, new_name)}
FILE_MAPPING = {
    # Current quatumunravel files
    "quantum_kaleidoscope_core.py": ("core", "kaleidoscope_core.py"),
    "core.py": ("core", "core_utils.py"),
    "AI_Core.py": ("core", "ai_core.py"),
    "AI_Core.cpython-312.py": (None, None),
    "llm_integration.py": ("llm", "llm_integration.py"),
    "GPTProcessor.py": ("llm", "gpt_processor.py"),
    "quantum-server.py": ("quantum", "quantum_server.py"),
    "quantum-client.py": ("quantum", "quantum_client.py"),
    "quantum-sync-protocol.py": ("quantum", "quantum_sync_protocol.py"),
    "quantum_visualization.py": ("visualization", "visualizer.py"),
    "quantum_visualizer_new.py": ("visualization", "visualizer_new.py"),
    "visualization_integration.py": ("visualization", "visualization_integration.py"),
    "visualizer.py": ("visualization", "base_visualizer.py"),
    "visualization-renderer.py": ("visualization", "visualization_renderer.py"),
    "hypercube-viz.py": ("visualization", "hypercube_viz.py"),
    "base_node.py": ("nodes", "base_node.py"),
    "BaseNode.py": ("nodes", "base_node_alt.py"),
    "BaseNode.cpython-312.py": (None, None),
    "CapabilityNode.py": ("nodes", "capability_node.py"),
    "TextNode.py": ("nodes", "text_node.py"),
    "text_node.py": ("nodes", "text_node_alt.py"),
    "VisualNode.py": ("nodes", "visual_node.py"),
    "NodeManager.py": ("nodes", "node_manager.py"),
    "GrowthLaws.py": ("nodes", "growth_laws.py"),
    "supernode_core.py": ("supernode", "supernode_core.py"),
    "supernode-manager.py": ("supernode", "supernode_manager.py"),
    "supernode-processor.py": ("supernode", "supernode_processor.py"),
    "SeedManager.py": ("state", "seed_manager.py"),
    "PerspectiveManager.py": ("state", "perspective_manager.py"),
    "MirroredNetwork.py": ("state", "mirrored_network.py"),
    "PatternRecognition.py": ("patterns", "pattern_recognition.py"),
    "class EmergentPatternDetector.py": ("patterns", "emergent_pattern_detector.py"),
    "app.py": ("web", "app.py"),
    "quantum-kaleidoscope-frontend.py": ("web", "frontend.py"),
    "kaleidoscope-api-server.py": ("web", "api_server.py"),
    "kaleidoscope_auth.py": ("auth", "auth_manager.py"),
    "error_handler.py": ("error", "error_handler.py"),
    "execution-sandbox-system.py": ("sandbox", "execution_sandbox.py"),
    "core-reconstruction.py": ("reconstruction", "code_generator.py"),
    "kaleidoscope-complete.py": ("", "kaleidoscope.py"),
    "unified_quantum_kaleidoscope.py": ("", "kaleidoscope_alt.py"),
    "kaleidoscope-integration.py": ("core", "integration.py"),
    "quantum_integration_manager.py": ("quantum", "integration_manager.py"),
    "quantum-integrator.py": ("quantum", "quantum_integrator.py"),
    "kaleidoscope_web.py": ("web", "web_interface.py"),
    "quantum-kaleidoscope-middleware.py": ("web", "middleware.py"),
    "qsin-network-visualizer.py": ("visualization", "qsin_visualizer.py"),
    "quantum-swarm-network.py": ("quantum", "swarm_network.py"),
    "hyperdimensional-processing.py": ("core", "hyperdimensional_processing.py"),
    "deployment-script.py": ("", "setup.sh"),
    "deployment-script.py.bak": (None, None),
    "deployment-fix.py": (None, None),
    "deployment-fix.py.bak": (None, None),
    "engine.py": ("core", "engine.py"),
    "enhanced-quantum-kaleidoscope.py": (None, None),
    "enhanced_quantum_kaleidoscope.py": (None, None),
    "kaleidoscope_ai_platform.py": (None, None),
    "quantum_kaleidoscope_launcher.py": (None, None),
    "advanced-quantum-cube.html": ("web/templates", "quantum_cube.html"),
    "index.html": ("web/templates", "index_alt.html"),
    "quantum_memory.db": (None, None),
    "integrated_system": (None, None),
    "venv": (None, None),
    # Uploaded files
    "config.txt": ("", "config.json"),
    "create_templates.txt": ("reconstruction", "template_generator.py"),
    "<!DOCTYPE html>.txt": ("web/templates", "index.html"),
    "'exe', 'dll', 'so', 'dylib', 'bin', # Bi.txt": ("sandbox", "binary_extensions.txt"),
    "__init__.txt": ("utils", "__init__.py"),
    "kaleidoscope.txt": ("", "README.md"),
    "kaleidoscope_auth.txt": ("auth", "auth_manager.py"),
    "kaleidoscope_core.txt": ("core", "kaleidoscope_core_from_txt.py"),
    "kaleidoscope_web.txt": ("web", "web_routes.py"),
    "mimicked_files.txt": ("mimicry", "mimic_engine.py"),
    "ollama_client.txt": ("llm", "ollama_client.py"),
    "test_ollama_client.txt": ("llm", "test_ollama_client.py"),
    "result[\"target_language\"] = task.txt": ("_unclassified", "result_task_snippet.txt"),
    "deploy.txt": ("", "deploy_notes.txt"),
    "mimicked_filesc.txt": ("_unclassified", "mimicked_filesc_snippet.txt"),
    "finish_kaleidoscope_setup.sh": ("", "finish_kaleidoscope_setup.sh"),
    "configjson.txt": ("", "config_alt.json"),
    "requirements.txt": ("", "requirements.txt"),
    "setup.txt": ("", "setup_notes.txt"),
    "run.sh": ("", "run.sh"),
    "sys.txt": ("_unclassified", "sys_snippet.txt"),
    "setup.sh": ("", "setup_alt.sh"),
    "Untitled-1.txt": ("_unclassified", "Untitled-1.txt"),
    "Untitled-2.txt": ("_unclassified", "Untitled-2.txt"),
    "Untitled-3.txt": ("_unclassified", "Untitled-3.txt"),
    "Untitled-7.txt": ("_unclassified", "Untitled-7.txt"),
    "Untitled-8.txt": ("_unclassified", "Untitled-8.txt"),
    "Untitled-10.txt": ("_unclassified", "Untitled-10.txt"),
    "Untitled-11.txt": ("_unclassified", "Untitled-11.txt"),
    "Untitled-12.txt": ("_unclassified", "Untitled-12.txt"),
    "Untitled-13.txt": ("_unclassified", "Untitled-13.txt"),
    "Untitled-14.txt": ("_unclassified", "Untitled-14.txt"),
    "Untitled-15.txt": ("_unclassified", "Untitled-15.txt"),
    "Untitled-17.txt": ("_unclassified", "Untitled-17.txt"),
    "Untitled-18.txt": ("_unclassified", "Untitled-18.txt"),
}

# Directories to create
DIRECTORIES = sorted(list(set([
    "core", "llm", "utils", "sandbox", "analysis", "reconstruction",
    "mimicry", "interfaces", "quantum", "visualization", "nodes",
    "supernode", "state", "patterns", "auth", "error", "web",
    "web/templates", "web/static", "_unclassified"
] + [d[0] for d in FILE_MAPPING.values() if d[0] is not None])))

# --- Stats ---
stats = {
    "copied": 0,
    "skipped_missing": 0,
    "skipped_no_mapping": 0,
    "skipped_conflict": 0,
    "skipped_invalid": 0,  # New stat for invalid content
    "overwritten": 0,
    "backed_up": 0,
    "unmapped_found": 0,
    "dirs_created": 0,
    "inits_created": 0,
    "errors": 0,
}

# --- Setup Logging ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('reorganizer')
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# --- Functions ---
def create_directory_structure(dest_dir_base, dry_run=False):
    """Create the kaleidoscope_project directory structure."""
    logger.info(f"Creating directory structure under: {dest_dir_base}")
    created_count = 0
    init_count = 0
    try:
        if not dry_run:
            os.makedirs(dest_dir_base, exist_ok=True)
        logger.info(f"{'(Dry Run) Would create' if dry_run else 'Created'}: {dest_dir_base}")
        created_count += 1

        for directory in DIRECTORIES:
            dir_path = Path(dest_dir_base) / directory
            if not dry_run:
                os.makedirs(dir_path, exist_ok=True)
            logger.info(f"{'(Dry Run) Would create' if dry_run else 'Created'}: {dir_path}")
            created_count += 1

            if directory and not directory.startswith("_"):
                init_path = dir_path / "__init__.py"
                if not init_path.exists():
                    if not dry_run:
                        try:
                            with open(init_path, "w") as f:
                                f.write(f"# Initialize the {directory} module\n")
                            logger.info(f"Created: {init_path}")
                            init_count += 1
                        except OSError as e:
                            logger.error(f"Failed to create {init_path}: {e}")
                            stats["errors"] += 1
                    else:
                        logger.info(f"(Dry Run) Would create: {init_path}")
                        init_count += 1
                else:
                    logger.debug(f"Skipping init creation, already exists: {init_path}")

    except OSError as e:
        logger.error(f"Failed to create base directory {dest_dir_base}: {e}")
        stats["errors"] += 1
        return False

    stats["dirs_created"] = created_count
    stats["inits_created"] = init_count
    return True

def handle_conflict(src_path, dest_path, conflict_mode, dry_run=False):
    """Handles file conflicts based on the specified mode."""
    if conflict_mode == 'skip':
        logger.warning(f"Skipping copy: Target already exists (conflict mode 'skip'): {dest_path}")
        stats["skipped_conflict"] += 1
        return False
    elif conflict_mode == 'backup':
        backup_name = f"{dest_path}.bak_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        logger.warning(f"Target exists. Backing up existing file to: {backup_name}")
        if not dry_run:
            try:
                shutil.move(dest_path, backup_name)
                logger.info(f"Moved existing {dest_path} to {backup_name}")
                stats["backed_up"] += 1
            except OSError as e:
                logger.error(f"Failed to backup {dest_path} to {backup_name}: {e}")
                stats["errors"] += 1
                return False
        else:
            logger.info(f"(Dry Run) Would move existing {dest_path} to {backup_name}")
            stats["backed_up"] += 1
        return True
    elif conflict_mode == 'overwrite':
        logger.warning(f"Target exists. Overwriting (conflict mode 'overwrite'): {dest_path}")
        stats["overwritten"] += 1
        return True
    else:
        logger.error(f"Invalid conflict mode: {conflict_mode}. Skipping.")
        stats["errors"] += 1
        return False

def validate_python_content(content, src_path):
    """Validate if content is valid Python syntax."""
    try:
        compile(content, str(src_path), 'exec')
        return True, None
    except SyntaxError as e:
        return False, f"Invalid Python syntax: {e}"
    except Exception as e:
        return False, f"Unexpected error during validation: {e}"

def convert_to_json(content, src_path):
    """Attempt to parse or convert content to JSON."""
    # First, try parsing as JSON
    try:
        json.loads(content)
        return True, content, None
    except json.JSONDecodeError:
        pass

    # If not JSON, attempt conversion from key-value format
    config_dict = {}
    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Match key=value or key: value formats
        match = re.match(r'^([^=:\s]+)\s*[=:]\s*(.+)$', line)
        if match:
            key, value = match.groups()
            # Attempt to convert value to appropriate type
            value = value.strip()
            try:
                # Try as JSON value (handles numbers, bool, null)
                value = json.loads(value)
            except json.JSONDecodeError:
                # Keep as string if not JSON-compatible
                pass
            config_dict[key.strip()] = value
        else:
            return False, None, f"Invalid config format in line: {line}"

    if not config_dict:
        return False, None, "No valid key-value pairs found"

    try:
        json_content = json.dumps(config_dict, indent=4)
        return True, json_content, None
    except Exception as e:
        return False, None, f"Failed to serialize to JSON: {e}"

def copy_and_rename_files(src_dir_base, dest_dir_base, conflict_mode='overwrite', dry_run=False):
    """Copy files from source to destination, renaming and handling conflicts."""
    logger.info("--- Starting File Copy and Rename Process ---")
    processed_sources = set()

    for src_file_rel, mapping in FILE_MAPPING.items():
        processed_sources.add(src_file_rel)
        src_path = Path(src_dir_base) / src_file_rel
        target_dir_rel, new_name = mapping

        # 1. Check if source file exists
        if not src_path.exists():
            logger.warning(f"Skipping: Source file not found: {src_path}")
            stats["skipped_missing"] += 1
            continue

        # 2. Check if mapping is defined
        if target_dir_rel is None or new_name is None:
            logger.info(f"Skipping: '{src_file_rel}' is marked for skipping in mapping.")
            stats["skipped_no_mapping"] += 1
            continue

        # 3. Determine destination path
        dest_subdir = Path(dest_dir_base) / target_dir_rel if target_dir_rel else Path(dest_dir_base)
        dest_path = dest_subdir / new_name

        # Ensure destination subdirectory exists
        if not dest_subdir.exists() and not dry_run:
            try:
                os.makedirs(dest_subdir, exist_ok=True)
                logger.info(f"Created intermediate directory: {dest_subdir}")
                stats["dirs_created"] += 1
            except OSError as e:
                logger.error(f"Failed to create required destination directory {dest_subdir}: {e}")
                stats["errors"] += 1
                continue

        # 4. Handle potential conflicts at destination
        proceed_copy = True
        if dest_path.exists():
            proceed_copy = handle_conflict(src_path, dest_path, conflict_mode, dry_run)

        # 5. Validate/Convert content if necessary
        if proceed_copy:
            # Read source content for validation/conversion
            try:
                with open(src_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Failed to read {src_path}: {e}")
                stats["errors"] += 1
                continue

            # Python validation for .txt to .py
            if new_name.endswith('.py') and src_path.suffix == '.txt':
                logger.info(f"Validating Python syntax for {src_path} -> {dest_path}")
                is_valid, error_msg = validate_python_content(content, src_path)
                if not is_valid:
                    logger.error(f"Skipping copy due to invalid Python content in {src_path}: {error_msg}")
                    stats["skipped_invalid"] += 1
                    continue
                logger.info(f"Python content validated successfully for {src_path}")

            # JSON validation/conversion for config.txt to config.json
            elif new_name == 'config.json' and src_path.name in ['config.txt', 'configjson.txt']:
                logger.info(f"Validating/Converting JSON for {src_path} -> {dest_path}")
                is_valid, json_content, error_msg = convert_to_json(content, src_path)
                if not is_valid:
                    logger.error(f"Skipping copy due to invalid JSON content in {src_path}: {error_msg}")
                    stats["skipped_invalid"] += 1
                    continue
                logger.info(f"JSON content validated/converted successfully for {src_path}")
                # Use json_content for writing
                if not dry_run:
                    try:
                        with open(dest_path, 'w', encoding='utf-8') as f:
                            f.write(json_content)
                        logger.info(f"Copied and converted: {src_path} -> {dest_path}")
                        stats["copied"] += 1
                    except OSError as e:
                        logger.error(f"Error writing JSON to {dest_path}: {e}")
                        stats["errors"] += 1
                    continue  # Skip default copy since we handled it
                else:
                    logger.info(f"(Dry Run) Would write JSON to {dest_path}")
                    stats["copied"] += 1
                    continue

            # Default copy for other files
            logger.info(f"{'(Dry Run) Would copy' if dry_run else 'Copying'}: {src_path} -> {dest_path}")
            if not dry_run:
                try:
                    shutil.copy2(src_path, dest_path)
                    stats["copied"] += 1
                except OSError as e:
                    logger.error(f"Error copying {src_path} to {dest_path}: {e}")
                    stats["errors"] += 1
                except shutil.SameFileError:
                    logger.warning(f"Skipping copy: Source and destination are the same file: {src_path}")
                    stats["skipped_conflict"] += 1
            else:
                stats["copied"] += 1

    logger.info("--- Finished Processing Mapped Files ---")
    return processed_sources

def handle_unmapped_files(src_dir_base, dest_dir_base, processed_sources, copy_unmapped, dry_run=False):
    """Checks for files in source not in mapping and optionally copies them."""
    logger.info("--- Checking for Unmapped Files ---")
    unmapped_dest_dir = Path(dest_dir_base) / "_unclassified"

    for item in Path(src_dir_base).iterdir():
        item_rel_path_str = str(item.relative_to(src_dir_base))
        if item_rel_path_str not in processed_sources:
            stats["unmapped_found"] += 1
            logger.warning(f"Unmapped item found: {item.name}")
            if item.is_file() and copy_unmapped:
                dest_path = unmapped_dest_dir / item.name
                logger.info(f"{'(Dry Run) Would copy unmapped file' if dry_run else 'Copying unmapped file'} to _unclassified: {item.name} -> {dest_path}")

                if not dry_run:
                    if not unmapped_dest_dir.exists():
                        try:
                            os.makedirs(unmapped_dest_dir, exist_ok=True)
                            logger.info(f"Created _unclassified directory: {unmapped_dest_dir}")
                            stats["dirs_created"] += 1
                        except OSError as e:
                            logger.error(f"Failed to create _unclassified directory: {e}. Skipping copy of {item.name}")
                            stats["errors"] += 1
                            continue

                    try:
                        shutil.copy2(item, dest_path)
                        stats["copied"] += 1
                    except OSError as e:
                        logger.error(f"Error copying unmapped file {item.name} to {dest_path}: {e}")
                        stats["errors"] += 1
                    except shutil.SameFileError:
                        logger.warning(f"Skipping copy of unmapped file: Source and destination are the same file: {item.name}")
            elif item.is_dir():
                logger.warning(f"Skipping unmapped item (is directory): {item.name}")
            elif not copy_unmapped:
                logger.warning(f"Skipping unmapped file (copy_unmapped=False): {item.name}")

# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="Reorganize project files into a structured directory.")
    parser.add_argument("source_dir", help="Path to the source directory (e.g., quatumunravel)")
    parser.add_argument("dest_dir", help="Path to the destination directory (e.g., kaleidoscope_project)")
    parser.add_argument("--conflict", choices=['overwrite', 'skip', 'backup'], default='overwrite',
                        help="How to handle existing files in the destination (default: overwrite)")
    parser.add_argument("--copy-unmapped", action="store_true",
                        help="Copy files found in source but not in the mapping to an '_unclassified' folder in destination.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate the process without actually copying or creating files.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose logging (DEBUG level).")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.info("Verbose logging enabled.")

    src_dir = Path(args.source_dir).resolve()
    dest_dir = Path(args.dest_dir).resolve()

    logger.info(f"Starting reorganization...")
    logger.info(f"Source:      {src_dir}")
    logger.info(f"Destination: {dest_dir}")
    logger.info(f"Conflict Mode: {args.conflict}")
    logger.info(f"Copy Unmapped: {args.copy_unmapped}")
    logger.info(f"Dry Run:     {args.dry_run}")

    if not src_dir.is_dir():
        logger.error(f"Source directory does not exist or is not a directory: {src_dir}")
        return 1

    if dest_dir.exists() and not dest_dir.is_dir():
        logger.error(f"Destination path exists but is not a directory: {dest_dir}")
        return 1

    if str(dest_dir).startswith(str(src_dir)):
        logger.error("Destination directory cannot be inside the source directory.")
        return 1

    # 1. Create Structure
    if not create_directory_structure(dest_dir, args.dry_run):
        logger.error("Failed to create directory structure. Aborting.")
        return 1

    # 2. Copy Mapped Files
    processed_sources = copy_and_rename_files(src_dir, dest_dir, args.conflict, args.dry_run)

    # 3. Handle Unmapped Files
    handle_unmapped_files(src_dir, dest_dir, processed_sources, args.copy_unmapped, args.dry_run)

    # 4. Print Summary Report
    logger.info("--- Reorganization Summary ---")
    logger.info(f"Directories created:     {stats['dirs_created']}")
    logger.info(f"__init__.py created:     {stats['inits_created']}")
    logger.info(f"Files copied:            {stats['copied']}")
    logger.info(f"Files overwritten:       {stats['overwritten']}")
    logger.info(f"Files backed up:         {stats['backed_up']}")
    logger.info(f"Skipped (Missing src):   {stats['skipped_missing']}")
    logger.info(f"Skipped (No mapping):    {stats['skipped_no_mapping']}")
    logger.info(f"Skipped (Conflict):      {stats['skipped_conflict']}")
    logger.info(f"Skipped (Invalid content): {stats['skipped_invalid']}")
    logger.info(f"Unmapped items found:    {stats['unmapped_found']}")
    logger.info(f"Errors encountered:      {stats['errors']}")
    logger.info("------------------------------")

    if args.dry_run:
        logger.info("Dry run complete. No actual changes were made.")
    else:
        logger.info("Reorganization process finished.")

    return 0 if stats["errors"] == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
