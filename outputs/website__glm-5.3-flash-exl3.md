# website / glm-5.3-flash-exl3

- decode 42.1 tok/s
- TTFT 0.42s
- wall 24.7s
- 1024 tokens generated

---

# Product Landing Page — "Lumina Desk Lamp"

A complete, dependency-free landing page. Save as `index.html` and open in a browser.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Lumina — the adaptive desk lamp that follows your day.">
<title>Lumina — Adaptive Desk Lamp</title>
<style>
  /* ============ Design tokens ============ */
  :root {
    --bg: #faf9f7;
    --surface: #ffffff;
    --text: #1a1a1a;
    --text-muted: #5c5c5c;
    --accent: #e8642c;
    --accent-hover: #d4531d;
    --border: #e2e0dc;
    --shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
    --radius: 12px;
    --nav-height: 64px;
  }

  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #121212;
      --surface: #1e1e1e;
      --text: #f0efed;
      --text-muted: #a3a3a3;
      --accent: #ff7a42;
      --accent-hover: #ff8f5e;
      --border: #333;
      --shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
    }
  }

  /* ============ Reset & base ============ */
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  html { scroll-behavior: smooth; }

  body {
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }

  img { max-width: 100%; display: block; }

  h1, h2, h3 { line-height: 1.2; letter-spacing: -0.02em; }

  a { color: var(--accent); }

  :focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 3px;
    border-radius: 4px;
  }

  .container {
    width: min(1100px, 100% - 2.5rem);
    margin-inline: auto;
  }

  /* ============ Sticky nav ============ */
  .site-header {
    position: sticky;
    top: 0;
    z-index: 100;
    background: color-mix(in srgb, var(--bg) 85%, transparent);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid transparent;
    transition: border-color 0.3s, box-shadow 0.3s;
  }

  .site-header.is-scrolled {
    border-bottom-color: var(--border);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  }

  .nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: var(--nav-height);
  }

  .brand {
    font-weight: 700;
    font-size: 1.25rem;
    color: var(--text);
    text-decoration: none;
  }

  .brand span { color: var(--accent); }

  .nav-links {
    display: flex;
    gap: 1.75rem;
    list-style: none;
  }

  .nav-links a {
    color: var(--text-muted);
    text-decoration: none;
    font-size: 0.95rem;
    font-weight: 500;
    transition: color 0.2s;
  }

  .nav-links a:hover { color: var(--text); }

  .nav-cta {
    background: var(--accent);
    color: #fff !important;
    padding: 0.5rem 1.1rem;
    border-radius: 999px;
    transition: background 0.2s;
  }

  .nav-cta:hover { background: var(--accent-hover); }

  /* Mobile nav toggle */
  .nav-toggle {
    display: none;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0.5rem;
  }

  .nav-toggle svg { width:
