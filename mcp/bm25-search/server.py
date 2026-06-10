#!/usr/bin/env python3
"""BM25 Search MCP Server - no external dependencies."""
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

CORPUS_PATH = Path("/app/corpus")

def tokenize(text):
    return re.findall(r'[a-z0-9]+', text.lower())

class SimpleBM25:
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.docs = []
        self.filenames = []
        self.df = defaultdict(int)
        self.avgdl = 0
        self.N = 0

    def index(self, filenames, texts):
        self.filenames = filenames
        self.N = len(texts)
        total_len = 0
        for text in texts:
            tokens = tokenize(text)
            self.docs.append(tokens)
            total_len += len(tokens)
            for t in set(tokens):
                self.df[t] += 1
        self.avgdl = total_len / self.N if self.N > 0 else 1

    def search(self, query, top_k=5):
        tokens = tokenize(query)
        scores = []
        for i, doc in enumerate(self.docs):
            score = 0
            doc_len = len(doc)
            tf_map = defaultdict(int)
            for t in doc:
                tf_map[t] += 1
            for t in tokens:
                if t not in self.df:
                    continue
                tf = tf_map.get(t, 0)
                idf = math.log((self.N - self.df[t] + 0.5) / (self.df[t] + 0.5) + 1)
                tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl))
                score += idf * tf_norm
            scores.append((i, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return [(self.filenames[i], round(s, 4)) for i, s in scores[:top_k] if s > 0]

def build_index():
    print("[BM25] Building index...", file=sys.stderr)
    if not CORPUS_PATH.exists():
        print(f"[BM25] Corpus not found at {CORPUS_PATH}", file=sys.stderr)
        return None
    files = sorted(CORPUS_PATH.glob("treasury_bulletin_*.txt"))
    print(f"[BM25] Indexing {len(files)} files...", file=sys.stderr)
    filenames, texts = [], []
    for f in files:
        try:
            filenames.append(f.name)
            texts.append(f.read_text(encoding="utf-8", errors="ignore")[:1000])
        except Exception as e:
            print(f"[BM25] Error: {f.name}: {e}", file=sys.stderr)
    bm25 = SimpleBM25()
    bm25.index(filenames, texts)
    print(f"[BM25] Done indexing {len(filenames)} files", file=sys.stderr)
    return bm25

# Build index at module load time
_bm25 = None
_filenames = []

def get_index():
    global _bm25
    if _bm25 is None:
        _bm25 = build_index()
    return _bm25

def handle(request):
    method = request.get("method", "")
    rid = request.get("id", 1)

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "bm25-search", "version": "1.0.0"}
        }}

    elif method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": [{
            "name": "search_corpus",
            "description": "Search Treasury Bulletin corpus using BM25 ranking. Returns most relevant filenames. Always use this FIRST before grep to find the right documents.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query with keywords year and metric e.g. 'national defense expenditures 1940 calendar year'"},
                    "top_k": {"type": "integer", "default": 5}
                },
                "required": ["query"]
            }
        }]}}

    elif method == "tools/call":
        args = request.get("params", {}).get("arguments", {})
        query = args.get("query", "")
        top_k = min(int(args.get("top_k", 5)), 10)
        if not query:
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": "Error: query required"}], "isError": True
            }}
        bm25 = get_index()
        if not bm25:
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": "Error: index not available"}], "isError": True
            }}
        results = bm25.search(query, top_k)
        if not results:
            text = "No results found. Try different keywords."
        else:
            lines = [f"Top {len(results)} results for: '{query}'\n"]
            for i, (fname, score) in enumerate(results, 1):
                lines.append(f"{i}. {fname} (relevance: {score})")
                lines.append(f"   Path: {CORPUS_PATH}/{fname}")
            text = "\n".join(lines)
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "content": [{"type": "text", "text": text}]
        }}

    elif method == "notifications/initialized":
        return None

    return {"jsonrpc": "2.0", "id": rid, "error": {
        "code": -32601, "message": f"Unknown method: {method}"
    }}

def mcp():
    """Entry point for MCP server."""
    print("[BM25] Starting...", file=sys.stderr)
    get_index()
    print("[BM25] Ready", file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle(req)
            if resp is not None:
                print(json.dumps(resp), flush=True)
        except Exception as e:
            print(json.dumps({
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32603, "message": str(e)}
            }), flush=True)

if __name__ == "__main__":
    mcp()

# Add at top of mcp() function - index only first 500 chars per file for speed
