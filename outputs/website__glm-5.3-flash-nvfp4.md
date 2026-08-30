# website / glm-5.3-flash-nvfp4

- decode 37.2 tok/s
- TTFT 0.26s
- wall 27.8s
- 1024 tokens generated

---

# Product Landing Page — "Lumina Desk Lamp"

A complete, dependency-free landing page. Semantic HTML5, CSS Grid with a mobile breakpoint, automatic dark mode, sticky nav, and client-side form validation — all in three files.

## `index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="Lumina — the adaptive desk lamp that follows your day.">
  <title>Lumina — The Adaptive Desk Lamp</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>

  <a class="skip-link" href="#main">Skip to content</a>

  <header class="site-header" id="site-header">
    <nav class="nav" aria-label="Primary">
      <a class="nav__brand" href="#hero">
        <svg class="nav__logo" width="28" height="28" viewBox="0 0 28 28" aria-hidden="true">
          <circle cx="14" cy="14" r="12" fill="none" stroke="currentColor" stroke-width="2"/>
          <circle cx="14" cy="14" r="5" fill="currentColor"/>
        </svg>
        Lumina
      </a>

      <button class="nav__toggle" id="nav-toggle" aria-expanded="false" aria-controls="nav-menu">
        <span class="nav__toggle-bar"></span>
        <span class="nav__toggle-bar"></span>
        <span class="nav__toggle-bar"></span>
        <span class="visually-hidden">Menu</span>
      </button>

      <ul class="nav__menu" id="nav-menu">
        <li><a href="#features">Features</a></li>
        <li><a href="#specs">Specs</a></li>
        <li><a href="#pricing">Pricing</a></li>
        <li><a class="nav__cta" href="#signup">Pre-order</a></li>
      </ul>
    </nav>
  </header>

  <main id="main">

    <!-- Hero -->
    <section class="hero" id="hero">
      <div class="hero__copy">
        <p class="eyebrow">Now shipping worldwide</p>
        <h1>Light that thinks<br>about your day.</h1>
        <p class="hero__lead">
          Lumina reads ambient brightness, time of day, and your posture —
          then tunes its output so your eyes never have to work overtime.
        </p>
        <div class="hero__actions">
          <a class="btn btn--primary" href="#signup">Pre-order — $149</a>
          <a class="btn btn--ghost" href="#features">See how it works</a>
        </div>
        <p class="hero__note">Free returns · 2-year warranty · Ships March 2025</p>
      </div>
      <div class="hero__visual" aria-hidden="true">
        <div class="lamp">
          <div class="lamp__arm"></div>
          <div class="lamp__head"></div>
          <div class="lamp__glow"></div>
          <div class="lamp__base"></div>
        </div>
      </div>
    </section>

    <!-- Features -->
    <section class="features" id="features">
      <h2 class="section-title">Built around your eyes</h2>
      <div class="features__grid">
        <article class="card">
          <h3>Adaptive output</h3>
          <p>A 60Hz ambient sensor adjusts color temperature from 2700K to 6500K in real time — no flicker, no stepping.</p>
        </article>
        <article class="card">
          <h3>Posture-aware beam</h3>
          <p>A passive IR array detects when you lean in and widens the beam so your workspace stays evenly lit.</p>
        </article>
        <article class="card">
          <h3>Zero-glare optics</h3>
          <p>Side-emitting diffuser means the light source never enters your field of view, even at full brightness.</p>
        </article>
        <article class="card">
          <h3>Weeks of battery</h3>
          <p>Untethered for up to 21 days of typical use. USB-C fast charge gets you a full day in 15 minutes.</p>
        </article>
        <article class="card">
          <h3>Focus timer</h3>
          <p>Optional 50/10
