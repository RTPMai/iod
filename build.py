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
# All twelve are live as of Sep 2, 2026. Eleven use the 2026-27 IOD*26 slugs;
# North Polk was moved to the custom slug /npiod.
# logo=None means we don't have real mascot art yet -- shows an initial badge.
# "cities" lists EVERY community the district officially serves (verified
# against each district's own site / NCES / Wikipedia, not just its mailing
# address) -- this drives both the on-card city line and the "Communities We
# Serve" directory, so keep it complete when adding a school.
# OWNER: adding a school means a chipply URL, a logo in assets/schools/ (SVG
# preferred -- it scales; the PNGs here are lower-res rasters of the same art),
# and a complete "cities" list. Then re-run.
# NOTE: build() wipes site/ and re-copies assets from the ROOT ./assets dir.
# On a fresh clone that dir does not exist -- run `cp -r site/assets ./assets`
# BEFORE the first build or the images and site/api/contact.js are lost.
SCHOOLS = [
    {"name": "North Polk",               "mascot": "Comets",  "chipply": "https://pmapparel.chipply.com/npiod",
     "logo": "/assets/schools/northpolk.png",
     "cities": ["Alleman", "Elkhart", "Polk City", "Sheldahl"]},
    {"name": "Woodward-Granger",         "mascot": "Hawks",   "chipply": "https://pmapparel.chipply.com/IODWG26",
     "logo": "/assets/schools/woodward-granger.png",
     "cities": ["Woodward", "Granger"]},
    {"name": "Ankeny Christian Academy", "mascot": "Eagles",  "chipply": "https://pmapparel.chipply.com/IODACA26",
     "logo": "/assets/schools/ankeny-christian-academy.png",
     "cities": ["Ankeny"]},
    {"name": "Ankeny Centennial",        "mascot": "Jaguars", "chipply": "https://pmapparel.chipply.com/IODCENT26",
     "logo": "/assets/schools/ankeny-centennial.png",
     "cities": ["Ankeny"]},
    {"name": "Ankeny",                   "mascot": "Hawks",   "chipply": "https://pmapparel.chipply.com/IODAH26",
     "logo": "/assets/schools/ankeny.png",
     "cities": ["Ankeny"]},
    {"name": "Saydel",                   "mascot": "Eagles",  "chipply": "https://pmapparel.chipply.com/IODSE26",
     "logo": "/assets/schools/saydel.png",
     "cities": ["Des Moines", "Saylorville"]},
    {"name": "Ballard",                  "mascot": "Bombers",     "chipply": "https://pmapparel.chipply.com/IODBALLARD26",
     "logo": "/assets/schools/ballard.svg",
     "cities": ["Huxley", "Cambridge", "Kelley", "Slater"]},
    {"name": "Bondurant-Farrar",         "mascot": "Bluejays",    "chipply": "https://pmapparel.chipply.com/IODBF26",
     "logo": "/assets/schools/bondurant-farrar.svg",
     "cities": ["Bondurant", "Farrar"]},
    {"name": "Perry",                    "mascot": "Bluejays",    "chipply": "https://pmapparel.chipply.com/IODPB26",
     "logo": "/assets/schools/perry.svg",
     "cities": ["Perry"]},
    {"name": "Roosevelt",                "mascot": "Roughriders", "chipply": "https://pmapparel.chipply.com/IODRR26",
     "logo": "/assets/schools/roosevelt.svg",
     "cities": ["Des Moines"]},
    {"name": "Dallas Center-Grimes",     "mascot": "Mustangs",    "chipply": "https://pmapparel.chipply.com/IODDCG26",
     "logo": "/assets/schools/dallas-center-grimes.svg",
     "cities": ["Dallas Center", "Grimes"]},
    {"name": "Johnston",                 "mascot": "Dragons",     "chipply": "https://pmapparel.chipply.com/IODJD26",
     "logo": "/assets/schools/johnston.svg",
     "cities": ["Johnston"]},
]

def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

def city_display(cities):
    """'Alleman, Elkhart, Polk City & Sheldahl, IA' -- joins a school's city list."""
    if len(cities) == 1:
        return f"{cities[0]}, IA"
    return f"{', '.join(cities[:-1])} & {cities[-1]}, IA"

# Every community any partnered district serves, derived from SCHOOLS itself
# so this list can't drift out of sync -- alphabetical for the directory.
COMMUNITIES = sorted({c for s in SCHOOLS for c in s["cities"]})

# community -> schools that serve it, preserving SCHOOLS' master order so a
# school's numbered badge (01-12) stays consistent everywhere it appears.
SCHOOLS_BY_COMMUNITY = {
    c: [s for s in SCHOOLS if c in s["cities"]] for c in COMMUNITIES
}
SCHOOL_INDEX = {s["name"]: i for i, s in enumerate(SCHOOLS, 1)}
SCHOOL_SLUGS = {s["name"]: slugify(s["name"]) for s in SCHOOLS}

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
     f'Iowa On Demand is focused on schools. If you need custom apparel for a business, organization, or event, our parent company <a href="{PM_URL}" target="_blank" rel="noopener noreferrer">P&amp;M Apparel</a> can do it all.'),
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
    ("What areas of Iowa does Iowa On Demand serve?",
     f"We partner with schools across the Des Moines metro and central Iowa, including {', '.join(COMMUNITIES[:-1])}, and {COMMUNITIES[-1]}. If your community isn't on the list yet, reach out."),
]

