#!/usr/bin/env python3
"""
Iowa On Demand -- static site generator
Same pattern as pmapparel.com / flyovercon.ink: this script wipes and
regenerates site/ every run. Never edit files in site/ directly.
"""
import json, os, re, shutil, datetime

# ---------------------------------------------------------------------------
# CONSTANTS -- edit these, then re-run
# ---------------------------------------------------------------------------
BASE = "https://www.iowaondemand.com"
SITE_NAME = "Iowa On Demand"
PM_URL = "https://www.pmapparel.com/"
JOTFORM_URL = "https://form.jotform.com/243246726056054"
FB_URL = "https://www.facebook.com/profile.php?id=61568774887639"
IG_URL = "https://www.instagram.com/iowaondemand/"
EMAIL = "info@iowaondemand.com"

TODAY = datetime.date.today().isoformat()
UPDATED_HUMAN = datetime.date.today().strftime("%B %-d, %Y")

# Twelve partnered schools. chipply=None means the store link isn't live yet.
# OWNER: fill in chipply URLs for the six new schools as they go live, then re-run.
SCHOOLS = [
    {"name": "North Polk",               "mascot": "Comets",  "chipply": "https://pmapparel.chipply.com/npiod/"},
    {"name": "Woodward-Granger",         "mascot": "Hawks",   "chipply": "https://pmapparel.chipply.com/iodwg/"},
    {"name": "Ankeny Christian Academy", "mascot": "Eagles",  "chipply": "https://pmapparel.chipply.com/iodaca"},
    {"name": "Ankeny Centennial",        "mascot": "Jaguars", "chipply": "https://pmapparel.chipply.com/centiod/?action=viewall"},
    {"name": "Ankeny",                   "mascot": "Hawks",   "chipply": "https://pmapparel.chipply.com/ioda/?action=viewall"},
    {"name": "Saydel",                   "mascot": "Eagles",  "chipply": "https://pmapparel.chipply.com/siod/?action=viewall"},
    {"name": "Ballard",                  "mascot": "Bombers", "chipply": None},
    {"name": "Bondurant-Farrar",         "mascot": "Bluejays","chipply": None},
    {"name": "Perry",                    "mascot": "Bluejays","chipply": None},
    {"name": "Roosevelt",                "mascot": "Roughriders","chipply": None},
    {"name": "Dallas Center-Grimes",     "mascot": "Mustangs","chipply": None},
    {"name": "Johnston",                 "mascot": "Dragons", "chipply": None},
]

FAQS = [
    ("How does Iowa On Demand work?",
     "Once your school partners with us, we build a dedicated online store for your spirit wear. Students, parents, and staff order directly, and every item prints on demand. No bulk minimums, no leftover inventory."),
    ("What kind of apparel can we order?",
     "T-shirts, hoodies, sweatpants, hats, and more. If you need something specific, tell us and we'll help source it."),
    ("How long does an order take?",
     "Most orders finish in 3 to 5 business days. Everything is produced locally in Polk City, which keeps turnaround short."),
    ("Can students and parents order directly?",
     "Yes. Every partnered school gets its own online store, open 24/7, no coordinator required to collect sizes or money."),
    ("Do you work with anyone besides schools?",
     f'Iowa On Demand is focused on schools. If you need custom apparel for a business, organization, or event, our parent company <a href="{PM_URL}">P&amp;M Apparel</a> can do it all.'),
    ("Can we get custom designs for our school?",
     "Yes. Our art team can build designs from scratch or refine something you already have in mind."),
    ("What happens if something's wrong with an order?",
     "Reach out and we'll fix it. We stand behind what we print."),
    ("Is there a minimum order size?",
     "No. Print-on-demand means a single shirt is a normal order, not a special case."),
    ("What does it cost a school to set up a store?",
     "Nothing. There's no setup fee for a partnered school. We build and manage the store; you share the link."),
    ("My school isn't listed. How do we get started?",
     "Tell us. Adding a school is quick, and there's no cost to get set up."),
]

