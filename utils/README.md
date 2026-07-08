# CaptionChameleon Utils

Submission materials generation utilities for CaptionChameleon.

## Contents

### Core Generators

**`build_submission.py`** - Master orchestration script
- Runs all generators in the correct sequence
- Creates the complete submission package
- Reports build status and file sizes

**`generate_video.py`** - Intro video generator
- Creates 10-second MP4 video (1920×1080, 30fps)
- 4 scenes: title, styles showcase, features, call-to-action
- Output: `submission/CaptionChameleon_Intro.mp4` (~2.1 MB)

**`generate_presentation_pdf.py`** - HTML to PDF converter
- Converts presentation template to PDF
- Handles 16:9 aspect ratio formatting
- Output: `submission/CaptionChameleon_Presentation.pdf` (~25 KB)

**`generate_cover.py`** - Professional cover SVG generator
- Creates 16:9 cover image with chameleons
- 4 style representations (Formal, Sarcastic, Tech, Casual)
- Output: `submission/cover.svg` (~5.7 KB)

### Templates

**`presentation_template.html`** - Google Slides-style presentation
- 9 professional slides
- Full project narrative and demo details
- Ready for PDF export via `generate_presentation_pdf.py`
- Can also be viewed/printed directly from browser

## Usage

### Build All Submission Materials (Recommended)

```bash
cd /home/abhi/amd_hackathon
python3 utils/build_submission.py
```

This single command:
1. ✓ Generates cover SVG (16:9, 1920×1080)
2. ✓ Creates intro video (10s, 1920×1080, 30fps)
3. ✓ Converts presentation to PDF (16:9, 9 slides)
4. ✓ Copies HTML presentation template
5. ✓ Organizes all files in `submission/` folder
6. ✓ Reports file sizes and build status

### Individual Generators

Generate specific materials:

```bash
# Generate video only
python3 utils/generate_video.py

# Generate PDF from presentation
python3 utils/generate_presentation_pdf.py

# Generate cover SVG
python3 utils/generate_cover.py
```

## Output Structure

All submission materials are organized in the `submission/` folder:

```
submission/
├── CaptionChameleon_Presentation.pdf    # Main PDF (9 slides, 16:9)
├── presentation_pdf.html               # Interactive presentation (browser/PDF)
├── CaptionChameleon_Intro.mp4         # Intro video (10s, 1920×1080)
└── cover.svg                           # Cover image (16:9)
```

## Dependencies

The utils require these Python packages:

- **opencv-python** - Video generation
- **weasyprint** - HTML to PDF conversion
- **numpy** - Image processing

These are included in `requirements.txt`. Install with:

```bash
pip install -r requirements.txt
```

`weasyprint` will be auto-installed by `generate_presentation_pdf.py` if missing.

## Customization

### Modify Video Content

Edit `generate_video.py` to change:
- Scene text and timing
- Colors and gradients
- Video duration (default: 10 seconds)
- Output resolution (default: 1920×1080)

### Modify Presentation

Edit `presentation_template.html` to customize:
- Slide content and text
- Colors and gradients
- Fonts and styling
- Number of slides

### Modify Cover Image

Edit `generate_cover.py` to change:
- Chameleon positions and colors
- Text and title size
- Gradient colors
- SVG dimensions

## Troubleshooting

**Video generation fails:**
- Ensure OpenCV is installed: `pip install opencv-python`
- Check disk space in `submission/` folder

**PDF generation fails:**
- Install weasyprint: `pip install weasyprint`
- On Linux, may require system dependencies: `apt-get install libffi-dev libcairo2`

**Files not found:**
- Ensure working directory is the project root: `cd /home/abhi/amd_hackathon`
- Check that `utils/` folder exists

## File Sizes Reference

Typical output sizes:

- `cover.svg`: ~5.7 KB
- `CaptionChameleon_Presentation.pdf`: ~25 KB
- `CaptionChameleon_Intro.mp4`: ~2.1 MB
- `presentation_pdf.html`: ~14 KB
- **Total submission**: ~2.2 MB

## Performance

Typical generation times:
- Cover SVG: <100 ms
- Video (10s, 30fps, 1920×1080): ~3-5 seconds
- Presentation PDF: ~2-3 seconds
- **Total build**: ~5-8 seconds

## Integration with CI/CD

Example GitHub Actions workflow step:

```yaml
- name: Generate submission materials
  run: python3 utils/build_submission.py
  
- name: Upload to releases
  uses: softprops/action-gh-release@v1
  with:
    files: submission/*
```

## License

These utilities are part of CaptionChameleon and follow the same license as the main project.