# ---------------------------------------------------------------------------
# LINK HELPER -- external destinations open in a new tab
# ---------------------------------------------------------------------------
def ext(url, text, cls="", aria_label=None):
    cls_attr = f' class="{cls}"' if cls else ""
    aria_attr = f' aria-label="{aria_label}"' if aria_label else ""
    return (f'<a href="{url}" target="_blank" rel="noopener noreferrer"{cls_attr}{aria_attr}>'
            f'{text}<span class="sr-only"> (opens in new tab)</span></a>')

# ---------------------------------------------------------------------------
# DESIGN SYSTEM (distinct from pmapparel.com / flyovercon.ink)
# Bright varsity look built around the real Iowa On Demand mark: gold
# #fcb426 and teal #008ea9, pulled directly from the logo file. Two neutral
# background tones only (white + a single warm-gray surface) so gold reads
# as a deliberate accent, never as a background wash. Mobile-first: base
# rules target small screens, min-width media queries layer on desktop.
# Display face Oswald (condensed, athletic), body Inter, roster numbers and
# labels in IBM Plex Mono.
# ---------------------------------------------------------------------------
CSS = """
:root{
  --paper:#ffffff;
  --surface:#f2f0ea;
  --card:#ffffff;
  --ink:#181a1f;
  --gold:#fcb426;
  --gold-dark:#c9860a;
  --teal:#008ea9;
  --teal-dark:#00697d;
  --line:#e2ddd0;
  --gray:#666a71;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{
  margin:0;background:var(--paper);color:var(--ink);
  font-family:'Inter',system-ui,sans-serif;line-height:1.55;font-size:16px;
  -webkit-font-smoothing:antialiased;
}
h1,h2,h3,.display{
  font-family:'Oswald',system-ui,sans-serif;
  text-transform:uppercase;letter-spacing:.02em;font-weight:600;
  margin:0 0 .4em;color:var(--ink);
}
h1{font-size:clamp(2rem,8vw,4.2rem);line-height:1.04;font-weight:700}
h2{font-size:clamp(1.4rem,5vw,2.2rem);letter-spacing:.03em}
h3{font-size:1.08rem}
p{margin:0 0 1em;color:#3a3d44}
a{color:var(--teal-dark)}
.mono{font-family:'IBM Plex Mono',monospace}
.wrap{max-width:1120px;margin:0 auto;padding:0 18px}
.eyebrow{
  font-family:'IBM Plex Mono',monospace;font-size:.72rem;letter-spacing:.16em;
  text-transform:uppercase;color:var(--teal-dark);margin:0 0 .8em;display:block;
}
a:focus-visible,button:focus-visible{outline:3px solid var(--teal-dark);outline-offset:2px}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}

.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;
  clip:rect(0,0,0,0);white-space:nowrap;border:0}
.skip-link{position:absolute;left:-999px;top:auto;background:var(--ink);color:#fff;
  padding:12px 20px;z-index:100;text-decoration:none;font-family:'Oswald',sans-serif;
  text-transform:uppercase;letter-spacing:.05em;font-size:.85rem}
.skip-link:focus{left:12px;top:12px}

/* breadcrumb */
.breadcrumb{padding:12px 0}
.breadcrumb ol{list-style:none;display:flex;flex-wrap:wrap;gap:6px;margin:0;padding:0;
  font-family:'IBM Plex Mono',monospace;font-size:.74rem;color:var(--gray)}
.breadcrumb a{color:var(--gray);text-decoration:none}
.breadcrumb a:hover{color:var(--teal-dark)}
.breadcrumb li:not(:last-child)::after{content:"/";margin-left:6px;color:var(--line)}
.breadcrumb li[aria-current]{color:var(--ink)}

/* header */
header.site{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.94);
  backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}
.nav{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:10px;padding:12px 0}
.wordmark{display:flex;align-items:center;gap:10px;text-decoration:none}
.badge{width:40px;height:40px;flex:none}
.wordmark-text{font-family:'Oswald',sans-serif;font-weight:700;letter-spacing:.04em;
  color:var(--ink);font-size:.98rem;line-height:1.05;text-transform:uppercase}
.wordmark-text span{display:block;font-size:.6rem;color:var(--teal-dark);letter-spacing:.14em;
  font-family:'IBM Plex Mono',monospace;font-weight:500}
nav.links{display:flex;flex-wrap:wrap;gap:14px 20px;align-items:center;width:100%;
  justify-content:center;order:3}
nav.links a{color:var(--ink);text-decoration:none;font-family:'Oswald',sans-serif;
  text-transform:uppercase;font-size:.85rem;letter-spacing:.06em}
nav.links a:hover{color:var(--teal-dark)}
.btn{display:inline-block;background:var(--gold);color:var(--ink);font-family:'Oswald',sans-serif;
  text-transform:uppercase;letter-spacing:.05em;font-weight:600;padding:11px 22px;
  text-decoration:none;font-size:.85rem;border:2px solid var(--gold);border-radius:3px;
  flex:1 1 100%;text-align:center}
.btn.ghost{background:transparent;color:var(--ink);border-color:var(--ink)}
.btn.ghost:hover{border-color:var(--teal-dark);color:var(--teal-dark)}
.btn:hover{background:var(--gold-dark);border-color:var(--gold-dark)}
@media (min-width:480px){.btn{flex:0 0 auto}}
@media (min-width:760px){nav.links{width:auto;order:0;justify-content:flex-start}}

/* stat bar (static, not a marquee) */
.stat-bar{background:var(--teal)}
.stat-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:rgba(255,255,255,.28)}
.stat-grid div{background:var(--teal);padding:12px 8px;text-align:center;color:#fff;
  font-family:'IBM Plex Mono',monospace;font-size:.66rem;letter-spacing:.07em;text-transform:uppercase}
@media (min-width:700px){.stat-grid{grid-template-columns:repeat(4,1fr)}.stat-grid div{font-size:.74rem;padding:12px}}

/* hero */
.hero{padding:40px 0 32px;border-bottom:1px solid var(--line);
  background:radial-gradient(ellipse at top right, #e8f6f9 0%, var(--paper) 62%)}
.hero p.lead{font-size:1.05rem;max-width:640px}
.hero .ctas{display:flex;gap:12px;margin-top:22px;flex-wrap:wrap}
.hero .ctas .btn{flex:1 1 100%}
@media (min-width:480px){.hero .ctas .btn{flex:0 0 auto}}
@media (min-width:700px){.hero{padding:68px 0 54px}.hero p.lead{font-size:1.18rem}}

/* feature grid */
.section{padding:40px 0}
.section.alt{background:var(--surface)}
.grid4{display:grid;grid-template-columns:1fr;gap:14px;margin-top:24px}
@media (min-width:640px){.grid4{grid-template-columns:repeat(2,1fr)}}
@media (min-width:980px){.grid4{grid-template-columns:repeat(4,1fr);gap:20px}}
.feature{border:1px solid var(--line);border-radius:5px;padding:20px 18px;background:var(--card);
  box-shadow:0 1px 2px rgba(20,20,10,.04)}
.feature .num{font-family:'IBM Plex Mono',monospace;color:var(--gold-dark);font-size:.78rem;letter-spacing:.1em}
.feature h3{margin-top:.5em}
.feature p{margin:0;font-size:.92rem;color:var(--gray)}
@media (min-width:700px){.section{padding:56px 0}}
.facts3{display:grid;grid-template-columns:1fr;gap:14px;margin-top:10px}
@media (min-width:700px){.facts3{grid-template-columns:repeat(3,1fr)}}

/* roster grid */
.roster{display:grid;grid-template-columns:1fr;gap:14px;margin-top:24px}
@media (min-width:560px){.roster{grid-template-columns:repeat(2,1fr)}}
@media (min-width:900px){.roster{grid-template-columns:repeat(3,1fr);gap:18px}}
.jersey{border:1px solid var(--line);background:var(--card);padding:18px;display:flex;
  flex-direction:column;gap:8px;position:relative;border-radius:6px;box-shadow:0 1px 3px rgba(20,20,10,.05)}
.jersey .no{font-family:'IBM Plex Mono',monospace;font-size:.7rem;color:var(--gray);letter-spacing:.1em}
.logo-wrap{width:56px;height:56px;display:flex;align-items:center;justify-content:center;margin:2px 0 4px}
.logo-wrap img{max-width:100%;max-height:100%;object-fit:contain}
.logo-wrap.placeholder{background:var(--paper);border:1px dashed var(--line);border-radius:50%;
  color:var(--gray);font-weight:700;font-size:1.3rem;font-family:'Oswald',sans-serif}
.jersey h3{margin:0;font-size:1.02rem}
.jersey h3 a{color:var(--ink);text-decoration:none}
.jersey h3 a:hover{color:var(--teal-dark)}
.jersey .mascot{color:var(--gray);font-family:'IBM Plex Mono',monospace;font-size:.72rem;
  text-transform:uppercase;letter-spacing:.07em}
.jersey .city{color:var(--teal-dark);font-family:'IBM Plex Mono',monospace;font-size:.68rem;
  text-transform:uppercase;letter-spacing:.05em;margin-top:-4px}
.jersey a.store{color:var(--teal-dark);text-decoration:none;font-family:'Oswald',sans-serif;
  text-transform:uppercase;font-size:.8rem;letter-spacing:.04em;border-top:1px solid var(--line);
  padding-top:10px;margin-top:auto;display:block}
.jersey a.store:hover{color:var(--gold-dark)}
.jersey .soon{color:var(--gray);font-family:'IBM Plex Mono',monospace;font-size:.7rem;
  text-transform:uppercase;letter-spacing:.07em;border-top:1px solid var(--line);padding-top:10px;
  margin-top:auto;display:block}

/* communities */
.community-list{columns:2;column-gap:10px;margin:22px 0 0;padding:0;list-style:none;max-width:640px}
.community-list li{break-inside:avoid;margin-bottom:8px}
.community-list a{display:block;text-align:center;background:var(--gold);color:var(--ink);
  font-family:'Oswald',sans-serif;text-transform:uppercase;letter-spacing:.05em;font-weight:600;
  font-size:.78rem;padding:9px 14px;border-radius:3px;text-decoration:none;border:2px solid var(--gold)}
.community-list a:hover{background:var(--gold-dark);border-color:var(--gold-dark)}
@media (min-width:480px){.community-list{columns:3}}
@media (min-width:700px){.community-list{columns:4}}

/* faq */
.faq-item{border-bottom:1px solid var(--line);padding:18px 0}
.faq-item h2{margin:0 0 8px;font-size:1.02rem;font-family:'Inter',sans-serif;
  text-transform:none;letter-spacing:0;font-weight:700;color:var(--teal-dark)}
.faq-item p{margin:0;color:#3a3d44}

/* cta band */
.cta-band{border-top:3px solid var(--gold);border-bottom:1px solid var(--line);
  background:var(--surface);padding:34px 0}
.cta-band .wrap{display:flex;flex-direction:column;gap:16px}
.cta-band h2{margin:0 0 6px}
.cta-band p{margin:0;color:var(--gray);max-width:520px}
.cta-band .btn{flex:1 1 100%}
@media (min-width:480px){.cta-band .btn{flex:0 0 auto}}
@media (min-width:700px){.cta-band{padding:48px 0}.cta-band .wrap{flex-direction:row;justify-content:space-between;align-items:center}}

/* note strip -- reuses the cta-band pattern with a teal accent, so it
   reads as the same component family as the "don't see your school" band */
.cta-band.alt{background:var(--paper);border-top:3px solid var(--teal);border-bottom:1px solid var(--line)}

/* footer */
footer{border-top:1px solid var(--line);padding:34px 0 24px;background:var(--surface)}
footer .wrap{display:flex;flex-direction:column;gap:26px}
footer .cols{display:flex;flex-direction:column;gap:22px}
footer h4{font-family:'IBM Plex Mono',monospace;font-size:.7rem;letter-spacing:.12em;
  text-transform:uppercase;color:var(--gray);margin:0 0 10px}
footer a{display:block;color:var(--ink);text-decoration:none;font-size:.9rem;margin-bottom:8px}
footer a:hover{color:var(--teal-dark)}
.social{display:flex;gap:12px;margin-top:12px}
.social a{width:32px;height:32px;border:1px solid var(--line);display:flex;align-items:center;
  justify-content:center;border-radius:50%;color:var(--ink)}
.fineprint{margin-top:22px;padding-top:18px;border-top:1px solid var(--line);
  font-family:'IBM Plex Mono',monospace;font-size:.68rem;color:var(--gray)}
@media (min-width:700px){footer .wrap{flex-direction:row;justify-content:space-between}
  footer .cols{flex-direction:row;gap:48px}}

/* contact */
.contact-card{border:1px solid var(--line);background:var(--card);padding:22px;
  border-radius:6px;box-shadow:0 1px 3px rgba(20,20,10,.05)}
.contact-card ul{margin:0 0 20px;padding-left:20px;color:#3a3d44}
.contact-card li{margin-bottom:8px}
@media (min-width:700px){.contact-card{padding:34px}}
.contact-grid{display:grid;grid-template-columns:1fr;gap:20px;align-items:start}
@media (min-width:900px){.contact-grid{grid-template-columns:5fr 7fr;gap:28px}}
.contact-form-card{border:1px solid var(--line);background:var(--card);border-radius:6px;
  box-shadow:0 1px 3px rgba(20,20,10,.05);padding:22px}
@media (min-width:700px){.contact-form-card{padding:34px}}
.form-row{margin-bottom:16px}
.form-row label{display:block;font-family:'IBM Plex Mono',monospace;font-size:.72rem;
  letter-spacing:.06em;text-transform:uppercase;color:var(--gray);margin-bottom:6px}
.form-row input,.form-row textarea{width:100%;box-sizing:border-box;border:1px solid var(--line);
  border-radius:3px;padding:11px 12px;font-family:'Inter',sans-serif;font-size:.95rem;
  color:var(--ink);background:var(--paper)}
.form-row input:focus,.form-row textarea:focus{outline:none;border-color:var(--teal-dark);
  box-shadow:0 0 0 3px rgba(0,142,169,.15)}
.form-row textarea{resize:vertical;min-height:120px}
.hp-field{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}
.form-status{margin:14px 0 0;font-size:.9rem;min-height:1.2em}
.form-status.success{color:var(--teal-dark);font-weight:600}
.form-status.error{color:#b3261e;font-weight:600}
#cf-submit{border:none;cursor:pointer}
#cf-submit:disabled{opacity:.6;cursor:not-allowed}
"""