# ---------------------------------------------------------------------------
# DESIGN SYSTEM (distinct from pmapparel.com / flyovercon.ink)
# Varsity / scoreboard aesthetic, built around the real Iowa On Demand mark:
# gold #fcb426 and teal #008ea9, pulled directly from the logo file. Display
# face Oswald (condensed, athletic), body Inter, roster numbers in IBM Plex Mono.
# ---------------------------------------------------------------------------
CSS = """
:root{
  --ink:#101010;
  --ink-2:#1a1a1a;
  --chalk:#ffffff;
  --gold:#fcb426;
  --gold-2:#ffc94d;
  --teal:#008ea9;
  --line:#33333340;
  --gray:#a8a8a8;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;background:var(--ink);color:var(--chalk);
  font-family:'Inter',system-ui,sans-serif;line-height:1.55;
  -webkit-font-smoothing:antialiased;
}
h1,h2,h3,.display{
  font-family:'Oswald',system-ui,sans-serif;
  text-transform:uppercase;letter-spacing:.02em;font-weight:600;
  margin:0 0 .4em;color:var(--chalk);
}
h1{font-size:clamp(2.4rem,6vw,4.2rem);line-height:1.02;font-weight:700}
h2{font-size:clamp(1.5rem,3.2vw,2.2rem);letter-spacing:.03em}
h3{font-size:1.15rem}
p{margin:0 0 1em;color:#d8d6cd}
a{color:var(--gold-2)}
.mono{font-family:'IBM Plex Mono',monospace}
.wrap{max-width:1120px;margin:0 auto;padding:0 24px}
.eyebrow{
  font-family:'IBM Plex Mono',monospace;font-size:.78rem;letter-spacing:.18em;
  text-transform:uppercase;color:var(--gold-2);margin:0 0 .8em;display:block;
}
a:focus-visible,button:focus-visible{outline:3px solid var(--gold-2);outline-offset:2px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}

/* header */
header.site{position:sticky;top:0;z-index:50;background:rgba(18,20,28,.92);
  backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}
.nav{display:flex;align-items:center;justify-content:space-between;padding:14px 0}
.wordmark{display:flex;align-items:center;gap:12px;text-decoration:none}
.badge{width:44px;height:44px;flex:none}
.wordmark-text{font-family:'Oswald',sans-serif;font-weight:700;letter-spacing:.05em;
  color:var(--chalk);font-size:1.05rem;line-height:1.05;text-transform:uppercase}
.wordmark-text span{display:block;font-size:.62rem;color:var(--gold-2);letter-spacing:.16em;
  font-family:'IBM Plex Mono',monospace;font-weight:500}
nav.links{display:flex;gap:26px;align-items:center}
nav.links a{color:var(--chalk);text-decoration:none;font-family:'Oswald',sans-serif;
  text-transform:uppercase;font-size:.85rem;letter-spacing:.08em}
nav.links a:hover{color:var(--gold-2)}
.btn{display:inline-block;background:var(--gold);color:var(--ink);font-family:'Oswald',sans-serif;
  text-transform:uppercase;letter-spacing:.06em;font-weight:600;padding:11px 22px;
  text-decoration:none;font-size:.85rem;border:2px solid var(--gold)}
.btn:hover{background:var(--gold-2);border-color:var(--gold-2)}
.btn.ghost{background:transparent;color:var(--chalk);border-color:var(--chalk)}
.btn.ghost:hover{border-color:var(--gold-2);color:var(--gold-2)}

/* ticker */
.ticker-wrap{background:var(--teal);border-top:1px solid var(--line);border-bottom:1px solid var(--line);
  overflow:hidden;white-space:nowrap}
.ticker{display:inline-block;padding:9px 0;animation:scroll 26s linear infinite}
.ticker span{font-family:'IBM Plex Mono',monospace;font-size:.78rem;letter-spacing:.1em;
  text-transform:uppercase;color:#eef3fa;margin-right:2.5em}
@keyframes scroll{from{transform:translateX(0)}to{transform:translateX(-50%)}}

/* hero */
.hero{padding:76px 0 60px;border-bottom:1px solid var(--line);
  background:radial-gradient(ellipse at top right, #1c2130 0%, var(--ink) 62%)}
.hero p.lead{font-size:1.18rem;max-width:640px}
.hero .ctas{display:flex;gap:14px;margin-top:26px;flex-wrap:wrap}

/* feature grid */
.section{padding:60px 0}
.section.alt{background:var(--ink-2)}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:22px;margin-top:30px}
@media (max-width:900px){.grid4{grid-template-columns:repeat(2,1fr)}}
@media (max-width:560px){.grid4{grid-template-columns:1fr}}
.feature{border:1px solid var(--line);padding:22px 20px;background:var(--ink)}
.feature .num{font-family:'IBM Plex Mono',monospace;color:var(--gold-2);font-size:.8rem;letter-spacing:.1em}
.feature h3{margin-top:.5em}
.feature p{margin:0;font-size:.94rem;color:var(--gray)}

/* roster grid */
.roster{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:30px}
@media (max-width:820px){.roster{grid-template-columns:repeat(2,1fr)}}
@media (max-width:520px){.roster{grid-template-columns:1fr}}
.jersey{border:1px solid var(--line);background:var(--ink-2);padding:20px;display:flex;
  flex-direction:column;gap:10px;position:relative}
.jersey .no{font-family:'Oswald',sans-serif;font-size:2.1rem;font-weight:700;color:var(--gold);
  line-height:1}
.jersey h3{margin:0;font-size:1.05rem}
.jersey .mascot{color:var(--gray);font-family:'IBM Plex Mono',monospace;font-size:.75rem;
  text-transform:uppercase;letter-spacing:.08em}
.jersey .status{margin-top:auto;padding-top:8px}
.jersey a.store{color:var(--gold-2);text-decoration:none;font-family:'Oswald',sans-serif;
  text-transform:uppercase;font-size:.82rem;letter-spacing:.05em;border-top:1px solid var(--line);
  padding-top:10px;display:block}
.jersey a.store:hover{color:var(--chalk)}
.jersey .soon{color:var(--gray);font-family:'IBM Plex Mono',monospace;font-size:.72rem;
  text-transform:uppercase;letter-spacing:.08em;border-top:1px solid var(--line);padding-top:10px;
  display:block}

/* faq */
.faq-item{border-bottom:1px solid var(--line);padding:20px 0}
.faq-item h3{margin:0 0 8px;font-size:1.05rem;font-family:'Inter',sans-serif;
  text-transform:none;letter-spacing:0;font-weight:700;color:var(--gold-2)}
.faq-item p{margin:0;color:#d8d6cd}

/* cta band */
.cta-band{border-top:1px solid var(--line);border-bottom:1px solid var(--line);
  background:linear-gradient(120deg,#1b2233,#171a24);padding:52px 0;text-align:left}
.cta-band .wrap{display:flex;justify-content:space-between;align-items:center;gap:24px;flex-wrap:wrap}
.cta-band h2{margin:0 0 6px}
.cta-band p{margin:0;color:var(--gray);max-width:520px}

/* footer */
footer{border-top:1px solid var(--line);padding:40px 0 30px;background:var(--ink-2)}
footer .wrap{display:flex;justify-content:space-between;flex-wrap:wrap;gap:24px}
footer .cols{display:flex;gap:52px;flex-wrap:wrap}
footer h4{font-family:'IBM Plex Mono',monospace;font-size:.72rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--gray);margin:0 0 12px}
footer a{display:block;color:var(--chalk);text-decoration:none;font-size:.9rem;margin-bottom:8px}
footer a:hover{color:var(--gold-2)}
.social{display:flex;gap:14px;margin-top:14px}
.social a{width:34px;height:34px;border:1px solid var(--line);display:flex;align-items:center;
  justify-content:center}
.fineprint{margin-top:28px;padding-top:20px;border-top:1px solid var(--line);
  font-family:'IBM Plex Mono',monospace;font-size:.72rem;color:var(--gray)}

/* contact */
.contact-card{border:1px solid var(--line);background:var(--ink-2);padding:34px;max-width:560px}
.contact-card ul{margin:0 0 22px;padding-left:20px;color:#d8d6cd}
.contact-card li{margin-bottom:8px}
"""

