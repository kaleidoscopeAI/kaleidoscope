import os
import shutil
import argparse
import logging
import json
from pathlib import Path
import datetime

# --- Configuration ---
# NOTE: Consider moving FILE_MAPPING and DIRECTORIES to an external JSON/YAML
#       for easier modification without changing the script code.

# Desired structure mapping based on user's `ls kaleidoscope_project` output
FILE_MAPPING = {
    "advanced-quantum-cube.txt": ("web/templates", "advanced_quantum_cube.html"),
    "app.txt": ("web", "app.py"),
    "BaseNode.txt": ("nodes", "base_node.py"),
    "CapabilityNode.txt": ("nodes", "capability_node.py"),
    "# Code Citations.md": ("docs", "code_citations.md"),
    "configjson.txt": ("", "config.json"), # Assumes this is the primary config
    "config.txt": ("", "config_alt.json"), # Avoids conflict with configjson.txt
    "core-reconstruction.txt": ("reconstruction", "code_generator.py"),
    "create_templates.txt": ("reconstruction", "template_generator.py"),
    "deployment-script.txt": ("scripts", "deploy.sh"), # Assume shell script
    "deployment-script.txt.bak": (None, None), # Skip backup
    "deploy.txt": ("scripts", "deploy_notes.txt"), # Assume notes related to deployment
    "<!DOCTYPE html>.txt": ("web/templates", "index.html"), # Primary index
    "enhance_reorganize.py": (None, None), # Skip the script itself if run from source (should be moved out!)
    "error_handler.txt": ("error", "error_handler.py"),
    "execution-sandbox-system.txt": ("sandbox", "execution_sandbox.py"),
    "'exe', 'dll', 'so', 'dylib', 'bin', # Bi.txt": ("sandbox", "binary_extensions.txt"), # Cleaned name slightly
    "# External Tools Setup GuideKaleidoscope.md": ("docs", "external_tools_setup_kaleidoscope.md"),
    "# External Tools Setup Guide.md": ("docs", "external_tools_setup.md"),
    "finish_kaleidoscope_setup.sh": ("scripts", "finish_kaleidoscope_setup.sh"),
    "fix-script.py": (None, None), # Skip unknown script
    "GPTProcessor.txt": ("llm", "gpt_processor.py"),
    "GrowthLaws.txt": ("nodes", "growth_laws.py"),
    "index.html": ("web/templates", "index_alt.html"), # Avoid conflict with <!DOCTYPE html>.txt
    "__init__.txt": ("_unclassified", "init_original.txt"), # Avoid assuming role, let auto-init handle package markers
    "# Kaleidoscope AI.md": ("docs", "kaleidoscope_ai_readme.md"), # Main project readme perhaps
    "kaleidoscope_auth.txt": ("auth", "auth_manager.py"),
    "kaleidoscope_core.txt": ("core", "kaleidoscope_core.py"),
    "kaleidoscope-integration.txt": ("core", "integration.py"),
    "kaleidoscope.txt": ("", "README.md"), # Assume this is the main README
    "kaleidoscope_web.txt": ("web", "web_interface.py"),
    "llm_integration.txt": ("llm", "llm_integration.py"),
    "mimicked_filesc.txt": ("_unclassified", "mimicked_filesc.txt"), # Unclear snippet
    "mimicked_files.txt": ("mimicry", "mimic_engine.py"),
    "MirroredNetwork.txt": ("state", "mirrored_network.py"),
    "# Multi-stage build for Kaleidoscope AI.dockerfile": ("", "Dockerfile"), # Standard Dockerfile name
    "NodeManager.txt": ("nodes", "node_manager.py"),
    "ollama_client.txt": ("llm", "ollama_client.py"),
    "PatternRecognition.txt": ("patterns", "pattern_recognition.py"),
    "PerspectiveManager.txt": ("state", "perspective_manager.py"),
    "qsin-network-visualizer.txt": ("visualization", "qsin_visualizer.py"),
    "quantum-client.txt": ("quantum", "quantum_client.py"),
    "quantum-kaleidoscope-frontend.txt": ("web", "frontend.py"), # Assuming web frontend code
    "quantum_kaleidoscope_hub.txt": ("quantum", "quantum_hub.py"),
    "quantum_kaleidoscope_launcher.txt": ("scripts", "launcher.py"),
    "quantum-server.txt": ("quantum", "quantum_server.py"),
    "quantum-sync-protocol.txt": ("quantum", "quantum_sync_protocol.py"),
    "quantum_visualizer_new.txt": ("visualization", "visualizer_new.py"),
    "requirements.txt": ("", "requirements.txt"),
    'result["target_language"] = task.txt': ("_unclassified", 'result_task_snippet.txt'),
    "run.sh": ("scripts", "run.sh"),
    "SeedManager.txt": ("state", "seed_manager.py"),
    "setup.sh": ("scripts", "setup.sh"),
    "setup.txt": ("docs", "setup_notes.txt"), # Assume setup documentation/notes
    "supernode_core.txt": ("supernode", "supernode_core.py"),
    "supernode-manager.txt": ("supernode", "supernode_manager.py"),
    "supernode-processor.txt": ("supernode", "supernode_processor.py"),
    "sys.txt": ("_unclassified", "sys_snippet.txt"), # Unclear snippet
    "test_ollama_client.txt": ("llm", "test_ollama_client.py"), # Assumed test script
    "TextNode.txt": ("nodes", "text_node.py"),
    "unified_quantum_kaleidoscope.txt": ("core", "unified_system.py"), # Assumed core/integration logic
    "Untitled-10.txt": ("_unclassified", "Untitled-10.txt"),
    "Untitled-11.txt": ("llm", "llm_chunking_utils.py"), # Guess based on prior context
    "Untitled-12.txt": ("error", "error_handling_notes.txt"), # Guess based on prior context
    "Untitled-13.txt": ("error", "error_handler_alt.py"), # Guess based on prior context
    "Untitled-14.txt": ("core", "code_reuse_arch_notes1.txt"), # Guess based on prior context
    "Untitled-15.txt": ("core", "code_reuse_arch_notes2.txt"), # Guess based on prior context
    "Untitled-17.txt": ("sandbox", "sandbox_notes.txt"), # Guess based on prior context
    "Untitled-18.txt": ("licensing", "licensing_system.py"), # Guess based on prior context
    "Untitled-1.txt": ("_unclassified", "Untitled-1.txt"),
    "Untitled-2.txt": ("core", "ast_generation_notes.txt"), # Guess based on prior context (AST?)
    "Untitled-3.txt": ("core", "core_functionality_notes.txt"), # Guess based on prior context
    "Untitled-7.txt": ("interfaces", "chatbot_interface.py"), # Guess based on prior context
    "Untitled-8.txt": ("web", "web_interface_notes.txt"), # Guess based on prior context
    "visualization_integration.txt": ("visualization", "visualization_integration.py"),
    "visualization.txt": ("visualization", "base_visualizer.py"), # Base class or general viz?
    "visualizer.txt": ("visualization", "plotly_visualizer.py"), # Assumed plotly implementation
    "VisualNode.txt": ("nodes", "visual_node.py"),
}