BADGE_IMG = '<img class="badge" src="/assets/logo.png" alt="Iowa On Demand logo" width="40" height="40" loading="eager">'

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
def breadcrumb_schema(crumbs):
    """crumbs: list of (label, path) tuples after Home, e.g.
    [("Schools", "/schools/"), ("North Polk", "/schools/north-polk/")]"""
    items = [{"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"}]
    for i, (label, path) in enumerate(crumbs, start=2):
        items.append({"@type": "ListItem", "position": i, "name": label, "item": BASE + path})
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}

PM_ADDRESS = {
    "@type": "PostalAddress",
    "streetAddress": "1100 South 5th St",
    "addressLocality": "Polk City",
    "addressRegion": "IA",
    "postalCode": "50226",
    "addressCountry": "US",
}

ORG_SCHEMA = {
    "@context": "https://schema.org",
    "@type": ["Organization", "LocalBusiness"],
    "name": "Iowa On Demand",
    "url": BASE + "/",
    "email": EMAIL,
    "logo": BASE + "/assets/logo.png",
    "dateModified": TODAY,
    "address": PM_ADDRESS,
    "parentOrganization": {"@type": "Organization", "name": "P&M Apparel", "url": PM_URL},
    "sameAs": [FB_URL, IG_URL],
    "areaServed": [{"@type": "City", "name": f"{c}, Iowa"} for c in COMMUNITIES],
    "description": "Print-on-demand spirit wear stores for Iowa schools, produced in Polk City, Iowa.",
    "member": [
        {
            "@type": "EducationalOrganization",
            "name": s["name"],
            "url": s["chipply"] if s["chipply"] else BASE + "/schools/",
            "areaServed": [{"@type": "City", "name": f"{c}, Iowa"} for c in s["cities"]],
        } for s in SCHOOLS
    ],
}