BADGE_IMG = '<img class="badge" src="/assets/logo.png" alt="Iowa On Demand logo" width="44" height="44" loading="eager">'

FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&'
    'family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" '
    'rel="stylesheet">'
)

NAV_ITEMS = [("/", "Home"), ("/schools/", "Schools"), ("/faq/", "FAQ"), ("/contact/", "Contact")]

# ---------------------------------------------------------------------------
# PAGE SHELL
# ---------------------------------------------------------------------------
def breadcrumb_schema(path, label):
    items = [{"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"}]
    if path != "/":
        items.append({"@type": "ListItem", "position": 2, "name": label, "item": BASE + path})
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}

ORG_SCHEMA = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Iowa On Demand",
    "url": BASE + "/",
    "email": EMAIL,
    "parentOrganization": {"@type": "Organization", "name": "P&M Apparel", "url": PM_URL},
    "sameAs": [FB_URL, IG_URL],
    "areaServed": "Iowa",
    "description": "Print-on-demand spirit wear stores for Iowa schools, produced in Polk City, Iowa."
}

def page(path, label, meta_title, meta_desc, body_html, extra_schema=None):
    schemas = [ORG_SCHEMA, breadcrumb_schema(path, label)]
    if extra_schema:
        schemas.append(extra_schema)
    schema_tags = "\n".join(
        f'<script type="application/ld+json">{json.dumps(s)}</script>' for s in schemas
    )
    nav_html = "\n".join(
        f'<a href="{href}">{text}</a>' for href, text in NAV_ITEMS
    )
    canonical = BASE + path
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{meta_title}</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32.png">
<link rel="icon" type="image/png" sizes="64x64" href="/assets/favicon-64.png">
<link rel="apple-touch-icon" href="/assets/favicon-180.png">
<meta property="og:image" content="{BASE}/assets/logo.png">
<meta property="og:title" content="{meta_title}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Iowa On Demand">
{FONT_LINKS}
<style>{CSS}</style>
{schema_tags}
</head>
<body>
<header class="site">
  <div class="wrap nav">
    <a class="wordmark" href="/">
      {BADGE_IMG}
      <span class="wordmark-text">Iowa On Demand<span>a division of P&amp;M Apparel</span></span>
    </a>
    <nav class="links">
      {nav_html}
      <a class="btn" href="/schools/">Shop Your School</a>
    </nav>
  </div>
