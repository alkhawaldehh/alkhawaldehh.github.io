#!/usr/bin/env python3
"""
tex_to_html.py
Parses Main.tex (Hassan's CV) and regenerates the dynamic content
sections of index.html, leaving the CSS/structure untouched.

Sections regenerated:
  - Education
  - Research Interests
  - Publications (Journal Articles + Conference Abstracts)
  - Research Activities (Experimental Campaigns)
  - Teaching & Supervision
  - Academic & Industry Engagements
  - Awards
"""

import re
import sys
from pathlib import Path

# ── helpers ──────────────────────────────────────────────────────────────────

def clean(s: str) -> str:
    """Strip LaTeX markup and normalize whitespace."""
    s = s.strip()
    # Remove comments
    s = re.sub(r'(?<!\\)%.*', '', s)
    # Strip spacing / box commands with arguments before anything else
    s = re.sub(r'\\[hv]space\*?\{[^}]*\}', '', s)
    s = re.sub(r'\\mbox\{([^}]*)\}', r'\1', s)
    s = re.sub(r'\\raisebox\{[^}]*\}\{([^}]*)\}', r'\1', s)
    s = re.sub(r'\\vspace\*?\{[^}]*\}', '', s)
    # \textbf{...} → <strong>...</strong>
    s = re.sub(r'\\textbf\{([^}]*)\}', r'<strong>\1</strong>', s)
    # \textit{...} or \itshape → <em>...</em>
    s = re.sub(r'\\textit\{([^}]*)\}', r'<em>\1</em>', s)
    s = re.sub(r'\{\\itshape ([^}]*)\}', r'<em>\1</em>', s)
    # \emph{...}
    s = re.sub(r'\\emph\{([^}]*)\}', r'<em>\1</em>', s)
    # \href{url}{text}
    s = re.sub(r'\\href\{([^}]*)\}\{([^}]*)\}', r'<a href="\1">\2</a>', s)
    # math mode (simple): $...$ → keep inner text
    s = re.sub(r'\$([^$]*)\$', lambda m: m.group(1).replace('\\sim', '~').replace('\\!', '').replace('{,}', ','), s)
    # common LaTeX escapes
    s = s.replace('\\%', '%').replace('\\&', '&amp;').replace("\\'", "'")
    s = s.replace('\\textsc{', '').replace('---', '—').replace('--', '–')
    s = s.replace('``', '"').replace("''", '"')
    # remove leftover braces
    s = re.sub(r'(?<!\\)\{([^{}]*)\}', r'\1', s)
    s = re.sub(r'(?<!\\)\{([^{}]*)\}', r'\1', s)  # second pass
    s = re.sub(r'[{}]', '', s)
    # collapse whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def author_highlight(s: str, name_pattern=r'H\.\s*Al\s*Khawaldeh') -> str:
    """Wrap the author's name in <span class="pub-me">.</span>"""
    return re.sub(name_pattern, r'<span class="pub-me">\g<0></span>', s)


def venue_highlight(s: str) -> str:
    """Wrap content of \\textit{...} that looks like a venue."""
    return re.sub(r'<em>([^<]*)</em>', r'<em class="pub-venue">\1</em>', s, count=1)


# ── section parsers ───────────────────────────────────────────────────────────

def extract_args(tex: str, n: int) -> list[str]:
    """Extract the next n brace-delimited arguments from tex, handling nesting."""
    args = []
    i = 0
    tex = tex.lstrip()
    for _ in range(n):
        if i >= len(tex) or tex[i] != '{':
            # skip whitespace/newlines between args
            while i < len(tex) and tex[i] in ' \t\n\r':
                i += 1
        if i >= len(tex):
            break
        if tex[i] != '{':
            break
        depth = 0
        start = i + 1
        while i < len(tex):
            if tex[i] == '{':
                depth += 1
            elif tex[i] == '}':
                depth -= 1
                if depth == 0:
                    args.append(tex[start:i])
                    i += 1
                    # skip whitespace between args
                    while i < len(tex) and tex[i] in ' \t\n\r':
                        i += 1
                    break
            i += 1
    return args


def parse_education(tex: str) -> str:
    blocks = []

    # Find \EducationEntry in the document body (after \begin{document})
    body_start = tex.find(r'\begin{document}')
    body = tex[body_start:] if body_start != -1 else tex

    phd_idx = body.find(r'\EducationEntry')
    if phd_idx != -1:
        after = body[phd_idx + len(r'\EducationEntry'):]
        args = extract_args(after, 5)
        if len(args) >= 5:
            years, degree, school, diss, advisor = [clean(a) for a in args[:5]]
            years = re.sub(r'\\[a-zA-Z]+\s*', '', years).strip()
            blocks.append(f'''
      <div class="edu-card">
        <div class="edu-year">{years}</div>
        <div>
          <div class="edu-degree">{degree}</div>
          <div class="edu-school">{school}</div>
          <div class="edu-detail">Dissertation: {diss}</div>
          <div class="edu-detail">Advisor: {advisor}</div>
        </div>
      </div>''')

    bs_idx = body.find(r'\UndergradEntry')
    if bs_idx != -1:
        after = body[bs_idx + len(r'\UndergradEntry'):]
        args = extract_args(after, 4)
        if len(args) >= 4:
            years, degree, school, minors = [clean(a) for a in args[:4]]
            years = re.sub(r'\\[a-zA-Z]+\s*', '', years).strip()
            blocks.append(f'''
      <div class="edu-card">
        <div class="edu-year">{years}</div>
        <div>
          <div class="edu-degree">{degree}</div>
          <div class="edu-school">{school}</div>
          <div class="edu-detail">Minors: {minors}</div>
        </div>
      </div>''')

    return '\n'.join(blocks)


