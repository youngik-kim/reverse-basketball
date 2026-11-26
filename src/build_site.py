# -*- coding: utf-8 -*-
"""data.json + template.html -> index.html"""
import io, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tpl = io.open(os.path.join(ROOT, "_build", "template.html"), encoding="utf-8").read()
data = io.open(os.path.join(ROOT, "data.json"), encoding="utf-8").read()
out = tpl.replace("/*__DATA__*/", data.strip())
assert "/*__DATA__*/" not in out
io.open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(out)
print("index.html", len(out), "bytes")
