#!/usr/bin/env python3
"""
CaptionChameleon - Submission Materials Builder
Orchestrates generation of all presentation, video, and branding assets
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_step(step_num, text):
    """Print a numbered step"""
    print(f"\n[{step_num}] {text}")

def run_python_script(script_path, description):
    """Run a Python script and report results"""
    print(f"    Running: {script_path.name}")
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            check=True
        )
        # Print output
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                print(f"    {line}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    ✗ Error: {e.stderr}")
        return False
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False

def build_submission():
    """Build all submission materials"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    submission_dir = project_root / "submission"
    
    print_header("CaptionChameleon - Submission Builder")
    print(f"Project Root: {project_root}")
    print(f"Output: {submission_dir}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ensure submission directory exists
    submission_dir.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # Step 1: Generate Cover SVG
    print_step(1, "Generating Cover Image (SVG)")
    cover_script = script_dir / "generate_cover.py"
    results['cover'] = run_python_script(cover_script, "Cover generation")
    
    # Step 2: Generate Video
    print_step(2, "Generating Intro Video (MP4)")
    video_script = script_dir / "generate_video.py"
    # Change to submission dir for video output
    original_cwd = Path.cwd()
    import os
    os.chdir(submission_dir)
    results['video'] = run_python_script(video_script, "Video generation")
    os.chdir(original_cwd)
    
    # Step 3: Generate Presentation PDF
    print_step(3, "Generating Presentation PDF")
    pdf_script = script_dir / "generate_presentation_pdf.py"
    results['pdf'] = run_python_script(pdf_script, "PDF generation")
    
    # Step 4: Copy HTML presentation template
    print_step(4, "Copying Presentation Template (HTML)")
    try:
        html_template = script_dir / "presentation_template.html"
        html_output = submission_dir / "presentation_pdf.html"
        import shutil
        shutil.copy2(html_template, html_output)
        print(f"    ✓ Copied to {html_output.name}")
        results['html'] = True
    except Exception as e:
        print(f"    ✗ Error: {e}")
        results['html'] = False
    
    # Summary
    print_header("Build Summary")
    tasks = [
        ("Cover SVG", results.get('cover', False)),
        ("Intro Video", results.get('video', False)),
        ("Presentation PDF", results.get('pdf', False)),
        ("Presentation HTML", results.get('html', False)),
    ]
    
    success_count = sum(1 for _, success in tasks if success)
    total_count = len(tasks)
    
    for task_name, success in tasks:
        status = "✓" if success else "✗"
        print(f"{status} {task_name}")
    
    # List submission files
    print_step("Files", "Submission contents")
    if submission_dir.exists():
        files = sorted(submission_dir.glob("*"))
        total_size = 0
        for file in files:
            size_mb = file.stat().st_size / (1024 * 1024)
            total_size += size_mb
            print(f"  {file.name:<40} {size_mb:>8.2f} MB")
        print(f"  {'TOTAL':<40} {total_size:>8.2f} MB")
    
    # Final status
    print_header("Complete")
    print(f"\n✓ Build completed: {success_count}/{total_count} tasks successful")
    print(f"Output directory: {submission_dir}/")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return success_count == total_count

def main():
    """Main entry point"""
    try:
        success = build_submission()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✗ Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
