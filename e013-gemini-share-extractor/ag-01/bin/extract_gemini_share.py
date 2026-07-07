#!/usr/bin/env python3
"""Extract conversation text from a Gemini share URL.

Outputs:
  - stdout: full conversation as Markdown with turn markers
  - ./output/<id>/: 
      conversation.md - full Markdown
      tables.json      - all tables as JSON array
      tables/           - individual tables as CSV + JSON

Usage:
  ./extract_gemini_share.py https://share.gemini.google/<id>
  echo "https://share.gemini.google/<id>" | ./extract_gemini_share.py

Dependencies: agent-browser (npm install -g agent-browser)
"""

import sys, subprocess, time, json, csv, io, os, re
from pathlib import Path
from html.parser import HTMLParser


EXTRACT_JS = r"""
(() => {
  const turns = Array.from(document.querySelectorAll("share-turn-viewer"));
  const result = [];

  for (const turn of turns) {
    const userEl = turn.querySelector("user-query");
    const respEl = turn.querySelector("response-container message-content");

    let userText = (userEl?.innerText || "").replace(/^You said\s*\n\s*/, "").trim();

    let responseHtml = respEl?.innerHTML || "";

    // Extract tables from response
    const tables = [];
    const tableEls = respEl?.querySelectorAll("table") || [];
    for (const tbl of tableEls) {
      const rows = [];
      const trs = tbl.querySelectorAll("tr");
      for (const tr of trs) {
        const cells = [];
        tr.querySelectorAll("th, td").forEach(cell => cells.push(cell.innerText.trim()));
        if (cells.length) rows.push(cells);
      }
      if (rows.length) tables.push(rows);
    }

    // Extract code blocks
    const codeBlocks = [];
    const preEls = respEl?.querySelectorAll("pre, code") || [];
    for (const el of preEls) {
      const text = el.innerText.trim();
      if (text.length > 40 && !codeBlocks.includes(text)) {
        // Determine language from class if available
        const lang = (el.className || "").match(/language-(\w+)/);
        codeBlocks.push({ language: lang ? lang[1] : "", code: text });
      }
    }

    let responseText = respEl?.innerText?.trim() || "";

    result.push({
      user: userText,
      response: responseText,
      responseHtml: responseHtml,
      tables: tables,
      codeBlocks: codeBlocks
    });
  }

  // Also get title and metadata
  const title = document.title.replace(/\u200e/g, "").trim();

  return JSON.stringify({
    title: title,
    url: location.href,
    turns: result
  });
})();
"""


