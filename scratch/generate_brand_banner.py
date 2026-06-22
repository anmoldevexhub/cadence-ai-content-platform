import os
import base64

logo_path = r"c:\Users\user\Downloads\Cadence\Cadence\frontend\media\devexhub_logo.png"
logo_base64 = ""

if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode("utf-8")
else:
    print("Warning: Logo not found at path")

svg_content = f"""<svg width="1200" height="800" viewBox="0 0 1200 800" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- Drop Shadow for Cards and Buttons -->
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="8" stdDeviation="6" flood-color="#001826" flood-opacity="0.25"/>
    </filter>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="15" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>

    <!-- Brand Gradients -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#001320" />
      <stop offset="50%" stop-color="#00263e" />
      <stop offset="100%" stop-color="#00537e" />
    </linearGradient>
    <linearGradient id="brandGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#00537e" />
      <stop offset="100%" stop-color="#008bf2" />
    </linearGradient>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.07" />
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0.02" />
    </linearGradient>

    <!-- Grid Pattern -->
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#ffffff" stroke-width="1" stroke-opacity="0.04"/>
    </pattern>
  </defs>

  <!-- Background -->
  <rect width="1200" height="800" fill="url(#bgGrad)"/>
  <rect width="1200" height="800" fill="url(#grid)"/>

  <!-- Glowing background elements on the right -->
  <circle cx="1000" cy="350" r="250" fill="#00537e" filter="url(#glow)" opacity="0.25"/>
  <circle cx="850" cy="500" r="180" fill="#008bf2" filter="url(#glow)" opacity="0.15"/>

  <!-- Abstract Tech Wave / Curved Shapes -->
  <path d="M 600 -100 Q 800 200 650 500 T 900 900" fill="none" stroke="#00537e" stroke-width="4" stroke-opacity="0.2"/>
  <path d="M 650 -100 Q 850 250 700 550 T 950 900" fill="none" stroke="#008bf2" stroke-width="2" stroke-opacity="0.15" stroke-dasharray="8,6"/>

  <!-- Left Side: Content & Typography -->
  
  <!-- Logo Section -->
  <g transform="translate(80, 60)">
    <!-- Logo image background wrapper -->
    <rect x="-12" y="-12" width="64" height="64" rx="14" fill="#ffffff" filter="url(#shadow)" opacity="0.95"/>
    <image href="data:image/png;base64,{logo_base64}" x="-6" y="-6" width="52" height="52"/>
    <text x="70" y="28" font-family="system-ui, -apple-system, sans-serif" font-size="26" font-weight="800" fill="#ffffff" letter-spacing="1">DevExHub</text>
  </g>

  <!-- Category Tag -->
  <g transform="translate(80, 200)">
    <rect x="0" y="0" rx="16" ry="16" width="160" height="32" fill="#00537e" fill-opacity="0.2" stroke="#00537e" stroke-width="2"/>
    <circle cx="18" cy="16" r="5" fill="#008bf2"/>
    <text x="32" y="21" font-family="system-ui, -apple-system, sans-serif" font-size="13" font-weight="700" fill="#ffffff" letter-spacing="1.5" text-transform="uppercase">{{category}}</text>
  </g>

  <!-- Article Title -->
  <!-- Note: We use dynamic multiple tspan elements to display the title. Since this is a template, we provide a placeholder wrapper. -->
  <g transform="translate(80, 280)">
    <text font-family="system-ui, -apple-system, sans-serif" font-size="46" font-weight="800" fill="#ffffff" line-height="1.2">
      <tspan x="0" dy="0">{{idea.title}}</tspan>
    </text>
  </g>

  <!-- Article Excerpt / Summary -->
  <g transform="translate(80, 410)">
    <text font-family="system-ui, -apple-system, sans-serif" font-size="18" font-weight="400" fill="#a0aec0">
      <tspan x="0" dy="0">{{excerpt}}</tspan>
    </text>
  </g>

  <!-- CTA Button: Read More -->
  <g transform="translate(80, 500)" filter="url(#shadow)">
    <rect x="0" y="0" width="180" height="52" rx="26" fill="#00537e"/>
    <text x="75" y="32" font-family="system-ui, -apple-system, sans-serif" font-size="15" font-weight="700" fill="#ffffff" text-anchor="middle" letter-spacing="0.5">Read More</text>
    <!-- Arrow icon -->
    <path d="M 124 26 L 134 26 M 130 21 L 135 26 L 130 31" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </g>


  <!-- Right Side: Visual Mockup (Web Dev / AI / Dashboard theme) -->
  <g transform="translate(680, 160)">
    <!-- Dashboard Glass Card Background -->
    <rect x="0" y="0" width="440" height="340" rx="20" fill="url(#cardGrad)" stroke="#ffffff" stroke-width="1.5" stroke-opacity="0.1" filter="url(#shadow)"/>
    
    <!-- Window Header -->
    <path d="M 0 20 A 20 20 0 0 1 20 0 L 420 0 A 20 20 0 0 1 440 20 L 440 40 L 0 40 Z" fill="#001826" fill-opacity="0.6"/>
    <circle cx="20" cy="20" r="6" fill="#ff5f56" />
    <circle cx="40" cy="20" r="6" fill="#ffbd2e" />
    <circle cx="60" cy="20" r="6" fill="#27c93f" />
    <text x="220" y="24" font-family="system-ui, -apple-system, sans-serif" font-size="12" font-weight="600" fill="#a0aec0" text-anchor="middle">devexhub.com | Console</text>
    
    <!-- Code / Data Visuals on Laptop Screen -->
    <g transform="translate(30, 70)">
      <!-- Line chart representing Growth / Performance -->
      <path d="M 10 180 L 70 140 L 140 160 L 210 100 L 280 120 L 350 40" fill="none" stroke="url(#brandGrad)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M 10 180 L 70 140 L 140 160 L 210 100 L 280 120 L 350 40 L 350 200 L 10 200 Z" fill="url(#brandGrad)" opacity="0.1"/>
      
      <!-- Chart Nodes -->
      <circle cx="70" cy="140" r="5" fill="#ffffff" stroke="#00537e" stroke-width="2"/>
      <circle cx="140" cy="160" r="5" fill="#ffffff" stroke="#00537e" stroke-width="2"/>
      <circle cx="210" cy="100" r="5" fill="#ffffff" stroke="#00537e" stroke-width="2"/>
      <circle cx="280" cy="120" r="5" fill="#ffffff" stroke="#00537e" stroke-width="2"/>
      <circle cx="350" cy="40" r="6" fill="#008bf2" stroke="#ffffff" stroke-width="2"/>
      
      <!-- Chart Axes -->
      <line x1="0" y1="200" x2="380" y2="200" stroke="#ffffff" stroke-opacity="0.1" stroke-width="1.5"/>
      <line x1="0" y1="20" x2="0" y2="200" stroke="#ffffff" stroke-opacity="0.1" stroke-width="1.5"/>
      
      <!-- Mini Tech Stats inside screen -->
      <rect x="10" y="10" width="100" height="50" rx="8" fill="#001826" fill-opacity="0.4" stroke="#ffffff" stroke-width="1" stroke-opacity="0.05"/>
      <text x="20" y="28" font-family="system-ui, -apple-system, sans-serif" font-size="11" font-weight="600" fill="#a0aec0">VISITORS</text>
      <text x="20" y="44" font-family="system-ui, -apple-system, sans-serif" font-size="15" font-weight="800" fill="#ffffff">+142%</text>

      <rect x="125" y="10" width="100" height="50" rx="8" fill="#001826" fill-opacity="0.4" stroke="#ffffff" stroke-width="1" stroke-opacity="0.05"/>
      <text x="135" y="28" font-family="system-ui, -apple-system, sans-serif" font-size="11" font-weight="600" fill="#a0aec0">CONVERSION</text>
      <text x="135" y="44" font-family="system-ui, -apple-system, sans-serif" font-size="15" font-weight="800" fill="#008bf2">4.82%</text>
    </g>
  </g>

  <!-- Floating Badges to represent Web Dev / AI / Marketing / Tech -->
  <g transform="translate(620, 310)" filter="url(#shadow)">
    <rect x="0" y="0" width="130" height="42" rx="10" fill="#001826" fill-opacity="0.9" stroke="#00537e" stroke-width="1.5"/>
    <circle cx="20" cy="21" r="6" fill="#00537e"/>
    <text x="36" y="26" font-family="system-ui, -apple-system, sans-serif" font-size="13" font-weight="700" fill="#ffffff">Web Dev</text>
  </g>

  <g transform="translate(850, 110)" filter="url(#shadow)">
    <rect x="0" y="0" width="100" height="42" rx="10" fill="#001826" fill-opacity="0.9" stroke="#008bf2" stroke-width="1.5"/>
    <circle cx="20" cy="21" r="6" fill="#008bf2"/>
    <text x="36" y="26" font-family="system-ui, -apple-system, sans-serif" font-size="13" font-weight="700" fill="#ffffff">AI / ML</text>
  </g>

  <g transform="translate(1030, 270)" filter="url(#shadow)">
    <rect x="0" y="0" width="120" height="42" rx="10" fill="#001826" fill-opacity="0.9" stroke="#22c55e" stroke-width="1.5"/>
    <circle cx="20" cy="21" r="6" fill="#22c55e"/>
    <text x="36" y="26" font-family="system-ui, -apple-system, sans-serif" font-size="13" font-weight="700" fill="#ffffff">Marketing</text>
  </g>

  <g transform="translate(980, 460)" filter="url(#shadow)">
    <rect x="0" y="0" width="110" height="42" rx="10" fill="#001826" fill-opacity="0.9" stroke="#eab308" stroke-width="1.5"/>
    <circle cx="20" cy="21" r="6" fill="#eab308"/>
    <text x="36" y="26" font-family="system-ui, -apple-system, sans-serif" font-size="13" font-weight="700" fill="#ffffff">Business</text>
  </g>


  <!-- Footer bar -->
  <rect x="0" y="730" width="1200" height="70" fill="#00121e" fill-opacity="0.9"/>
  <line x1="0" y1="730" x2="1200" y2="730" stroke="#00537e" stroke-width="1.5" stroke-opacity="0.5"/>
  
  <g transform="translate(0, 730)">
    <!-- Email Contact -->
    <g transform="translate(150, 35)">
      <!-- Mail Icon -->
      <circle cx="-16" cy="-5" r="13" fill="#00537e" fill-opacity="0.3" stroke="#00537e" stroke-width="1"/>
      <rect x="-22" y="-10" width="12" height="9" rx="1.5" fill="none" stroke="#ffffff" stroke-width="1.5"/>
      <path d="M -22 -9 L -16 -5 L -10 -9" fill="none" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round"/>
      <text x="5" y="0" fill="#cbd5e1" font-family="system-ui, -apple-system, sans-serif" font-size="14" font-weight="600">info@devexhub.com</text>
    </g>

    <!-- Phone Contact -->
    <g transform="translate(500, 35)">
      <!-- Phone Icon -->
      <circle cx="-16" cy="-5" r="13" fill="#00537e" fill-opacity="0.3" stroke="#00537e" stroke-width="1"/>
      <path d="M -19.5 -8.5 C -19.5 -5 -15 -0.5 -11.5 -0.5 C -10 -0.5 -9.5 -2 -10.5 -3 L -12 -4.5 C -12.5 -5 -13.5 -5 -14 -4.5 L -15 -3.5 C -16 -4 -17 -5 -17.5 -6 L -16.5 -7 C -16 -7.5 -16 -8.5 -16.5 -9 L -18 -10.5 C -19 -11.5 -19.5 -10 -19.5 -8.5 Z" fill="#ffffff"/>
      <text x="5" y="0" fill="#cbd5e1" font-family="system-ui, -apple-system, sans-serif" font-size="14" font-weight="600">+91 98759 05952</text>
    </g>

    <!-- Website Link -->
    <g transform="translate(870, 35)">
      <!-- Globe Icon -->
      <circle cx="-16" cy="-5" r="13" fill="#00537e" fill-opacity="0.3" stroke="#00537e" stroke-width="1"/>
      <circle cx="-16" cy="-5" r="7" fill="none" stroke="#ffffff" stroke-width="1.5"/>
      <path d="M -23 -5 L -9 -5 M -16 -12 L -16 2 M -20 -8 Q -16 -5 -12 -8 M -20 -2 Q -16 -5 -12 -2" fill="none" stroke="#ffffff" stroke-width="1.2"/>
      <text x="5" y="0" fill="#cbd5e1" font-family="system-ui, -apple-system, sans-serif" font-size="14" font-weight="600">devexhub.com</text>
    </g>
  </g>
</svg>
"""

# Save to scratch_svgs
svgs_dir = r"c:\Users\user\Downloads\Cadence\Cadence\scratch_svgs"
os.makedirs(svgs_dir, exist_ok=True)
svg_path = os.path.join(svgs_dir, "devexhub_brand_banner.svg")

with open(svg_path, "w", encoding="utf-8") as f:
    f.write(svg_content)

print(f"SVG written to: {svg_path}")

# Also save to frontend/media
frontend_media_dir = r"c:\Users\user\Downloads\Cadence\Cadence\frontend\media"
os.makedirs(frontend_media_dir, exist_ok=True)
svg_path_frontend = os.path.join(frontend_media_dir, "devexhub_brand_banner.svg")

with open(svg_path_frontend, "w", encoding="utf-8") as f:
    f.write(svg_content)

print(f"SVG written to: {svg_path_frontend}")
