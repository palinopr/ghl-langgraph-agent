#!/usr/bin/env python3
"""
Cleanup Dead Code Script
Backs up everything, then removes all non-production files
"""
import os
import shutil
import datetime
import sys
from pathlib import Path
from typing import List, Set, Tuple, Dict
import json

# PRODUCTION FILES TO KEEP
PRODUCTION_FILES = {
    # Entry points
    "app.py",
    "app/api/webhook_simple.py",
    "app/workflow.py",
    
    # Core workflow
    "app/workflow_modernized.py",
    
    # Active agents
    "app/agents/receptionist_memory_aware.py",
    "app/agents/supervisor_official.py",
    "app/agents/maria_memory_aware.py",
    "app/agents/carlos_agent_v2_fixed.py",
    "app/agents/sofia_agent_v2_fixed.py",
    "app/agents/responder_streaming.py",
    
    # Intelligence
    "app/intelligence/analyzer.py",
    "app/intelligence/fuzzy_extractor.py",  # Used by analyzer
    
    # Tools
    "app/tools/agent_tools_modernized.py",
    "app/tools/ghl_client.py",  # Used by tools
    "app/tools/calendar_slots.py",  # Used by tools
    "app/tools/webhook_processor.py",  # Used by webhook
    "app/tools/webhook_enricher.py",  # May be used
    "app/tools/conversation_loader.py",  # May be used
    "app/tools/ghl_streaming.py",  # Used by responder
    
    # State
    "app/state/conversation_state.py",
    "app/state/memory_aware_state.py",  # May be used
    
    # Utils (check imports to determine which are needed)
    "app/utils/simple_logger.py",
    "app/utils/model_factory.py",
    "app/utils/state_utils.py",
    "app/utils/memory_manager.py",
    "app/utils/context_filter.py",
    "app/utils/conversation_enforcer.py",
    "app/utils/tracing.py",
    
    # Debug middleware (keep for production monitoring)
    "app/debug/trace_middleware.py",
    
    # API
    "app/api/debug_endpoints.py",
    
    # Config
    "app/config.py",
    "app/__init__.py",
    "app/agents/__init__.py",
    "app/tools/__init__.py",
    "app/state/__init__.py",
    "app/utils/__init__.py",
    "app/intelligence/__init__.py",
    "app/api/__init__.py",
    "app/debug/__init__.py",
    
    # Root files to keep
    "requirements.txt",
    "langgraph.json",
    ".env",
    ".env.example",
    "README.md",
    "Makefile",
    ".gitignore",
    ".githooks/pre-push",
    "validate_workflow.py",
    "pyproject.toml",
    
    # Documentation
    "PRODUCTION_EXECUTION_FLOW.md",
    "CLAUDE.md",
}

# Patterns to always delete
DELETE_PATTERNS = [
    "test_*.py",
    "analyze_*.py",
    "debug_*.py",
    "backup_*",
    "*_test.py",
    "fetch_*.py",
    "check_*.py",
    "setup_*.py",
    "send_*.py",
    "monitor_*.py",
    "fix_*.py",
    "update_*.py",
    "access_*.py",
    "find_*.py",
    "create_*.py",
    "run_*.py",
    "quick_*.py",
    "interactive_*.py",
    "deployment_*.py",
    "trace_*.py",
    "*.pyc",
    "__pycache__",
    ".pytest_cache",
    ".coverage",
    "*.log"
]

# Directories to check for cleanup
CLEANUP_DIRS = [
    "app/agents",
    "app/tools", 
    "app/state",
    "app/utils",
    "app/intelligence",
    "app/api",
    "app/debug",
    "app",
    "."
]