def page(path, crumbs, meta_title, meta_desc, body_html, extra_schema=None):
    schemas = [ORG_SCHEMA, breadcrumb_schema(crumbs)]
    if extra_schema:
        schemas.append(extra_schema)
    schema_tags = "\n".join(
        f'<script type="application/ld+json">{json.dumps(s)}</script>' for s in schemas
    )
    nav_html = "\n".join(
        f'<a href="{href}">{text}</a>' for href, text in NAV_ITEMS
    )
    canonical = BASE + path
    if not crumbs:
        breadcrumb_html = ""
    else:
        crumb_items = "\n".join(
            f'<li><a href="{p}">{l}</a></li>' if i < len(crumbs) else f'<li aria-current="page">{l}</li>'
            for i, (l, p) in enumerate(crumbs, start=1)
        )
        breadcrumb_html = f'''<div class="wrap breadcrumb">
    <nav aria-label="Breadcrumb"><ol>
      <li><a href="/">Home</a></li>
      {crumb_items}
    </ol></nav>
  </div>'''
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-ZJZ325GQXS"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-ZJZ325GQXS');
</script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{meta_title}</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32.png">
<link rel="icon" type="image/png" sizes="64x64" href="/assets/favicon-64.png">
<link rel="apple-touch-icon" href="/assets/favicon-180.png">
<meta name="theme-color" content="#ffffff">
<meta property="og:image" content="{BASE}/assets/logo.png">
<meta property="og:image:width" content="817">
<meta property="og:image:height" content="817">
<meta property="og:title" content="{meta_title}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Iowa On Demand">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{meta_title}">
<meta name="twitter:description" content="{meta_desc}">
<meta name="twitter:image" content="{BASE}/assets/logo.png">
{FONT_LINKS}
<style>{CSS}</style>
{schema_tags}
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site">
  <div class="wrap nav">
    <a class="wordmark" href="/">
      {BADGE_IMG}
      <span class="wordmark-text">Iowa On Demand<span>a division of P&amp;M Apparel</span></span>
    </a>
    <nav class="links" aria-label="Primary">
      {nav_html}
      <a class="btn" href="/schools/">Shop Your School</a>
    </nav>
  </div>