</header>
<div class="ticker-wrap" aria-hidden="true">
  <div class="ticker">
    <span>12 SCHOOLS PARTNERED</span><span>3&ndash;5 DAY TURNAROUND</span><span>ZERO SETUP COST</span>
    <span>PRINTED IN POLK CITY, IOWA</span>
    <span>12 SCHOOLS PARTNERED</span><span>3&ndash;5 DAY TURNAROUND</span><span>ZERO SETUP COST</span>
    <span>PRINTED IN POLK CITY, IOWA</span>
  </div>
</div>
<main>
{body_html}
</main>
<footer>
  <div class="wrap">
    <div>
      <a class="wordmark" href="/" style="margin-bottom:14px">
        {BADGE_IMG}
        <span class="wordmark-text">Iowa On Demand</span>
      </a>
      <p style="max-width:280px;color:var(--gray);font-size:.9rem">Print-on-demand spirit wear for Iowa schools. A division of <a href="{PM_URL}">P&amp;M Apparel</a>, Polk City, Iowa.</p>
      <div class="social">
        <a href="{FB_URL}" aria-label="Facebook">f</a>
        <a href="{IG_URL}" aria-label="Instagram">ig</a>
      </div>
    </div>
    <div class="cols">
      <div>
        <h4>Site</h4>
        <a href="/">Home</a>
        <a href="/schools/">Schools</a>
        <a href="/faq/">FAQ</a>
        <a href="/contact/">Contact</a>
      </div>
      <div>
        <h4>Get in touch</h4>
        <a href="mailto:{EMAIL}">{EMAIL}</a>
        <a href="{JOTFORM_URL}">Add your school</a>
        <a href="{PM_URL}">pmapparel.com</a>
      </div>
    </div>
  </div>
  <div class="wrap fineprint">Updated {UPDATED_HUMAN} &middot; &copy; {datetime.date.today().year} Iowa On Demand, a division of P&amp;M Apparel</div>