def parse_research_interests(tex: str) -> str:
    m = re.search(r'\\CVSection\{Research Interest\}(.*?)\\CVSection\{', tex, re.DOTALL)
    if not m:
        return ''
    block = m.group(1)
    item = re.search(r'\\CVItem\{Topics\}\{(.*?)\}', block, re.DOTALL)
    if not item:
        return ''
    raw = clean(item.group(1))
    # Split on semicolons to get individual topics
    topics = [t.strip() for t in raw.split(';') if t.strip()]
    tags = ''.join(f'<span class="rtag">{t}</span>\n        ' for t in topics)
    return f'<div class="tag-cloud">\n        {tags}</div>'


def parse_publications(tex: str, section_title: str) -> list[dict]:
    """Return list of {title, meta} dicts for a publication section."""
    escaped = re.escape(section_title)
    m = re.search(rf'\\CVSection\{{{escaped}\}}(.*?)\\CVSection\{{', tex, re.DOTALL)
    if not m:
        return []
    block = m.group(1)

    pubs = []
    for item_m in re.finditer(r'\\CVItem\s*', block):
        pos = item_m.end()
        args = extract_args(block[pos:], 2)
        if len(args) < 2:
            continue
        num, body = args[0], args[1]
        body = body.strip()
        # Title is inside ``...''
        title_m = re.search(r'``(.*?)\'\'', body, re.DOTALL)
        if not title_m:
            title_m_alt = re.match(r'(.*?)[,\.]\s', body)
            title = clean(title_m_alt.group(1)) if title_m_alt else clean(body[:120])
        else:
            title = clean(title_m.group(1))
        meta = clean(body)
        meta = author_highlight(meta)
        meta = re.sub(r'<em>([^<]+)</em>', r'<span class="pub-venue">\1</span>', meta)
        pubs.append({'num': num.strip(), 'title': title, 'meta': meta})
    return pubs


def render_pub_section(pubs: list[dict]) -> str:
    items = []
    for p in pubs:
        items.append(f'''
      <div class="pub-item">
        <div class="pub-title">{p["title"]}</div>
        <div class="pub-meta">{p["meta"]}</div>
      </div>''')
    return '\n'.join(items)


def parse_cvitems_with_bullets(tex: str, section_title: str) -> list[dict]:
    """Parse \\CVItem entries that contain \\begin{{itemize}} bullet lists."""
    escaped = re.escape(section_title)
    m = re.search(rf'\\CVSection\{{{escaped}\}}(.*?)(?=\\CVSection\{{|\Z)', tex, re.DOTALL)
    if not m:
        return []
    block = m.group(1)

    results = []
    for item_m in re.finditer(r'\\CVItem\s*', block):
        pos = item_m.end()
        args = extract_args(block[pos:], 2)
        if len(args) < 2:
            continue
        date_raw, body_raw = args[0], args[1]

        date = clean(date_raw)
        date = re.sub(r'\\[hv]space\s*\{[^}]*\}', '', date)
        date = re.sub(r'\\mbox\s*', '', date)
        # strip any remaining backslash commands
        date = re.sub(r'\\[a-zA-Z]+', '', date).strip()

        # Bold title
        title_m = re.search(r'\\textbf\{([^}]*)\}', body_raw)
        title = clean(title_m.group(1)) if title_m else ''

        # Organisation line
        org_m = re.search(r'\\textbf\{[^}]*\}\s*,?\s*([^\n\\]*?)(?=\\begin\{itemize\}|$)',
                          body_raw, re.DOTALL)
        org = clean(org_m.group(1)) if org_m else ''

        # Bullet items
        bullets_m = re.search(r'\\begin\{itemize\}(.*?)\\end\{itemize\}', body_raw, re.DOTALL)
        bullets = []
        if bullets_m:
            raw_items = re.findall(r'\\item\s+(.*?)(?=\\item|\\end\{itemize\}|\Z)',
                                   bullets_m.group(1), re.DOTALL)
            for ri in raw_items:
                bullets.append(clean(ri))

        results.append({'date': date, 'title': title, 'org': org, 'bullets': bullets})
    return results