</header>
<div class="stat-bar">
  <div class="stat-grid">
    <div>12 Schools Partnered</div>
    <div>3&ndash;5 Day Turnaround</div>
    <div>Zero Setup Cost</div>
    <div>Printed in Polk City, Iowa</div>
  </div>
</div>
{breadcrumb_html}
<main id="main">
{body_html}
</main>
<footer>
  <div class="wrap">
    <div>
      <a class="wordmark" href="/" style="margin-bottom:14px">
        {BADGE_IMG}
        <span class="wordmark-text">Iowa On Demand</span>
      </a>
      <p style="max-width:280px;color:var(--gray);font-size:.9rem">Print-on-demand spirit wear for Iowa schools. A division of {ext(PM_URL, "P&amp;M Apparel")}, Polk City, Iowa.</p>
      <div class="social">
        {ext(FB_URL, "f", aria_label="Iowa On Demand on Facebook")}
        {ext(IG_URL, "ig", aria_label="Iowa On Demand on Instagram")}
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
        {ext(JOTFORM_URL, "Add your school")}
        {ext(PM_URL, "pmapparel.com")}
      </div>
    </div>
  </div>
  <div class="wrap fineprint">Updated {UPDATED_HUMAN} &middot; &copy; {datetime.date.today().year} Iowa On Demand, a division of P&amp;M Apparel</div>