# Directories to create (ensure all target_dirs from mapping are included)
# Start with a base set of expected directories
base_dirs = [
    "", # For top-level files like README.md, config.json
    "core", "llm", "utils", "sandbox", "analysis", "reconstruction",
    "mimicry", "interfaces", "quantum", "visualization", "nodes",
    "supernode", "state", "patterns", "auth", "error", "web",
    "web/templates", "web/static", "_unclassified", "docs", "scripts",
    "licensing" # Added based on Untitled-18 mapping
]
# Dynamically add any other directories mentioned in the mapping values
mapped_dirs = [d[0] for d in FILE_MAPPING.values() if d[0] is not None]
# Combine, remove duplicates, filter out empty string for root, and sort
DIRECTORIES = sorted(list(set([d for d in base_dirs + mapped_dirs if d])))


# --- Stats ---
stats = {
    "copied": 0,
    "skipped_missing": 0,
    "skipped_no_mapping": 0,
    "skipped_conflict": 0,
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
logger.setLevel(logging.INFO) # Default level

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
# Avoid adding handler if it already exists (e.g., if script is imported)
if not logger.handlers:
    logger.addHandler(console_handler)

# --- Functions ---
def create_directory_structure(dest_dir_base, dry_run=False):
    """Create the kaleidoscope_project directory structure."""
    logger.info(f"Creating directory structure under: {dest_dir_base}")
    created_count = 0
    init_count = 0
    try:
        # Create base destination directory first
        if not dry_run:
            os.makedirs(dest_dir_base, exist_ok=True)
            created_count += 1 # Count base dir if created/exists
        logger.info(f"{'(Dry Run) Would ensure exists' if dry_run else 'Ensured exists'}: {dest_dir_base}")


        for directory in DIRECTORIES:
            # Handle potential empty string for root files - no dir needed
            if not directory:
                continue
            dir_path = Path(dest_dir_base) / directory
            should_create = not dir_path.exists()

            if should_create:
                 if not dry_run:
                     os.makedirs(dir_path, exist_ok=True)
                 logger.info(f"{'(Dry Run) Would create' if dry_run else 'Created'}: {dir_path}")
                 created_count += 1
            else:
                 logger.debug(f"Directory already exists: {dir_path}")


            # Create __init__.py in each directory, except special/top level ones
            # Only create if the directory itself was newly created or already exists
            # Don't create in _unclassified, docs, scripts, templates, static etc.
            potential_package_dirs = [
                "core", "llm", "utils", "sandbox", "analysis", "reconstruction",
                "mimicry", "interfaces", "quantum", "visualization", "nodes",
                "supernode", "state", "patterns", "auth", "error", "web", "licensing"
            ]
            # Check if the *base* name of the directory is in our list of packages
            if dir_path.name in potential_package_dirs:
                init_path = dir_path / "__init__.py"
                if not init_path.exists():
                    if not dry_run:
                        try:
                            with open(init_path, "w") as f:
                                f.write(f"# Initialize the {dir_path.name} module\n")
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
        logger.error(f"Failed to create base/sub directory under {dest_dir_base}: {e}")
        stats["errors"] += 1
        return False # Indicate failure

    stats["dirs_created"] = created_count
    stats["inits_created"] = init_count
    return True # Indicate success

def handle_conflict(src_path, dest_path, conflict_mode, dry_run=False):
    """Handles file conflicts based on the specified mode."""
    if conflict_mode == 'skip':
        logger.warning(f"Skipping copy: Target already exists (conflict mode 'skip'): {dest_path}")
        stats["skipped_conflict"] += 1
        return False # Do not copy
    elif conflict_mode == 'backup':
        # Use pathlib for easier suffix manipulation
        backup_name = dest_path.with_suffix(f"{dest_path.suffix}.bak_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
        logger.warning(f"Target exists. Backing up existing file to: {backup_name}")
        if not dry_run:
            try:
                # shutil.move works across filesystems, Path.rename might not
                shutil.move(str(dest_path), str(backup_name))
                logger.info(f"Moved existing {dest_path} to {backup_name}")
                stats["backed_up"] += 1
            except OSError as e:
                logger.error(f"Failed to backup {dest_path} to {backup_name}: {e}")
                stats["errors"] += 1
                return False # Failed backup, do not proceed with copy
        else:
             logger.info(f"(Dry Run) Would move existing {dest_path} to {backup_name}")
             stats["backed_up"] += 1
        return True # Proceed with copy
    elif conflict_mode == 'overwrite':
        logger.warning(f"Target exists. Overwriting (conflict mode 'overwrite'): {dest_path}")
        stats["overwritten"] += 1
        return True # Proceed with copy
    else: # Should not happen with argparse choices
        logger.error(f"Invalid conflict mode: {conflict_mode}. Skipping.")
        stats["errors"] += 1
        return False

def copy_and_rename_files(src_dir_base, dest_dir_base, conflict_mode='overwrite', dry_run=False):
    """Copy files from source to destination, renaming and handling conflicts."""
    logger.info("--- Starting File Copy and Rename Process ---")
    processed_sources = set()

    for src_file_rel, mapping in FILE_MAPPING.items():
        processed_sources.add(src_file_rel) # Mark as processed via mapping
        src_path = Path(src_dir_base) / src_file_rel
        target_dir_rel, new_name = mapping

        # 1. Check if source file exists
        if not src_path.exists():
            # Log differently if it's the script itself (expected if moved out)
            if src_file_rel == 'enhance_reorganize.py':
                 logger.debug(f"Skipping: Script file '{src_file_rel}' not found in source (expected if moved).")
            else:
                 logger.warning(f"Skipping: Source file not found: {src_path}")
            stats["skipped_missing"] += 1
            continue

        # 2. Check if mapping is defined to skip
        if target_dir_rel is None or new_name is None:
            logger.info(f"Skipping: '{src_file_rel}' is marked for skipping in mapping (target is None).")
            stats["skipped_no_mapping"] += 1
            continue

        # 3. Determine destination path
        # Handle root directory case where target_dir_rel is ''
        dest_subdir = Path(dest_dir_base) / target_dir_rel if target_dir_rel else Path(dest_dir_base)
        dest_path = dest_subdir / new_name

        # Ensure destination subdirectory exists (should have been created)
        # Create just in case, shouldn't harm if it exists
        if not dry_run and target_dir_rel: # Only needed if target_dir_rel is not empty
             try:
                 os.makedirs(dest_subdir, exist_ok=True)
             except OSError as e:
                  logger.error(f"Failed to ensure required destination directory {dest_subdir} exists: {e}")
                  stats["errors"] += 1
                  continue # Skip this file if dir can't be made/verified


        # 4. Handle potential conflicts at destination
        proceed_copy = True
        if dest_path.exists():
            proceed_copy = handle_conflict(src_path, dest_path, conflict_mode, dry_run)

        # 5. Perform the copy if applicable
        if proceed_copy:
            # --- Optional Content Validation/Conversion Placeholder ---
            # Add checks here if needed, e.g., for .py syntax or JSON validity
            # --- End Placeholder ---

            logger.info(f"{'(Dry Run) Would copy' if dry_run else 'Copying'}: {src_path} -> {dest_path}")
            if not dry_run:
                try:
                    shutil.copy2(src_path, dest_path) # copy2 preserves metadata
                    stats["copied"] += 1
                except OSError as e:
                    logger.error(f"Error copying {src_path} to {dest_path}: {e}")
                    stats["errors"] += 1
                except shutil.SameFileError:
                     logger.warning(f"Skipping copy: Source and destination are the same file: {src_path}")
                     stats["skipped_conflict"] +=1
            else:
                 stats["copied"] += 1 # Count intention in dry run

    logger.info("--- Finished Processing Mapped Files ---")
    return processed_sources

def handle_unmapped_files(src_dir_base, dest_dir_base, processed_sources, copy_unmapped, dry_run=False):
    """Checks for files in source not in mapping and optionally copies them."""
    logger.info("--- Checking for Unmapped Files ---")
    unmapped_dest_dir = Path(dest_dir_base) / "_unclassified"
    items_in_source = 0
    found_unmapped = 0

    for item in Path(src_dir_base).iterdir():
        items_in_source += 1
        # Use Path object's name for comparison, easier than relative string paths here
        item_name = item.name
        if item_name not in processed_sources:
            found_unmapped +=1
            logger.warning(f"Unmapped item found: {item_name}")

            if item.is_file():
                if copy_unmapped:
                    dest_path = unmapped_dest_dir / item.name
                    logger.info(f"{'(Dry Run) Would copy unmapped file' if dry_run else 'Copying unmapped file'} to _unclassified: {item.name} -> {dest_path}")

                    if not dry_run:
                        # Ensure _unclassified dir exists
                        if not unmapped_dest_dir.exists():
                            try:
                               os.makedirs(unmapped_dest_dir, exist_ok=True)
                               logger.info(f"Created _unclassified directory: {unmapped_dest_dir}")
                               stats["dirs_created"] +=1
                            except OSError as e:
                               logger.error(f"Failed to create _unclassified directory: {e}. Skipping copy of {item.name}")
                               stats["errors"] += 1
                               continue # Skip this file

                        # Copy the file
                        try:
                            shutil.copy2(item, dest_path)
                            stats["copied"] += 1 # Count as copied
                        except OSError as e:
                            logger.error(f"Error copying unmapped file {item.name} to {dest_path}: {e}")
                            stats["errors"] += 1
                        except shutil.SameFileError:
                            logger.warning(f"Skipping copy of unmapped file: Source and destination are the same file: {item.name}")
                else:
                     logger.warning(f"Skipping unmapped file (copy_unmapped=False): {item.name}")

            elif item.is_dir():
                 logger.warning(f"Skipping unmapped item (is directory): {item.name}")
            else:
                 logger.warning(f"Skipping unmapped item (not file or directory): {item.name}")

    stats["unmapped_found"] = found_unmapped
    logger.info(f"Checked {items_in_source} items in source, found {found_unmapped} unmapped items.")


# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="Reorganize project files into a structured directory.")
    parser.add_argument("source_dir", help="Path to the source directory (e.g., kaleidoscope_project)")
    parser.add_argument("dest_dir", help="Path to the destination directory (e.g., kaleidoscope_project_organized)")
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
        # Set level on the root logger if no specific handler level is set
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
             handler.setLevel(logging.DEBUG) # Ensure handlers also process DEBUG
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

    # Prevent running if destination is inside source
    try:
        if dest_dir.samefile(src_dir):
             logger.error("Destination directory cannot be the same as the source directory.")
             return 1
        # Check if dest is inside src (covers more cases than simple string startswith)
        if src_dir in dest_dir.parents:
             logger.error("Destination directory cannot be inside the source directory.")
             return 1
    except FileNotFoundError:
         # If dest_dir doesn't exist yet, samefile check fails, which is fine
         pass
    except Exception as e:
         logger.error(f"Error comparing source and destination paths: {e}")
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
    logger.info(f"Directories created/ensured: {stats['dirs_created']}")
    logger.info(f"__init__.py created:         {stats['inits_created']}")
    logger.info(f"Files copied:                {stats['copied']}")
    logger.info(f"Files overwritten:           {stats['overwritten']}")
    logger.info(f"Files backed up:             {stats['backed_up']}")
    logger.info(f"Skipped (Missing src):       {stats['skipped_missing']}")
    logger.info(f"Skipped (Marked in map):     {stats['skipped_no_mapping']}")
    logger.info(f"Skipped (Conflict):          {stats['skipped_conflict']}")
    logger.info(f"Unmapped items found:        {stats['unmapped_found']}")
    logger.info(f"Errors encountered:          {stats['errors']}")
    logger.info("------------------------------")

    if args.dry_run:
        logger.info("Dry run complete. No actual changes were made.")
    else:
         logger.info("Reorganization process finished.")
         if stats['unmapped_found'] > 0 and not args.copy_unmapped:
              logger.warning("There were unmapped files that were not copied. Consider using --copy-unmapped or updating the FILE_MAPPING.")
         if stats['errors'] > 0:
              logger.error("Errors were encountered during the process. Please review the log.")

    return 0 if stats["errors"] == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