</footer>
</body>
</html>"""


# ---------------------------------------------------------------------------
# PAGE BODIES
# ---------------------------------------------------------------------------
def home_body():
    features = [
        ("01", "Iowa-Based Production", "Every item is designed and printed right here in Iowa. Fast turnaround, and we understand what our schools need because we're part of the same communities."),
        ("02", "On-Demand Convenience", "No long waits, no bulk minimums. Gear prints when it's ordered, so there's no overstock sitting in a closet."),
        ("03", "Built for Schools", "Dedicated online stores for spirit wear, team gear, and fundraiser apparel. Set up once, order year-round."),
        ("04", "Zero Setup Cost", "We build and manage the store at no cost to the school. Share the link and let students, parents, and staff order direct."),
    ]
    feat_html = "\n".join(
        f'<div class="feature"><span class="num">{n}</span><h3>{t}</h3><p>{d}</p></div>'
        for n, t, d in features
    )
    live_schools = [s for s in SCHOOLS if s["chipply"]][:6]
    preview_html = "\n".join(
        f'''<div class="jersey"><span class="no">{i:02d}</span><h3>{s["name"]}</h3>
        <span class="mascot">{s["mascot"]}</span>
        <a class="store" href="{s["chipply"]}">Shop the store &rarr;</a></div>'''
        for i, s in enumerate(live_schools, 1)
    )
    return f"""
<section class="hero">
  <div class="wrap">
    <span class="eyebrow">A Division of P&amp;M Apparel &middot; Polk City, Iowa</span>
    <h1>Twelve schools.<br>One place to shop.</h1>
    <p class="lead">Iowa On Demand builds a dedicated online store for your school's spirit wear. Students, parents, and staff order anytime. Every piece prints on demand, right here in Iowa.</p>
    <div class="ctas">
      <a class="btn" href="/schools/">Shop Your School</a>
      <a class="btn ghost" href="/contact/">Bring It To My School</a>
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <span class="eyebrow">What Sets Us Apart</span>
    <h2>Local gear, ordered your way.</h2>
    <div class="grid4">
      {feat_html}
    </div>
  </div>
</section>

<section class="section alt">
  <div class="wrap">
    <span class="eyebrow">The Roster</span>
    <h2>Shop a partnered school.</h2>
    <div class="roster">
      {preview_html}
    </div>
    <p style="margin-top:26px"><a href="/schools/">See all 12 partnered schools &rarr;</a></p>
  </div>
</section>

<section class="cta-band">
  <div class="wrap">
    <div>
      <h2>Don't see your school?</h2>
      <p>Adding a school is quick and there's no cost to get set up. Tell us about your school and we'll take it from there.</p>
    </div>
    <a class="btn" href="{JOTFORM_URL}">Add Your School</a>
  </div>
</section>
"""

def schools_body():
    cards = []
    for i, s in enumerate(SCHOOLS, 1):
        if s["chipply"]:
            action = f'<a class="store" href="{s["chipply"]}">Shop the store &rarr;</a>'
        else:
            action = '<span class="soon">Store opening soon</span>'
        cards.append(
            f'''<div class="jersey"><span class="no">{i:02d}</span><h3>{s["name"]}</h3>
            <span class="mascot">{s["mascot"]}</span>{action}</div>'''
        )
    cards_html = "\n".join(cards)
    return f"""
<section class="hero" style="padding-bottom:36px">
  <div class="wrap">
    <span class="eyebrow">Our Partnered Schools</span>
    <h1>Shop your school.</h1>
    <p class="lead">Twelve Iowa schools, twelve dedicated stores. Pick yours below to shop spirit wear, team gear, and fundraiser apparel, printed on demand.</p>
  </div>
</section>
<section class="section">
  <div class="wrap">
    <div class="roster">
      {cards_html}
    </div>
  </div>
