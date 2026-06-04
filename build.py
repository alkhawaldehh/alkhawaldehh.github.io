"""
build.py — regenerate index.html from CV_file.tex

Usage:
    python3 build.py

Place this file in the same folder as CV_file.tex and index.html.
Run it every time you update your CV. Then commit and push index.html to GitHub.

Adding a new section to CV_file.tex will automatically appear on the website.
"""

import re

CV_FILE    = 'CV_file.tex'
INDEX_FILE = 'index.html'

with open(CV_FILE, 'r') as f:
    tex = f.read()

# ── HELPERS ────────────────────────────────────────────────────────────────

def clean(s):
    if not s: return ''
    s = re.sub(r'%[^\n]*', '', s)
    s = re.sub(r'\\textbf\{([^}]*)\}', r'<strong>\1</strong>', s)
    s = re.sub(r'\\textit\{([^}]*)\}', r'<em>\1</em>', s)
    s = re.sub(r'\\emph\{([^}]*)\}',   r'<em>\1</em>', s)
    s = re.sub(r'\\textsc\{([^}]*)\}', r'\1', s)
    s = re.sub(r'\\href\{[^}]*\}\{([^}]*)\}', r'\1', s)
    s = re.sub(r'\\itshape\s*', '', s)
    s = re.sub(r'\\color\{[^}]*\}', '', s)
    def fix_math(m):
        t = m.group().strip('$')
        t = re.sub(r'\\sim\\!?', '~', t)
        t = re.sub(r'\\mu\s*', 'μ', t)
        t = re.sub(r'\\times', '×', t)
        t = re.sub(r'\\infty', '∞', t)
        t = re.sub(r'\^\{?2\}?', '²', t)
        t = re.sub(r'\{([^}]*)\}', r'\1', t)
        return re.sub(r'\\[a-zA-Z]+\s*', '', t).strip()
    s = re.sub(r'\$[^$]+\$', fix_math, s)
    s = s.replace('``', '\u201c').replace("''", '\u201d')
    s = s.replace('\\&', '&amp;').replace('\\%', '%')
    s = re.sub(r'---', '—', s)
    s = re.sub(r'--', '–', s)
    s = s.replace('~', '\u00a0')
    s = re.sub(r'\{,\}', ',', s)
    s = re.sub(r'\\mbox\{([^}]*)\}', r'\1', s)
    s = re.sub(r'\\hspace\{[^}]*\}', '', s)
    s = re.sub(r'\\vspace\{[^}]*\}', '', s)
    s = re.sub(r'\\[a-zA-Z]+\s*', ' ', s)
    s = re.sub(r'[{}]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def hl(text):
    """Highlight author name in amber."""
    return re.sub(r'(H\.\s*Al\s*Khawaldeh)', r'<span class="pub-me">\1</span>', text)

def brace_arg(s):
    """Extract first brace-balanced {arg} from s. Returns (content, rest)."""
    s = s.lstrip()
    if not s or s[0] != '{': return None, s
    depth = 0
    for i, c in enumerate(s):
        if c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0: return s[1:i], s[i+1:]
    return None, s

def extract_bullets(block):
    m = re.search(r'\\begin\{itemize\}([\s\S]*?)\\end\{itemize\}', block)
    if not m: return []
    return [clean(b) for b in re.split(r'\\item\s+', m.group(1)) if b.strip()]

def section_slug(name):
    """Convert a section name to a safe HTML id."""
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

# ── DISCOVER ALL SECTIONS IN CV ORDER ─────────────────────────────────────

doc_start = tex.find(r'\begin{document}')
doc = tex[doc_start:] if doc_start != -1 else tex

# Find all \CVSection{Name} in document order, skipping commented-out ones
all_sections = []  # list of (name, start_pos, end_pos) in doc
for m in re.finditer(r'^[^%\n]*\\CVSection\{([^}]+)\}', doc, re.MULTILINE | re.IGNORECASE):
    all_sections.append((m.group(1).strip(), m.start()))

# Compute end positions
section_blocks = []
for i, (name, start) in enumerate(all_sections):
    end = all_sections[i+1][1] if i+1 < len(all_sections) else len(doc)
    block = doc[start:end]
    section_blocks.append((name, block))

print(f"Found {len(section_blocks)} sections: {[s[0] for s in section_blocks]}")

# ── SECTION PARSERS ────────────────────────────────────────────────────────

def parse_cvitems(block):
    r"""Parse \CVItem{date}{\textbf{title} org \begin{itemize}...} entries."""
    entries, pos = [], 0
    while True:
        m = re.search(r'\\CVItem', block[pos:])
        if not m: break
        pos += m.start() + len(r'\CVItem')
        rest = block[pos:]
        date_raw, rest = brace_arg(rest.lstrip())
        body,     rest = brace_arg(rest.lstrip())
        pos = len(block) - len(rest)
        if not date_raw or not body or '\\textbf' not in body: continue
        date_raw = re.sub(r'\\hspace\{[^}]*\}\\mbox\{([^}]*)\}', r'\1', date_raw)
        date_raw = re.sub(r'\\vspace\{[^}]*\}', '', date_raw)
        date = clean(date_raw)
        title_m = re.search(r'\\textbf\{([^}]*)\}', body)
        title = clean(title_m.group(1)) if title_m else ''
        after = body[title_m.end():] if title_m else body
        org_part = re.split(r'\\begin\{itemize\}', after)[0]
        org = clean(org_part).lstrip(',').strip()
        bullets = extract_bullets(body)
        if title: entries.append({'date': date, 'title': title, 'org': org, 'bullets': bullets})
    return entries

def parse_pub_items(block):
    r"""Parse \CVItem{[N]}{citation text} publication entries."""
    items, pos = [], 0
    while True:
        m = re.search(r'\\CVItem\s*\{(\[[^\]]*\])\}', block[pos:])
        if not m: break
        num = m.group(1)
        pos += m.end()
        rest = block[pos:]
        content, rest = brace_arg(rest.lstrip())
        pos = len(block) - len(rest)
        if content:
            text = clean(content)
            if text: items.append({'num': num, 'text': text})
    return items

def parse_education(block):
    cards = []
    for tag, n, typ in [('\\EducationEntry', 5, 'phd'), ('\\UndergradEntry', 4, 'ug')]:
        pos = 0
        while True:
            idx = block.find(tag, pos)
            if idx == -1: break
            pos = idx + len(tag)
            rest = block[pos:]
            args = []
            for _ in range(n):
                a, rest = brace_arg(rest.lstrip())
                if a is None: break
                args.append(a)
            if len(args) < n: continue
            year_raw = re.sub(r'\\hspace\{[^}]*\}', '', args[0])
            year_raw = re.sub(r'\\mbox\{([^}]*)\}', r'\1', year_raw)
            c = {'year': clean(year_raw), 'degree': clean(args[1]),
                 'institution': clean(args[2]), 'type': typ}
            if typ == 'phd':
                c['dissertation'] = clean(args[3])
                c['advisor'] = clean(args[4]) if len(args) > 4 else ''
            else:
                c['minors'] = clean(args[3])
            cards.append(c)
    return cards

def parse_research(block):
    m = re.search(r'\\CVItem\{Topics\}', block)
    if not m: return []
    content, _ = brace_arg(block[m.end():].lstrip())
    if not content: return []
    raw = re.sub(r'%[^\n]*', '', content)
    return [clean(t) for t in raw.split(';') if t.strip()]

def parse_awards(block):
    awards, pos = [], 0
    while True:
        m = re.search(r'\\CVItem', block[pos:])
        if not m: break
        pos += m.start() + len(r'\CVItem')
        rest = block[pos:]
        date_raw, rest = brace_arg(rest.lstrip())
        body,     rest = brace_arg(rest.lstrip())
        pos = len(block) - len(rest)
        if not date_raw or not body: continue
        year_raw = re.sub(r'\\hspace\{[^}]*\}\\mbox\{([^}]*)\}', r'\1', date_raw)
        year = clean(year_raw)
        text = clean(body)
        if year and text: awards.append({'year': year, 'text': text})
    return awards

# ── DETECT SECTION TYPE ────────────────────────────────────────────────────

def detect_type(name, block):
    """Infer what kind of content a section contains."""
    name_l = name.lower()
    if 'education' in name_l:                        return 'education'
    if 'research interest' in name_l:                return 'research'
    if 'journal' in name_l:                          return 'journals'
    if 'conference' in name_l or 'refereed' in name_l: return 'conferences'
    if 'award' in name_l:                            return 'awards'
    # Generic: check whether it looks like pub items ([1], [2]...) or CVItems
    if re.search(r'\\CVItem\s*\{\[', block):         return 'publications'
    if re.search(r'\\CVItem', block):                return 'cvitems'
    return 'cvitems'

# ── HTML BUILDERS ──────────────────────────────────────────────────────────

def edu_html(cards):
    out = []
    for c in cards:
        yr = c['year']
        out.append(f'''<div class="edu-card">
  <div class="edu-year">{yr}</div>
  <div>
    <div class="edu-degree">{c["degree"]}</div>
    <div class="edu-school">{c["institution"]}</div>
    {"<div class='edu-detail'>Dissertation: " + c.get("dissertation","") + "</div>" if c.get("dissertation") else ""}
    {"<div class='edu-detail'>Advisor: " + c.get("advisor","") + "</div>" if c.get("advisor") else ""}
    {"<div class='edu-detail'>Minors: " + c.get("minors","") + "</div>" if c.get("minors") else ""}
  </div>
</div>''')
    return '\n'.join(out)

def research_html(topics):
    return '<div class="tag-cloud">' + ''.join(f'<span class="rtag">{t}</span>' for t in topics) + '</div>'

def pub_html(item):
    raw = item['text']
    qm = re.search(r'[\u201c"](.*?)[\u201d"]', raw)
    if qm:
        title = qm.group(1).rstrip(' ,')
        meta  = hl((raw[:qm.start()] + raw[qm.end():]).lstrip(' ,').strip())
    else:
        comma = raw.find(',')
        title = raw[:comma] if comma > 0 else raw
        meta  = hl(raw[comma+1:].strip()) if comma > 0 else ''
    return f'<div class="pub-item"><div class="pub-title">{title}</div><div class="pub-meta">{meta}</div></div>'

def pubs_html(items):
    return '\n'.join(pub_html(i) for i in items)

def conferences_grouped_html(items):
    groups = {}
    for i in items:
        yrs = re.findall(r'\b(20\d{2}|19\d{2})\b', i['text'])
        yr = yrs[-1] if yrs else 'Other'
        groups.setdefault(yr, []).append(i)
    out = []
    for yr in sorted(groups.keys(), reverse=True):
        out.append(f'<div class="pub-group-label">{yr}</div>')
        out.extend(pub_html(i) for i in groups[yr])
    return '\n'.join(out)

def exp_html(entries):
    out = []
    for e in entries:
        bullets = ''.join(f'<li>{b}</li>' for b in e['bullets'])
        out.append(f'''<div class="exp-card">
  <div class="exp-header">
    <div class="exp-role">{e["title"]}</div>
    <span class="exp-date">{e["date"]}</span>
  </div>
  <div class="exp-org">{e["org"]}</div>
  {"<ul class='exp-bullets'>" + bullets + "</ul>" if bullets else ""}
</div>''')
    return '\n'.join(out)

def awards_html(awards):
    return '\n'.join(f'''<div class="award-card">
  <span class="award-year-badge">{a["year"]}</span>
  <div class="award-text">{a["text"]}</div>
</div>''' for a in awards)

# ── SECTION ICONS ──────────────────────────────────────────────────────────

ICONS = {
    'education':    '<path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/>',
    'research':     '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
    'journals':     '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    'conferences':  '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 3H8M12 3v4"/>',
    'publications': '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    'awards':       '<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>',
    'cvitems':      '<rect x="2" y="7" width="20" height="15" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/>',
}

def icon_svg(stype):
    paths = ICONS.get(stype, ICONS['cvitems'])
    return f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">{paths}</svg>'

# ── BUILD ALL SECTIONS ─────────────────────────────────────────────────────

# Track counts for stat cards
counts = {}

sections_html = []   # (name, slug, stype, content_html, count)
for name, block in section_blocks:
    slug  = section_slug(name)
    stype = detect_type(name, block)

    if stype == 'education':
        cards = parse_education(block)
        content = edu_html(cards)
        count = len(cards)
    elif stype == 'research':
        topics = parse_research(block)
        content = research_html(topics)
        count = len(topics)
    elif stype == 'journals':
        items = parse_pub_items(block)
        content = pubs_html(items)
        count = len(items)
        counts['journals'] = count
    elif stype == 'conferences':
        items = parse_pub_items(block)
        content = conferences_grouped_html(items)
        count = len(items)
        counts['conferences'] = count
    elif stype == 'publications':
        items = parse_pub_items(block)
        content = pubs_html(items)
        count = len(items)
    elif stype == 'awards':
        items = parse_awards(block)
        content = awards_html(items)
        count = len(items)
    else:  # cvitems (experience, campaigns, teaching, industry, hobbies, etc.)
        entries = parse_cvitems(block)
        content = exp_html(entries)
        count = len(entries)

    counts[slug] = count
    sections_html.append((name, slug, stype, content, count))
    print(f"  {name}: {count} items")

# ── SECTION COUNT BADGE ────────────────────────────────────────────────────

def count_label(name, stype, count):
    if stype == 'journals':     return f'{count} article{"s" if count!=1 else ""}'
    if stype == 'conferences':  return f'{count} abstract{"s" if count!=1 else ""}'
    if stype == 'publications': return f'{count} item{"s" if count!=1 else ""}'
    if stype == 'education':    return ''
    if stype == 'research':     return ''
    if stype == 'awards':       return f'{count} award{"s" if count!=1 else ""}'
    return f'{count} entr{"ies" if count!=1 else "y"}' if count else ''

# ── BUILD NAV HTML ─────────────────────────────────────────────────────────

NAV_GROUP_RULES = {
    # stype -> nav group label (first occurrence sets the group)
    'education':    'Overview',
    'research':     'Overview',
    'journals':     'Publications',
    'conferences':  'Publications',
    'publications': 'Publications',
    'awards':       'Experience',
    'cvitems':      'Experience',
}

def build_nav(sections_html):
    out = []
    current_group = None
    # Always start with About
    out.append('''    <div class="nav-group-label">Overview</div>
    <a href="#about" class="nav-link active">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>About
    </a>''')
    current_group = 'Overview'

    for name, slug, stype, content, count in sections_html:
        group = NAV_GROUP_RULES.get(stype, 'Experience')
        if group != current_group:
            out.append(f'    <div class="nav-group-label">{group}</div>')
            current_group = group
        badge = f'<span class="nav-badge">{count}</span>' if count and stype in ('journals','conferences','publications') else ''
        out.append(f'''    <a href="#{slug}" class="nav-link">
      {icon_svg(stype)}{name}{badge}
    </a>''')
    return '\n'.join(out)

# ── BUILD MAIN SECTIONS HTML ───────────────────────────────────────────────

def build_sections(sections_html):
    out = []
    for name, slug, stype, content, count in sections_html:
        label = count_label(name, stype, count)
        count_span = f'<span class="section-count" id="count-{slug}">{label}</span>' if label else ''
        out.append(f'''    <div class="section" id="{slug}">
      <div class="section-header">
        <div class="section-icon">{icon_svg(stype)}</div>
        <div class="section-title">{name}</div>
        {count_span}
      </div>
      <div id="{slug}-content">
{content}
      </div>
    </div>''')
    return '\n'.join(out)

nav_html    = build_nav(sections_html)
main_html   = build_sections(sections_html)

# ── INJECT INTO index.html ─────────────────────────────────────────────────

with open(INDEX_FILE, 'r') as f:
    html = f.read()

# Replace nav content
nav_start = html.find('<nav>')
nav_end   = html.find('</nav>') + len('</nav>')
if nav_start != -1 and nav_end != -1:
    html = html[:nav_start] + f'<nav>\n{nav_html}\n  </nav>' + html[nav_end:]
else:
    print("WARNING: <nav> block not found in index.html")

# Replace all dynamic sections between the about section and contact section
def find_section_bounds(html, sid):
    """Return (start, end) of <div class="section" id="sid">...</div>"""
    tag = f'<div class="section" id="{sid}">'
    start = html.find(tag)
    if start == -1: return -1, -1
    depth, i = 0, start
    while i < len(html):
        if html[i:i+4] == '<div': depth += 1; i += 4
        elif html[i:i+6] == '</div>':
            depth -= 1
            if depth == 0: return start, i + 6
            i += 6
        else: i += 1
    return start, len(html)

about_start, about_end     = find_section_bounds(html, 'about')
contact_start, contact_end = find_section_bounds(html, 'contact')

if about_end != -1 and contact_start != -1:
    html = html[:about_end] + '\n\n' + main_html + '\n\n    ' + html[contact_start:]
else:
    print("WARNING: could not find about/contact sections — sections not updated")

# Update stat cards (journals / conferences)
j = counts.get('journals', 0)
c = counts.get('conferences', 0)
html = re.sub(r'(<div class="stat-num" id="stat-journals">)[^<]*(</div>)',    f'\\g<1>{j}\\2', html)
html = re.sub(r'(<div class="stat-num" id="stat-conferences">)[^<]*(</div>)', f'\\g<1>{c}\\2', html)
html = re.sub(r'(<span class="nav-badge" id="badge-journals">)[^<]*(</span>)',    f'\\g<1>{j}\\2', html)
html = re.sub(r'(<span class="nav-badge" id="badge-conferences">)[^<]*(</span>)', f'\\g<1>{c}\\2', html)

with open(INDEX_FILE, 'w') as f:
    f.write(html)

print(f"\n✓ {INDEX_FILE} updated with {len(sections_html)} sections.")