</footer>
</body>
</html>"""


# ---------------------------------------------------------------------------
# SHARED: roster / jersey card
# ---------------------------------------------------------------------------
def jersey_card(s):
    i = SCHOOL_INDEX[s["name"]]
    slug = SCHOOL_SLUGS[s["name"]]
    if s.get("logo"):
        visual = f'<div class="logo-wrap"><img src="{s["logo"]}" alt="{s["name"]} {s["mascot"]} logo" width="56" height="56" loading="lazy"></div>'
    else:
        visual = f'<div class="logo-wrap placeholder" aria-hidden="true">{s["name"][0]}</div>'
    if s["chipply"]:
        action = ext(s["chipply"], "Shop the store &rarr;", cls="store")
    else:
        action = '<span class="soon">Store opening soon</span>'
    return f'''<div class="jersey"><span class="no">{i:02d}</span>{visual}<h3><a href="/schools/{slug}/">{s["name"]}</a></h3>
    <span class="mascot">{s["mascot"]}</span><span class="city">{city_display(s["cities"])}</span>{action}</div>'''


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
    preview_html = "\n".join(jersey_card(s) for s in live_schools)
    def community_href(c):
        schools_here = SCHOOLS_BY_COMMUNITY[c]
        if len(schools_here) == 1:
            return f'/schools/{SCHOOL_SLUGS[schools_here[0]["name"]]}/'
        return "/schools/"  # multiple schools serve this city -- send to the full roster

    chips_html = "\n".join(
        f'<li><a href="{community_href(c)}">{c}</a></li>' for c in COMMUNITIES
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

<section class="section">
  <div class="wrap">
    <span class="eyebrow">Where We Show Up</span>
    <h2>Communities we serve.</h2>
    <p style="max-width:640px">Iowa On Demand partners with schools across the Des Moines metro and central Iowa. Tap a city to see the schools we serve there.</p>
    <ul class="community-list">
      {chips_html}
    </ul>
  </div>
</section>

<section class="cta-band">
  <div class="wrap">
    <div>
      <h2>Don't see your school?</h2>
      <p>Adding a school is quick and there's no cost to get set up. Tell us about your school and we'll take it from there.</p>
    </div>
    {ext(JOTFORM_URL, "Add Your School", cls="btn")}
  </div>
</section>

<section class="cta-band alt">
  <div class="wrap">
    <div>
      <h2>Need more than spirit wear?</h2>
      <p>For custom screen printing, embroidery, promotional products, and event apparel for local businesses, our parent company {ext(PM_URL, "P&amp;M Apparel")} has you covered.</p>
    </div>
    {ext(PM_URL, "Visit P&amp;M Apparel", cls="btn ghost")}
  </div>
</section>
"""

def schools_body():
    cards_html = "\n".join(jersey_card(s) for s in SCHOOLS)
    return f"""
<section class="hero" style="padding-bottom:24px">
  <div class="wrap">
    <span class="eyebrow">Our Partnered Schools</span>
    <h1>Shop your school.</h1>
    <p class="lead">Twelve Iowa schools, twelve dedicated stores, serving families from Ankeny and Johnston to Grimes, Bondurant, Perry, and the Des Moines metro. Pick yours below to shop spirit wear, team gear, and fundraiser apparel, printed on demand.</p>
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
    {ext(JOTFORM_URL, "Add Your School", cls="btn")}
  </div>
</section>
"""

def faq_body():
    items = "\n".join(
        f'<div class="faq-item"><h2>{q}</h2><p>{a}</p></div>' for q, a in FAQS
    )
    return f"""
<section class="hero" style="padding-bottom:16px">
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
    <div class="contact-grid">
      <div class="contact-card">
        <h3 style="text-transform:none;font-family:'Inter',sans-serif;font-size:1.15rem;color:var(--ink)">Why reach out?</h3>
        <ul>
          <li>Partner with us for your school's custom apparel.</li>
          <li>Set up a dedicated online store for students, parents, and staff.</li>
          <li>Ask about our process, products, or anything else.</li>
        </ul>
        <p style="color:var(--gray);font-size:.92rem">We're here to help your school shine with custom, on-demand gear made in Iowa.</p>
        <p style="margin-top:18px;font-size:.9rem">Prefer email? Reach us directly at <a href="mailto:{EMAIL}">{EMAIL}</a></p>
      </div>
      <div class="contact-form-card">
        <form id="contact-form" novalidate>
          <div class="form-row">
            <label for="cf-name">Name</label>
            <input type="text" id="cf-name" name="name" autocomplete="name" required>
          </div>
          <div class="form-row">
            <label for="cf-email">Email</label>
            <input type="email" id="cf-email" name="email" autocomplete="email" required>
          </div>
          <div class="form-row">
            <label for="cf-school">School <span style="text-transform:none">(optional)</span></label>
            <input type="text" id="cf-school" name="school" autocomplete="organization">
          </div>
          <div class="form-row">
            <label for="cf-message">Message</label>
            <textarea id="cf-message" name="message" rows="5" required></textarea>
          </div>
          <div class="hp-field" aria-hidden="true">
            <label for="cf-company">Leave this field blank</label>
            <input type="text" id="cf-company" name="company" tabindex="-1" autocomplete="off">
          </div>
          <button type="submit" class="btn" id="cf-submit">Send Message</button>
          <p class="form-status" id="cf-status" role="status" aria-live="polite"></p>
        </form>
      </div>
    </div>
  </div>
</section>
<script>
(function(){{
  var form = document.getElementById('contact-form');
  if (!form) return;
  var status = document.getElementById('cf-status');
  var btn = document.getElementById('cf-submit');
  form.addEventListener('submit', function(e){{
    e.preventDefault();
    status.textContent = '';
    status.className = 'form-status';
    var payload = {{
      name: form.name.value.trim(),
      email: form.email.value.trim(),
      school: form.school.value.trim(),
      message: form.message.value.trim(),
      company: form.company.value
    }};
    btn.disabled = true;
    btn.textContent = 'Sending...';
    fetch('/api/contact', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(payload)
    }}).then(function(r){{
      return r.json().catch(function(){{ return {{}}; }}).then(function(j){{ return {{ok: r.ok, body: j}}; }});
    }}).then(function(res){{
      if (res.ok) {{
        form.reset();
        status.textContent = "Thanks \u2013 we'll be in touch shortly.";
        status.className = 'form-status success';
      }} else {{
        status.textContent = (res.body && res.body.error) || 'Something went wrong. Please try again or email us directly at {EMAIL}.';
        status.className = 'form-status error';
      }}
    }}).catch(function(){{
      status.textContent = 'Something went wrong. Please try again or email us directly at {EMAIL}.';
      status.className = 'form-status error';
    }}).finally(function(){{
      btn.disabled = false;
      btn.textContent = 'Send Message';
    }});
  }});
}})();
</script>
"""