</section>
<section class="cta-band">
  <div class="wrap">
    <div>
      <h2>Not seeing your school?</h2>
      <p>We'd love to bring Iowa On Demand to your community. Reach out and let's start the conversation, there's no cost to get set up.</p>
    </div>
    <a class="btn" href="{JOTFORM_URL}">Add Your School</a>
  </div>
</section>
"""

def faq_body():
    items = "\n".join(
        f'<div class="faq-item"><h3>{q}</h3><p>{a}</p></div>' for q, a in FAQS
    )
    return f"""
<section class="hero" style="padding-bottom:20px">
  <div class="wrap">
    <span class="eyebrow">Frequently Asked</span>
    <h1>Questions, answered.</h1>
    <p class="lead">Everything schools and families ask us most, in one place.</p>
  </div>
</section>
<section class="section" style="padding-top:0">
  <div class="wrap" style="max-width:820px">
    {items}
  </div>
</section>
<section class="cta-band">
  <div class="wrap">
    <div>
      <h2>Still have a question?</h2>
      <p>Send it over. We'll get back to you directly.</p>
    </div>
    <a class="btn" href="/contact/">Contact Us</a>
  </div>
</section>
"""

def contact_body():
    return f"""
<section class="hero">
  <div class="wrap">
    <span class="eyebrow">Get In Touch</span>
    <h1>Let's outfit your school.</h1>
    <p class="lead">Whether you're setting up a new store, adding a design, or just have a question, we're here to help.</p>
  </div>
</section>
<section class="section" style="padding-top:0">
  <div class="wrap">
    <div class="contact-card">
      <h3 style="text-transform:none;font-family:'Inter',sans-serif;font-size:1.2rem;color:var(--chalk)">Why reach out?</h3>
      <ul>
        <li>Partner with us for your school's custom apparel.</li>
        <li>Set up a dedicated online store for students, parents, and staff.</li>
        <li>Ask about our process, products, or anything else.</li>
      </ul>
      <p style="color:var(--gray);font-size:.92rem">We're here to help your school shine with custom, on-demand gear made in Iowa.</p>
      <a class="btn" href="{JOTFORM_URL}">Get In Touch</a>
      <p style="margin-top:18px;font-size:.9rem">Or email us directly at <a href="mailto:{EMAIL}">{EMAIL}</a></p>
    </div>
  </div>