def render_exp_cards(entries: list[dict]) -> str:
    cards = []
    for e in entries:
        bullets_html = ''.join(f'<li>{b}</li>\n          ' for b in e['bullets'])
        cards.append(f'''
      <div class="exp-card">
        <div class="exp-header">
          <div class="exp-role">{e["title"]}</div>
          <span class="exp-date">{e["date"]}</span>
        </div>
        <div class="exp-org">{e["org"]}</div>
        <ul class="exp-bullets">
          {bullets_html}
        </ul>
      </div>''')
    return '\n'.join(cards)


def parse_awards(tex: str) -> str:
    m = re.search(r'\\CVSection\{Awards\}(.*?)(?=\\CVSection\{|\\end\{document\})', tex, re.DOTALL)
    if not m:
        return ''
    block = m.group(1)
    cards = []
    for item_m in re.finditer(r'\\CVItem\s*', block):
        pos = item_m.end()
        args = extract_args(block[pos:], 2)
        if len(args) < 2:
            continue
        date_raw, body = args[0], args[1]
        year_m = re.search(r'\d{4}', date_raw)
        year = year_m.group() if year_m else date_raw.strip()
        text = clean(body)
        cards.append(f'''
      <div class="award-card">
        <span class="award-year-badge">{year}</span>
        <div class="award-text">{text}</div>
      </div>''')
    return '\n'.join(cards)


# ── count stats ───────────────────────────────────────────────────────────────

def count_pubs(tex: str) -> dict:
    journal_m = re.search(r'\\CVSection\{Publications: Journal Articles\}(.*?)\\CVSection\{',
                          tex, re.DOTALL)
    conf_m = re.search(r'\\CVSection\{Publications: Refereed Conference Abstracts\}(.*?)\\CVSection\{',
                       tex, re.DOTALL)
    journals = len(re.findall(r'\\CVItem', journal_m.group(1))) if journal_m else 0
    confs = len(re.findall(r'\\CVItem', conf_m.group(1))) if conf_m else 0
    campaigns_m = re.search(r'Collaborative Experimental Campaigns(.*?)(?=\\CVSection\{|\Z)', tex, re.DOTALL)
    campaigns = len(re.findall(r'\\CVItem', campaigns_m.group(1))) if campaigns_m else 0
    return {'journals': journals, 'confs': confs, 'total': journals + confs, 'campaigns': campaigns}


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    tex_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('Main.tex')
    html_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('index.html')

    tex = tex_path.read_text(encoding='utf-8')
    html = html_path.read_text(encoding='utf-8')

    # ── Education ──
    edu_html = parse_education(tex)
    def replace_section(tag, content, h):
        return re.sub(
            rf'(<!-- GEN:{tag} -->)(.*?)(<!-- /GEN:{tag} -->)',
            lambda m: m.group(1) + '\n' + content + '\n      ' + m.group(3),
            h, flags=re.DOTALL)

    html = replace_section('education', edu_html, html)

    ri_html = parse_research_interests(tex)
    html = replace_section('research-interests', ri_html, html)

    j_pubs = parse_publications(tex, 'Publications: Journal Articles')
    j_html = render_pub_section(j_pubs)
    html = replace_section('pub-journals', j_html, html)

    c_pubs = parse_publications(tex, 'Publications: Refereed Conference Abstracts')
    c_html = render_pub_section(c_pubs)
    html = replace_section('pub-conferences', c_html, html)

    camp_entries = parse_cvitems_with_bullets(tex, 'Research Activities')
    camp_html = render_exp_cards(camp_entries)
    html = replace_section('campaigns', camp_html, html)

    teach_entries = parse_cvitems_with_bullets(tex, 'Teaching and Supervision')
    teach_html = render_exp_cards(teach_entries)
    html = replace_section('teaching', teach_html, html)

    ind_entries = parse_cvitems_with_bullets(tex, 'Academic and Industry Engagements')
    ind_html = render_exp_cards(ind_entries)
    html = replace_section('industry', ind_html, html)

    awards_html = parse_awards(tex)
    html = replace_section('awards', awards_html, html)

    stats = count_pubs(tex)
    html = re.sub(r'(<!-- GEN:stat-journals -->)(.*?)(<!-- /GEN:stat-journals -->)',
                  lambda m, s=stats: m.group(1) + str(s['journals']) + m.group(3), html, flags=re.DOTALL)
    html = re.sub(r'(<!-- GEN:stat-total-pubs -->)(.*?)(<!-- /GEN:stat-total-pubs -->)',
                  lambda m, s=stats: m.group(1) + str(s['total']) + m.group(3), html, flags=re.DOTALL)
    html = re.sub(r'(<!-- GEN:stat-campaigns -->)(.*?)(<!-- /GEN:stat-campaigns -->)',
                  lambda m, s=stats: m.group(1) + str(s['campaigns']) + m.group(3), html, flags=re.DOTALL)

    html_path.write_text(html, encoding='utf-8')
    print(f"✓ index.html regenerated from {tex_path}")
    print(f"  {stats['journals']} journal articles · {stats['confs']} conference papers · {stats['campaigns']} campaigns")


if __name__ == '__main__':
    main()
