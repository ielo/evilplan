"""Split the policy PDF into sections that keep rule IDs and text, so every Rego rule can point back to its source."""
import argparse, json, re, sys
import pymupdf

RULE = re.compile(r"^([A-Z]-\d{2})\s+(.+)$")
HEAD = re.compile(r"^(\d{1,2})\.\s+(.+)$")
NOISE = re.compile(r"^(ACME BANK\s+\|.*|Page \d+)$")

def sections(pdf_path):
    doc = pymupdf.open(pdf_path)
    out, cur = [], None
    for pno, page in enumerate(doc, 1):
        for line in page.get_text().splitlines():
            line = line.strip()
            if not line or NOISE.match(line):
                continue
            m = RULE.match(line)
            h = HEAD.match(line)
            if m:
                cur = {"id": m.group(1), "title": m.group(2), "page": pno, "text": []}
                out.append(cur)
            elif h and len(line) < 80:
                cur = {"id": "S" + h.group(1).zfill(2), "title": h.group(2), "page": pno, "text": []}
                out.append(cur)
            elif cur is None:
                cur = {"id": "S00", "title": "Preamble", "page": pno, "text": []}
                out.append(cur)
                cur["text"].append(line)
            else:
                cur["text"].append(line)
    for s in out:
        s["text"] = "\n".join(s["text"])
    return out

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("-o", required=True)
    a = ap.parse_args(argv)
    secs = sections(a.pdf)
    import os
    os.makedirs(os.path.dirname(a.o) or ".", exist_ok=True)
    json.dump(secs, open(a.o, "w"), indent=2, ensure_ascii=False)
    rules = [s for s in secs if RULE.match(s["id"] + " x")]
    print(f"{len(secs)} sections, {len(rules)} labeled rules -> {a.o}")

if __name__ == "__main__":
    main()