</section>
"""

def _strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)

FAQ_SCHEMA = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
        {
            "@type": "Question", "name": q,
            "acceptedAnswer": {"@type": "Answer", "text": _strip_tags(a)}
        } for q, a in FAQS
    ]
}

PAGES = {
    "/": {
        "label": "Home",
        "title": "Iowa On Demand | Print-on-Demand Spirit Wear for Iowa Schools",
        "desc": "Iowa On Demand builds print-on-demand spirit wear stores for Iowa schools. No minimums, no setup cost, printed locally in Polk City, Iowa. A division of P&M Apparel.",
        "body": home_body(),
        "schema": None,
    },
    "/schools/": {
        "label": "Schools",
        "title": "Partnered Schools | Iowa On Demand",
        "desc": "Shop spirit wear for all 12 Iowa On Demand partnered schools, from North Polk to Johnston. Dedicated print-on-demand stores for every school.",
        "body": schools_body(),
        "schema": None,
    },
    "/faq/": {
        "label": "FAQ",
        "title": "FAQ | Iowa On Demand",
        "desc": "Answers to common questions about Iowa On Demand's print-on-demand school apparel program: turnaround times, ordering, custom designs, and more.",
        "body": faq_body(),
        "schema": FAQ_SCHEMA,
    },
    "/contact/": {
        "label": "Contact",
        "title": "Contact | Iowa On Demand",
        "desc": "Get in touch with Iowa On Demand to set up a print-on-demand spirit wear store for your Iowa school, or ask a question about an existing order.",
        "body": contact_body(),
        "schema": None,
    },
}

# ---------------------------------------------------------------------------
# BUILD
# ---------------------------------------------------------------------------
def build():
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(root)

    # copy real brand assets (logo + favicons)
    src_assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    dst_assets = os.path.join(root, "assets")
    if os.path.isdir(src_assets):
        shutil.copytree(src_assets, dst_assets)

    for path, p in PAGES.items():
        html = page(path, p["label"], p["title"], p["desc"], p["body"], p["schema"])
        if path == "/":
            out_dir = root
        else:
            out_dir = os.path.join(root, path.strip("/"))
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

    # sitemap.xml
    urls = "".join(
        f"<url><loc>{BASE}{p}</loc><lastmod>{TODAY}</lastmod></url>" for p in PAGES
    )
    with open(os.path.join(root, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?>'
                 f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')

    # robots.txt -- explicitly welcome AI crawlers, matching pmapparel.com pattern
    with open(os.path.join(root, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(
            "User-agent: *\nAllow: /\n\n"
            "User-agent: GPTBot\nAllow: /\n\n"
            "User-agent: OAI-SearchBot\nAllow: /\n\n"
            "User-agent: ClaudeBot\nAllow: /\n\n"
            "User-agent: Claude-SearchBot\nAllow: /\n\n"
            "User-agent: PerplexityBot\nAllow: /\n\n"
            "User-agent: Google-Extended\nAllow: /\n\n"
            f"Sitemap: {BASE}/sitemap.xml\n"
        )

    # vercel.json -- noindex the preview deployment until DNS cutover
    with open(os.path.join(root, "vercel.json"), "w", encoding="utf-8") as f:
        json.dump({
            "headers": [{
                "source": "/(.*)",
                "headers": [{"key": "X-Robots-Tag", "value": "noindex"}]
            }]
        }, f, indent=2)

    return root


# ---------------------------------------------------------------------------
# VERIFICATION GATE
# ---------------------------------------------------------------------------
def verify(root):
    errors = []
    titles = set()
    for path in PAGES:
        fp = os.path.join(root, path.strip("/"), "index.html") if path != "/" else os.path.join(root, "index.html")
        if not os.path.exists(fp):
            errors.append(f"MISSING FILE: {fp}")
            continue
        html = open(fp, encoding="utf-8").read()

        m = re.search(r"<title>(.*?)</title>", html)
        title = m.group(1) if m else None
        if not title:
            errors.append(f"{path}: no <title>")
        elif title in titles:
            errors.append(f"{path}: duplicate title '{title}'")
        else:
            titles.add(title)

        h1s = re.findall(r"<h1[ >]", html)
        if len(h1s) != 1:
            errors.append(f"{path}: expected 1 <h1>, found {len(h1s)}")

        m = re.search(r'name="description" content="(.*?)"', html)
        desc = m.group(1) if m else ""
        if len(desc) < 70:
            errors.append(f"{path}: meta description under 70 chars ({len(desc)})")

        for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
            try:
                json.loads(block)
            except json.JSONDecodeError as e:
                errors.append(f"{path}: invalid JSON-LD ({e})")

        for bad in ["TODO", "PLACEHOLDER", "Lorem ipsum", "TBD"]:
            if bad in html:
                errors.append(f"{path}: placeholder text '{bad}' found")

        if "\u2014" in html or "\u2013 " in html.replace("3\u20135", ""):
            # allow the turnaround-time en dash "3-5"; flag stray em dashes
            if "\u2014" in html:
                errors.append(f"{path}: em dash found")

        for href in re.findall(r'<a [^>]*href="(/[a-z0-9/_.-]*)"', html):
            if "." in href.rsplit("/", 1)[-1]:
                continue  # asset link (favicon, image, etc.), not a page
            clean = href if href.endswith("/") or href == "/" else href + "/"
            if clean not in PAGES and href not in ("/", ""):
                errors.append(f"{path}: internal link to unknown page {href}")

    if errors:
        print("VERIFICATION FAILED:")
        for e in errors:
            print(" -", e)
        raise SystemExit(1)
    print(f"Verification passed. {len(PAGES)} pages built cleanly.")


if __name__ == "__main__":
    out = build()
    verify(out)
    print(f"Built to {out}")