def get_file_size(file_path: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except:
        return 0

def format_size(size_bytes: int) -> str:
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def should_delete_file(file_path: str) -> bool:
    """Check if file should be deleted"""
    # Keep production files
    if file_path in PRODUCTION_FILES:
        return False
    
    # Keep directories
    if os.path.isdir(file_path):
        return False
    
    filename = os.path.basename(file_path)
    
    # Check delete patterns
    for pattern in DELETE_PATTERNS:
        if pattern.startswith("*") and pattern.endswith("*"):
            if pattern[1:-1] in filename:
                return True
        elif pattern.startswith("*"):
            if filename.endswith(pattern[1:]):
                return True
        elif pattern.endswith("*"):
            if filename.startswith(pattern[:-1]):
                return True
        else:
            if pattern == filename:
                return True
    
    # Check specific file types to delete
    if file_path.endswith(('.md', '.txt', '.json')) and file_path not in PRODUCTION_FILES:
        # Keep only specific documentation
        if filename in ['README.md', 'requirements.txt', 'langgraph.json', 'pyproject.toml']:
            return False
        if 'PRODUCTION' in filename or 'CLAUDE' in filename:
            return False
        return True
    
    # Delete all non-production Python files
    if file_path.endswith('.py') and file_path not in PRODUCTION_FILES:
        return True
    
    # Delete shell scripts except Makefile
    if file_path.endswith('.sh') and filename != 'Makefile':
        return True
    
    return False

def create_backup(backup_dir: str) -> bool:
    """Create full backup of current directory"""
    print(f"\n📦 Creating backup in {backup_dir}...")
    try:
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
        
        # Copy everything except existing backups and git
        for item in os.listdir('.'):
            if item.startswith('backup_') or item == '.git' or item == backup_dir or item.startswith('venv') or item == 'node_modules':
                continue
            
            src = os.path.join('.', item)
            dst = os.path.join(backup_dir, item)
            
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        
        print(f"✅ Backup created successfully!")
        return True
    except Exception as e:
        print(f"❌ Backup failed: {str(e)}")
        return False

def analyze_codebase() -> Tuple[List[str], List[str], int, int]:
    """Analyze what files to keep and delete"""
    files_to_keep = []
    files_to_delete = []
    total_size_before = 0
    total_size_after = 0
    
    for cleanup_dir in CLEANUP_DIRS:
        if not os.path.exists(cleanup_dir):
            continue
            
        for root, dirs, files in os.walk(cleanup_dir):
            # Skip .git, backup directories, venv, and node_modules
            if '.git' in root or 'backup_' in root or 'venv' in root or 'node_modules' in root:
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                # Normalize path for comparison
                normalized_path = file_path.replace('\\', '/').lstrip('./')
                file_size = get_file_size(file_path)
                total_size_before += file_size
                
                if should_delete_file(normalized_path):
                    files_to_delete.append((normalized_path, file_size))
                else:
                    files_to_keep.append((normalized_path, file_size))
                    total_size_after += file_size
    
    return files_to_keep, files_to_delete, total_size_before, total_size_after

def group_files_by_type(files: List[Tuple[str, int]]) -> Dict[str, List[Tuple[str, int]]]:
    """Group files by their type/category"""
    groups = {
        'workflows': [],
        'agents': [],
        'tools': [],
        'state': [],
        'utils': [],
        'intelligence': [],
        'tests': [],
        'scripts': [],
        'docs': [],
        'debug': [],
        'other': []
    }
    
    for file_path, size in files:
        if 'workflow' in file_path:
            groups['workflows'].append((file_path, size))
        elif 'app/agents/' in file_path:
            groups['agents'].append((file_path, size))
        elif 'app/tools/' in file_path:
            groups['tools'].append((file_path, size))
        elif 'app/state/' in file_path:
            groups['state'].append((file_path, size))
        elif 'app/utils/' in file_path:
            groups['utils'].append((file_path, size))
        elif 'app/intelligence/' in file_path:
            groups['intelligence'].append((file_path, size))
        elif 'test' in file_path or 'Test' in file_path:
            groups['tests'].append((file_path, size))
        elif file_path.endswith('.py') and '/' not in file_path:
            groups['scripts'].append((file_path, size))
        elif file_path.endswith(('.md', '.txt', '.json')):
            groups['docs'].append((file_path, size))
        elif 'debug' in file_path or 'Debug' in file_path:
            groups['debug'].append((file_path, size))
        else:
            groups['other'].append((file_path, size))
    
    # Remove empty groups
    return {k: v for k, v in groups.items() if v}

def create_manifest(files_to_keep, files_to_delete, total_size_before, total_size_after):
    """Create cleanup manifest"""
    manifest = []
    manifest.append("# Cleanup Manifest\n")
    manifest.append(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Summary
    manifest.append("## Summary\n")
    manifest.append(f"- **Files before**: {len(files_to_keep) + len(files_to_delete)}")
    manifest.append(f"- **Files after**: {len(files_to_keep)}")
    manifest.append(f"- **Files deleted**: {len(files_to_delete)}")
    manifest.append(f"- **Size before**: {format_size(total_size_before)}")
    manifest.append(f"- **Size after**: {format_size(total_size_after)}")
    manifest.append(f"- **Size saved**: {format_size(total_size_before - total_size_after)}")
    manifest.append(f"- **Reduction**: {((total_size_before - total_size_after) / total_size_before * 100):.1f}%\n")
    
    # Files kept
    manifest.append("## Files Kept (Production)\n")
    kept_groups = group_files_by_type(files_to_keep)
    for group, files in sorted(kept_groups.items()):
        manifest.append(f"### {group.title()} ({len(files)} files)\n")
        for file_path, size in sorted(files):
            manifest.append(f"- `{file_path}` ({format_size(size)})")
        manifest.append("")
    
    # Files deleted
    manifest.append("\n## Files Deleted\n")
    deleted_groups = group_files_by_type(files_to_delete)
    for group, files in sorted(deleted_groups.items()):
        manifest.append(f"### {group.title()} ({len(files)} files)\n")
        for file_path, size in sorted(files)[:10]:  # Show first 10
            manifest.append(f"- `{file_path}` ({format_size(size)})")
        if len(files) > 10:
            manifest.append(f"- ... and {len(files) - 10} more")
        manifest.append("")
    
    return "\n".join(manifest)

def delete_files(files_to_delete):
    """Delete the specified files"""
    deleted_count = 0
    for file_path, _ in files_to_delete:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_count += 1
        except Exception as e:
            print(f"⚠️  Could not delete {file_path}: {str(e)}")
    
    # Clean up empty directories
    for cleanup_dir in CLEANUP_DIRS:
        if os.path.exists(cleanup_dir):
            for root, dirs, files in os.walk(cleanup_dir, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):  # Empty directory
                            os.rmdir(dir_path)
                    except:
                        pass
    
    return deleted_count

def main():
    """Main cleanup function"""
    print("🧹 LangGraph Codebase Cleanup Tool")
    print("=" * 50)
    
    # Check for auto mode
    auto_mode = "--auto" in sys.argv
    
    # Create backup directory name
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup_full_{timestamp}"
    
    # Analyze what to keep and delete
    print("\n🔍 Analyzing codebase...")
    files_to_keep, files_to_delete, total_size_before, total_size_after = analyze_codebase()
    
    # Show summary
    print(f"\n📊 Analysis Results:")
    print(f"  - Files to keep: {len(files_to_keep)}")
    print(f"  - Files to delete: {len(files_to_delete)}")
    print(f"  - Current size: {format_size(total_size_before)}")
    print(f"  - Size after cleanup: {format_size(total_size_after)}")
    print(f"  - Space to be freed: {format_size(total_size_before - total_size_after)}")
    
    # Ask for confirmation
    print(f"\n⚠️  This will:")
    print(f"  1. Create a full backup in {backup_dir}/")
    print(f"  2. Delete {len(files_to_delete)} files")
    print(f"  3. Keep only {len(files_to_keep)} production files")
    
    if auto_mode:
        print("\n🤖 Auto mode enabled - proceeding automatically...")
        response = 'yes'
    else:
        response = input("\n❓ Do you want to proceed? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("\n❌ Cleanup cancelled.")
        return
    
    # Create backup
    if not create_backup(backup_dir):
        print("\n❌ Backup failed. Cleanup cancelled for safety.")
        return
    
    # Create manifest before deletion
    print("\n📝 Creating manifest...")
    manifest = create_manifest(files_to_keep, files_to_delete, total_size_before, total_size_after)
    
    # Perform cleanup
    print(f"\n🗑️  Deleting {len(files_to_delete)} files...")
    deleted_count = delete_files(files_to_delete)
    print(f"✅ Deleted {deleted_count} files")
    
    # Save manifest
    with open("CLEANUP_MANIFEST.md", "w") as f:
        f.write(manifest)
    print("\n📄 Manifest saved to CLEANUP_MANIFEST.md")
    
    print("\n✨ Cleanup complete!")
    print(f"   Backup saved in: {backup_dir}/")
    print(f"   Files kept: {len(files_to_keep)}")
    print(f"   Files deleted: {deleted_count}")

if __name__ == "__main__":
    main()