def run_agent_browser(url):
    t0 = time.time()

    result = subprocess.run(['agent-browser', 'open', url],
                            capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise RuntimeError(f"agent-browser open failed: {result.stderr[:200]}")

    result = subprocess.run(['agent-browser', 'wait', '--load', 'networkidle'],
                            capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"agent-browser wait failed: {result.stderr[:200]}")

    t1 = time.time()

    result = subprocess.run(
        ['agent-browser', 'eval', '--stdin'],
        input=EXTRACT_JS, capture_output=True, text=True, timeout=10
    )
    if result.returncode != 0:
        raise RuntimeError(f"agent-browser eval failed: {result.stderr[:200]}")

    t2 = time.time()

    subprocess.run(['agent-browser', 'close'], capture_output=True, timeout=5)

    raw = result.stdout.strip()
    # agent-browser wraps eval output in an extra JSON string layer
    if raw.startswith('"') and raw.endswith('"'):
        raw = json.loads(raw)
    data = json.loads(raw) if isinstance(raw, str) else raw
    data['_timing'] = {'load': t1 - t0, 'extract': t2 - t1, 'total': t2 - t0}
    return data


def html_to_markdown_simple(html):
    """Convert Gemini response HTML to basic Markdown."""
    result = []
    i = 0
    while i < len(html):
        # Tables
        if html[i:i+6] == '<table':
            end = html.find('</table>', i) + len('</table>')
            result.append('\n' + _table_to_markdown(html[i:end]) + '\n')
            i = end
            continue
        # Code blocks
        if html[i:i+4] == '<pre':
            end = html.find('</pre>', i) + len('</pre>')
            pre_html = html[i:end]
            code_match = re.search(r'<code[^>]*>(.*?)</code>', pre_html, re.DOTALL)
            if code_match:
                code_text = code_match.group(1).strip()
                code_text = re.sub(r'<br\s*/?>', '\n', code_text)
                code_text = re.sub(r'<[^>]+>', '', code_text)
                lang_match = re.search(r'class="[^"]*language-(\w+)"', html[i:end])
                lang = lang_match.group(1) if lang_match else ''
                result.append(f'\n```{lang}\n{code_text}\n```\n')
            i = end
            continue
        # Paragraphs
        if html[i:i+2] == '<p' and html[i+2] in ('>', ' '):
            end = html.find('</p>', i)
            if end != -1:
                inner = _strip_tags(html[html.find('>', i)+1:end]).strip()
                if inner:
                    result.append('\n' + inner + '\n')
                i = end + 4
                continue
        # Bold
        if html[i:i+3] == '<b>':
            end = html.find('</b>', i)
            if end != -1:
                result.append('**' + _strip_tags(html[i+3:end]) + '**')
                i = end + 4
                continue
        # Italic
        if html[i:i+3] == '<i>':
            end = html.find('</i>', i)
            if end != -1:
                result.append('_' + _strip_tags(html[i+3:end]) + '_')
                i = end + 4
                continue
        # Strong
        if html[i:i+4] == '<str' and 'strong' in html[i:i+8]:
            end = html.find('</strong>', i)
            if end != -1:
                result.append('**' + _strip_tags(html[html.find('>', i)+1:end]) + '**')
                i = end + 9
                continue
        # Line breaks
        if html[i:i+4] == '<br>' or html[i:i+5] == '<br />':
            result.append('\n')
            i += 5 if html[i:i+5] == '<br />' else 4
            continue
        # Links
        if html[i:i+2] == '<a ' or html[i:i+3] == '<a>':
            end_tag = html.find('>', i)
            end_a = html.find('</a>', i)
            if end_tag != -1 and end_a != -1:
                href_match = re.search(r'href="([^"]*)"', html[i:end_tag])
                href = href_match.group(1) if href_match else ''
                text = _strip_tags(html[end_tag+1:end_a])
                result.append(f'[{text}]({href})')
                i = end_a + 4
                continue
        # Headers
        heading = re.match(r'<h([2-4])[^>]*>(.*?)</h\1>', html[i:], re.DOTALL)
        if heading:
            level = int(heading.group(1))
            text = _strip_tags(heading.group(2))
            result.append(f'\n{"#" * level} {text}\n')
            i += heading.end()
            continue
        # Ordered list
        if html[i:i+3] == '<ol':
            end_list = html.find('</ol>', i) + 5
            items = re.findall(r'<li[^>]*>(.*?)</li>', html[i:end_list], re.DOTALL)
            for idx, item in enumerate(items):
                item_text = _strip_tags(item).strip()
                if item_text:
                    result.append(f'\n{idx+1}. {item_text}\n')
            i = end_list
            continue
        # Unordered list
        if html[i:i+4] == '<ul ' or html[i:i+4] == '<ul>':
            end_list = html.find('</ul>', i) + 5
            items = re.findall(r'<li[^>]*>(.*?)</li>', html[i:end_list], re.DOTALL)
            for item in items:
                item_text = _strip_tags(item).strip()
                if item_text:
                    result.append(f'\n- {item_text}\n')
            i = end_list
            continue
        # Div (just skip opening/closing)
        if html[i:i+4] == '<div' or html[i:i+5] == '</div':
            end_tag = html.find('>', i)
            if end_tag != -1:
                i = end_tag + 1
                continue
        # Skip other tags
        if html[i] == '<':
            end_tag = html.find('>', i)
            if end_tag != -1:
                i = end_tag + 1
                continue
        # Plain text
        result.append(html[i])
        i += 1

    out = ''.join(result)
    # Collapse multiple newlines
    out = re.sub(r'\n{3,}', '\n\n', out)
    return out.strip()


def _strip_tags(html):
    return re.sub(r'<[^>]+>', '', html)


def _table_to_markdown(table_html):
    """Convert HTML table to Markdown table."""
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
    if not rows:
        return ''

    header = True
    md_rows = []
    for row in rows:
        cells = re.findall(r'<th[^>]*>(.*?)</th>|<td[^>]*>(.*?)</td>', row, re.DOTALL)
        cell_texts = []
        for c in cells:
            text = (c[0] or c[1]).strip()
            text = re.sub(r'<[^>]+>', '', text)
            cell_texts.append(text)

        if not cell_texts:
            continue

        md_rows.append('| ' + ' | '.join(cell_texts) + ' |')
        if header:
            md_rows.append('| ' + ' | '.join(['---'] * len(cell_texts)) + ' |')
            header = False

    return '\n'.join(md_rows) + '\n'


def format_markdown(data):
    """Format the extracted data as a Markdown document."""
    lines = []
    lines.append(f'# {data["title"]}')
    lines.append('')
    lines.append(f'_{data["url"]}_')
    lines.append('')

    for i, turn in enumerate(data['turns']):
        turn_num = i + 1
        if turn['user']:
            lines.append('---')
            lines.append(f'> **User** (Turno {turn_num}):')
            for line in turn['user'].split('\n'):
                lines.append(f'> {line}')
            lines.append('')
            lines.append('')

        if turn['response']:
            lines.append(f'> **Gemini** (Turno {turn_num}):')
            lines.append('')
            md_body = html_to_markdown_simple(turn.get('responseHtml', ''))
            for line in md_body.split('\n'):
                lines.append(f'> {line}')
            lines.append('')

    return '\n'.join(lines)


def main():
    root = Path(__file__).resolve().parent.parent
    output_dir = root / 'output'

    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = sys.stdin.read().strip()
        if not url:
            print("Usage: extract_gemini_share.py <url>", file=sys.stderr)
            sys.exit(1)

    # Extract share ID from URL
    share_id_match = re.search(r'/([^/?]+)', url.split('gemini.google')[-1])
    share_id = share_id_match.group(1) if share_id_match else 'unknown'

    start = time.time()

    try:
        data = run_agent_browser(url)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    md = format_markdown(data)
    timing = data['_timing']
    load_t = timing['load']
    extract_t = timing['extract']

    session_dir = output_dir / share_id
    session_dir.mkdir(parents=True, exist_ok=True)

    # Write files
    conv_path = session_dir / 'conversation.md'
    conv_path.write_text(md)
    print(f"Written: {conv_path}")

    # Extract all tables into CSV files
    all_tables = []
    tables_dir = session_dir / 'tables'
    for i, turn in enumerate(data['turns']):
        for j, table in enumerate(turn.get('tables', [])):
            table_id = f"turn{i+1:02d}_table{j+1:02d}"
            all_tables.append({'id': table_id, 'turn': i + 1, 'rows': table})

            tables_dir.mkdir(parents=True, exist_ok=True)
            csv_path = tables_dir / f'{table_id}.csv'
            with open(csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(table)
            print(f"Written: {csv_path}")

    # Also print to stdout
    print(md)
    print(file=sys.stderr)
    print(f"--- Timing ---", file=sys.stderr)
    print(f"Page load:      {load_t:.2f}s", file=sys.stderr)
    print(f"Data extract:   {extract_t:.2f}s", file=sys.stderr)
    print(f"Total:          {time.time()-start:.2f}s", file=sys.stderr)
    print(f"Turns:          {len(data['turns'])}", file=sys.stderr)
    print(f"Tables found:   {len(all_tables)}", file=sys.stderr)
    print(f"Output dir:     {session_dir}", file=sys.stderr)


if __name__ == '__main__':
    main()