def school_page_body(s):
    cities = city_display(s["cities"])
    if s["chipply"]:
        cta = ext(s["chipply"], f"Shop {s['name']} Gear", cls="btn")
    else:
        cta = ext(JOTFORM_URL, "Get Notified When It's Live", cls="btn")

    if s.get("logo"):
        logo_html = f'<img src="{s["logo"]}" alt="{s["name"]} {s["mascot"]} logo" width="120" height="120" style="width:120px;height:120px;object-fit:contain;flex:none">'
    else:
        logo_html = f'<div class="logo-wrap placeholder" aria-hidden="true" style="width:120px;height:120px;font-size:2.4rem;flex:none">{s["name"][0]}</div>'

    facts = [
        ("No Minimums", "Order one shirt or a hundred. Every piece prints on demand, so there's no bulk requirement."),
        ("3&ndash;5 Day Turnaround", "Produced locally in Polk City, Iowa, so orders move fast."),
        ("Zero Setup Cost", "Free to launch and free to run. We build and manage the store."),
    ]
    facts_html = "\n".join(f'<div class="feature"><h3>{t}</h3><p>{d}</p></div>' for t, d in facts)

    others = [o for o in SCHOOLS if o["name"] != s["name"]]
    shared = [o for o in others if set(o["cities"]) & set(s["cities"])]
    rest = [o for o in others if o not in shared]
    picks = (shared + rest)[:3]
    other_links = "\n".join(
        f'<li><a href="/schools/{SCHOOL_SLUGS[o["name"]]}/">{o["name"]}</a> '
        f'<span class="mascot">{o["mascot"]}</span></li>'
        for o in picks
    )

    return f"""
<section class="hero">
  <div class="wrap">
    <span class="eyebrow">{cities}</span>
    <h1>{s['name']} {s['mascot']}</h1>
    <p class="lead">Shop print-on-demand spirit wear for {s['name']}, serving {cities}. Order anytime, no bulk minimums, printed locally right here in Iowa.</p>
    <div class="ctas">
      {cta}
      <a class="btn ghost" href="/schools/">All Schools</a>
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap" style="display:flex;gap:24px;align-items:center;flex-wrap:wrap">
    {logo_html}
    <div>
      <h2 style="margin-bottom:.2em">Why order through Iowa On Demand</h2>
      <p style="max-width:520px;margin:0">A dedicated {s['name']} store means students, parents, and staff can order {s['mascot'].lower()} gear whenever they want it, not just during a seasonal fundraiser window.</p>
    </div>
  </div>
</section>

<section class="section alt">
  <div class="wrap">
    <div class="facts3">
      {facts_html}
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <span class="eyebrow">Nearby Schools</span>
    <h2>Other schools we serve.</h2>
    <ul style="list-style:none;padding:0;margin:22px 0 0;display:flex;flex-direction:column;gap:10px;max-width:420px">
      {other_links}
    </ul>
    <p style="margin-top:18px"><a href="/schools/">See all 12 partnered schools &rarr;</a></p>
  </div>
</section>

<section class="cta-band">
  <div class="wrap">
    <div>
      <h2>Questions about the {s['name']} store?</h2>
      <p>Check our FAQ or reach out directly, we're happy to help.</p>
    </div>
    <a class="btn" href="/faq/">View FAQ</a>
  </div>
</section>
"""

def school_schema(s):
    slug = SCHOOL_SLUGS[s["name"]]
    return {
        "@context": "https://schema.org",
        "@type": "EducationalOrganization",
        "name": s["name"],
        "url": BASE + f"/schools/{slug}/",
        "sameAs": [s["chipply"]] if s["chipply"] else [],
        "areaServed": [{"@type": "City", "name": f"{c}, Iowa"} for c in s["cities"]],
        "memberOf": {"@type": "Organization", "name": "Iowa On Demand", "url": BASE + "/"},
    }

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
        "crumbs": [],
        "title": "Iowa On Demand | School Spirit Wear for Ankeny, Johnston, Grimes & More",
        "desc": "Iowa On Demand builds print-on-demand spirit wear stores for schools across Ankeny, Johnston, Grimes, Bondurant, Perry, and the Des Moines metro. No minimums, no setup cost, printed locally in Polk City, Iowa.",
        "body": home_body(),
        "schema": None,
    },
    "/schools/": {
        "crumbs": [("Schools", "/schools/")],
        "title": "Partnered Schools in Ankeny, Johnston, Grimes & Central Iowa | Iowa On Demand",
        "desc": "Shop spirit wear for all 12 Iowa On Demand partnered schools, serving Ankeny, Alleman, Polk City, Woodward, Bondurant, Johnston, Grimes, Perry, and Des Moines.",
        "body": schools_body(),
        "schema": None,
    },
    "/faq/": {
        "crumbs": [("FAQ", "/faq/")],
        "title": "FAQ | Iowa On Demand",
        "desc": "Answers to common questions about Iowa On Demand's print-on-demand school apparel program: turnaround times, ordering, custom designs, and more.",
        "body": faq_body(),
        "schema": FAQ_SCHEMA,
    },
    "/contact/": {
        "crumbs": [("Contact", "/contact/")],
        "title": "Contact | Iowa On Demand",
        "desc": "Get in touch with Iowa On Demand to set up a print-on-demand spirit wear store for your Iowa school, or ask a question about an existing order.",
        "body": contact_body(),
        "schema": None,
    },
}

