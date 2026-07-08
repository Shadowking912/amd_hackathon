#!/usr/bin/env python3
"""
CaptionChameleon - Cover SVG Generator
Creates a professional 16:9 cover image with 4 chameleons
"""

from pathlib import Path

def generate_cover_svg(output_path):
    """Generate professional 16:9 cover image"""
    svg_content = '''<svg width="1920" height="1080" viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg">
  <!-- Gradient Background -->
  <defs>
    <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0066cc;stop-opacity:1" />
      <stop offset="50%" style="stop-color:#9333ea;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#00ff88;stop-opacity:1" />
    </linearGradient>
    
    <linearGradient id="titleGradient" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#ffffff;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#00ff88;stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Background -->
  <rect width="1920" height="1080" fill="url(#bgGradient)"/>
  
  <!-- Chameleon 1 - Formal (Blue) - Top Left -->
  <circle cx="380" cy="300" r="120" fill="#0066cc" opacity="0.3"/>
  <ellipse cx="380" cy="300" rx="80" ry="100" fill="#0066cc"/>
  <!-- Head -->
  <circle cx="380" cy="220" r="50" fill="#0066cc"/>
  <!-- Eyes -->
  <circle cx="365" cy="210" r="8" fill="#ffffff"/>
  <circle cx="395" cy="210" r="8" fill="#ffffff"/>
  <!-- Tail -->
  <path d="M 420 350 Q 500 380 480 450" stroke="#0066cc" stroke-width="30" fill="none" stroke-linecap="round"/>
  <!-- Label -->
  <text x="380" y="460" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff" text-anchor="middle">FORMAL</text>
  
  <!-- Chameleon 2 - Sarcastic (Purple) - Top Right -->
  <circle cx="1540" cy="300" r="120" fill="#9333ea" opacity="0.3"/>
  <ellipse cx="1540" cy="300" rx="80" ry="100" fill="#9333ea"/>
  <!-- Head -->
  <circle cx="1540" cy="220" r="50" fill="#9333ea"/>
  <!-- Eyes -->
  <circle cx="1525" cy="210" r="8" fill="#ffffff"/>
  <circle cx="1555" cy="210" r="8" fill="#ffffff"/>
  <!-- Tail -->
  <path d="M 1500 350 Q 1420 380 1440 450" stroke="#9333ea" stroke-width="30" fill="none" stroke-linecap="round"/>
  <!-- Label -->
  <text x="1540" y="460" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff" text-anchor="middle">SARCASTIC</text>
  
  <!-- Chameleon 3 - Tech (Green) - Bottom Left -->
  <circle cx="380" cy="850" r="120" fill="#00ff88" opacity="0.3"/>
  <ellipse cx="380" cy="850" rx="80" ry="100" fill="#00ff88"/>
  <!-- Head -->
  <circle cx="380" cy="770" r="50" fill="#00ff88"/>
  <!-- Eyes -->
  <circle cx="365" cy="760" r="8" fill="#0f172a"/>
  <circle cx="395" cy="760" r="8" fill="#0f172a"/>
  <!-- Tail -->
  <path d="M 420 900 Q 500 930 480 1000" stroke="#00ff88" stroke-width="30" fill="none" stroke-linecap="round"/>
  <!-- Label -->
  <text x="380" y="1010" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff" text-anchor="middle">TECH</text>
  
  <!-- Chameleon 4 - Casual (Orange) - Bottom Right -->
  <circle cx="1540" cy="850" r="120" fill="#ff8c00" opacity="0.3"/>
  <ellipse cx="1540" cy="850" rx="80" ry="100" fill="#ff8c00"/>
  <!-- Head -->
  <circle cx="1540" cy="770" r="50" fill="#ff8c00"/>
  <!-- Eyes -->
  <circle cx="1525" cy="760" r="8" fill="#ffffff"/>
  <circle cx="1555" cy="760" r="8" fill="#ffffff"/>
  <!-- Tail -->
  <path d="M 1500 900 Q 1420 930 1440 1000" stroke="#ff8c00" stroke-width="30" fill="none" stroke-linecap="round"/>
  <!-- Label -->
  <text x="1540" y="1010" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#ffffff" text-anchor="middle">CASUAL</text>
  
  <!-- Title -->
  <text x="960" y="600" font-family="Arial, sans-serif" font-size="96" font-weight="300" fill="url(#titleGradient)" text-anchor="middle">CaptionChameleon</text>
  
  <!-- Subtitle -->
  <text x="960" y="680" font-family="Arial, sans-serif" font-size="48" font-weight="300" fill="#ffffff" text-anchor="middle" opacity="0.9">Adaptive Multi-Style Video Captioning</text>
</svg>'''
    
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg_content)
    
    file_size_kb = output.stat().st_size / 1024
    print(f"✓ Cover SVG generated successfully!")
    print(f"  File: {output_path}")
    print(f"  Size: {file_size_kb:.1f} KB")
    print(f"  Format: 16:9 (1920x1080)")

if __name__ == "__main__":
    output_path = Path(__file__).parent.parent / "submission" / "cover.svg"
    generate_cover_svg(str(output_path))