# One dedicated page per school -- /schools/{slug}/ -- so each school can
# rank on its own for "<school> spirit wear" searches instead of competing
# with 11 others on a single shared page.
for _s in SCHOOLS:
    _slug = SCHOOL_SLUGS[_s["name"]]
    _path = f"/schools/{_slug}/"
    PAGES[_path] = {
        "crumbs": [("Schools", "/schools/"), (_s["name"], _path)],
        "title": f"{_s['name']} {_s['mascot']} Spirit Wear | {_s['cities'][0]}, IA | Iowa On Demand",
        "desc": f"Shop {_s['name']} {_s['mascot']} spirit wear from Iowa On Demand, serving {city_display(_s['cities'])}. Order anytime, no bulk minimums, printed locally in Polk City, Iowa.",
        "body": school_page_body(_s),
        "schema": school_schema(_s),
    }

# ---------------------------------------------------------------------------
# BUILD
# ---------------------------------------------------------------------------
def build():
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
    if os.path.exists(root):
        shutil.rmtree(root)
    os.makedirs(root)

    # copy real brand assets (logo + favicons + school mascots)
    src_assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    dst_assets = os.path.join(root, "assets")
    if os.path.isdir(src_assets):
        shutil.copytree(src_assets, dst_assets)

    for path, p in PAGES.items():
        html = page(path, p["crumbs"], p["title"], p["desc"], p["body"], p["schema"])
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
    page_html = {}
    page_ids = {}

    for path in PAGES:
        fp = os.path.join(root, path.strip("/"), "index.html") if path != "/" else os.path.join(root, "index.html")
        if not os.path.exists(fp):
            errors.append(f"MISSING FILE: {fp}")
            continue
        html = open(fp, encoding="utf-8").read()
        page_html[path] = html
        page_ids[path] = set(re.findall(r'\bid="([a-z0-9-]+)"', html))

    # every community must resolve to a school somewhere, and every school's
    # city list must point to a real community -- catches typos/dropped towns
    for c in COMMUNITIES:
        if not SCHOOLS_BY_COMMUNITY.get(c):
            errors.append(f"COMMUNITIES: '{c}' has no school serving it")
    for s in SCHOOLS:
        if not s["cities"]:
            errors.append(f"SCHOOLS: '{s['name']}' has no cities listed")
        for c in s["cities"]:
            if c not in COMMUNITIES:
                errors.append(f"SCHOOLS: '{s['name']}' lists unknown community '{c}'")

    for path, html in page_html.items():
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

        if "\u2014" in html:
            errors.append(f"{path}: em dash found")

        for href in re.findall(r'<a [^>]*href="(/[a-z0-9/_.#-]*)"', html):
            base, _, fragment = href.partition("#")
            if base and "." in base.rsplit("/", 1)[-1]:
                continue  # asset link (favicon, image, etc.), not a page
            clean = base if base.endswith("/") or base == "/" else base + "/"
            if clean not in PAGES and base not in ("/", ""):
                errors.append(f"{path}: internal link to unknown page {href}")
                continue
            if fragment:
                target_page = clean if base else path  # bare "#frag" points at own page
                target_ids = page_ids.get(target_page, set())
                if fragment not in target_ids:
                    errors.append(f"{path}: link to {href} but no id=\"{fragment}\" found on {target_page}")

        # bare same-page fragment links, e.g. href="#ankeny" (no leading slash)
        for fragment in re.findall(r'<a [^>]*href="#([a-z0-9-]+)"', html):
            if fragment not in page_ids.get(path, set()):
                errors.append(f"{path}: link to #{fragment} but no matching id on this page")

        # every external (target=_blank) link must carry rel=noopener for security
        for m in re.finditer(r'<a\s+[^>]*href="(https?://[^"]+)"[^>]*>', html):
            tag = m.group(0)
            if 'target="_blank"' in tag and "noopener" not in tag:
                errors.append(f"{path}: external link missing rel=noopener: {m.group(1)}")

    if errors:
        print("VERIFICATION FAILED:")
        for e in errors:
            print(" -", e)
        raise SystemExit(1)
    print(f"Verification passed. {len(PAGES)} pages built cleanly, {len(COMMUNITIES)} communities all linked correctly.")


if __name__ == "__main__":
    out = build()
    verify(out)
    print(f"Built to {out}")
