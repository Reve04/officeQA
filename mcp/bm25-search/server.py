import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Union

from fastmcp import FastMCP

DOCUMENT_CACHE = {}  
BM25_CACHE = {}      

CORPUS_PATH = Path("/app/corpus")
if not CORPUS_PATH.exists():
    CORPUS_PATH = Path("d:/arenaQA/corpus")

def tokenize(text):
    return re.findall(r'[a-z0-9]+', text.lower())

def parse_float_list(s: str):
    if not s or not s.strip(): return []
    s = re.sub(r',(\d{3})(?!\d)', r'\1', s)
    s = re.sub(r'\(([^)]+)\)', r'-\1', s)
    s = re.sub(r'(\d+(?:\.\d+)?)\s*[kK]', lambda m: str(float(m.group(1)) * 1e3), s)
    s = re.sub(r'(\d+(?:\.\d+)?)\s*[mM](?:illion)?', lambda m: str(float(m.group(1)) * 1e6), s)
    s = re.sub(r'(\d+(?:\.\d+)?)\s*[bB](?:illion)?', lambda m: str(float(m.group(1)) * 1e9), s)
    parts = re.split(r'[\s,]+', s.strip())
    result = []
    for p in parts:
        p_clean = re.sub(r'[^0-9\.\-]', '', p)
        if p_clean and p_clean != '-':
            try: result.append(float(p_clean))
            except ValueError: pass
    return result

def parse_time_period(query):
    years = [int(y) for y in set(re.findall(r'\b(19\d{2}|20\d{2})\b', query))]
    month_map = {
        'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
        'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
        'august': 8, 'aug': 8, 'september': 9, 'sept': 9, 'sep': 9,
        'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
    }
    q_month = -1
    for m, val in month_map.items():
        if re.search(r'\b' + m + r'\b', query.lower()):
            q_month = val
            break
    return years, q_month

class SimpleBM25:
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.docs = []
        self.doc_ids = []
        self.page_nums = []
        self.df = defaultdict(int)
        self.avgdl = 0
        self.N = 0

    def index(self, doc_ids, page_nums, texts):
        self.doc_ids = doc_ids
        self.page_nums = page_nums
        self.N = len(texts)
        if self.N == 0: return
        total_len = 0
        for text in texts:
            tokens = tokenize(text)
            self.docs.append(tokens)
            total_len += len(tokens)
            for t in set(tokens): self.df[t] += 1
        self.avgdl = total_len / self.N

    def search(self, query, top_k=5):
        tokens = tokenize(query)
        scores = []
        q_years, q_month = parse_time_period(query)
        
        for i, doc in enumerate(self.docs):
            score = 0
            doc_len = len(doc)
            tf_map = defaultdict(int)
            for t in doc: tf_map[t] += 1
            for t in tokens:
                if t not in self.df: continue
                tf = tf_map.get(t, 0)
                idf = math.log((self.N - self.df[t] + 0.5) / (self.df[t] + 0.5) + 1)
                tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl))
                score += idf * tf_norm
            
            if self.doc_ids[i].endswith(".json"): score *= 5.0
                
            if q_years:
                f_year_match = re.search(r'treasury_bulletin_(\d{4})_(\d{2})', self.doc_ids[i])
                if f_year_match:
                    f_year, f_month = int(f_year_match.group(1)), int(f_year_match.group(2))
                    if q_month != -1 and f_year in q_years and f_month == q_month: score *= 3.0
                    elif f_year in q_years: score *= 1.5
            
            scores.append((i, score))
            
        scores.sort(key=lambda x: x[1], reverse=True)
        return [(self.doc_ids[i], self.page_nums[i], round(s, 4)) for i, s in scores[:top_k] if s > 0]

# --- PURE PYTHON MATH HELPERS (Numerical Stability & Fallbacks) ---

def _solve_linear_system(A, b):
    """Solves Ax = b using Gaussian elimination with partial pivoting."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    
    for i in range(n):
        max_row = max(range(i, n), key=lambda r: abs(M[r][i]))
        M[i], M[max_row] = M[max_row], M[i]
        if abs(M[i][i]) < 1e-12: continue
        for k in range(i+1, n):
            c = M[k][i] / M[i][i]
            for j in range(i, n+1):
                M[k][j] -= c * M[i][j]
                
    x = [0.0] * n
    for i in range(n-1, -1, -1):
        if abs(M[i][i]) < 1e-12: x[i] = 0.0
        else:
            x[i] = M[i][n]
            for j in range(i+1, n): x[i] -= M[i][j] * x[j]
            x[i] /= M[i][i]
    return x

def _hp_filter_pure(y, lambda_val):
    """Pure-Python Hodrick-Prescott filter fallback."""
    n = len(y)
    A = [[0.0]*n for _ in range(n)]
    for i in range(n): A[i][i] = 1.0
        
    for j in range(n):
        for k in range(n):
            val = 0.0
            for i in range(n-2):
                d_ij = 1.0 if i == j else (-2.0 if i+1 == j else (1.0 if i+2 == j else 0.0))
                d_ik = 1.0 if i == k else (-2.0 if i+1 == k else (1.0 if i+2 == k else 0.0))
                val += d_ij * d_ik
            A[j][k] += lambda_val * val
            
    return _solve_linear_system(A, y)

mcp = FastMCP("treasury-agent-tools")

@mcp.tool()
def search_corpus(query: str, top_k: int = 5) -> str:
    """Search Treasury Bulletin corpus."""
    q_years, q_month = parse_time_period(query)
    q_years = list(set(q_years)) 
    
    if not q_years:
        q_years = list(range(1939, 2026))

    if not CORPUS_PATH.exists(): return f"Error: Corpus path {CORPUS_PATH} does not exist."

    all_results = []
    for y in q_years:
        if y not in DOCUMENT_CACHE:
            files_json = list(CORPUS_PATH.glob(f"treasury_bulletin_{y}_*.json"))
            files_txt = list(CORPUS_PATH.glob(f"treasury_bulletin_{y}_*.txt"))
            y_doc_ids, y_page_nums, y_texts = [], [], []
            for f in files_json:
                try:
                    data = json.loads(f.read_text(encoding="utf-8", errors="ignore"))
                    for p in data.get("pages", []):
                        page_text = p.get("text", "") + "\n" + "\n".join([t.get("markdown", "") for t in p.get("tables", [])])
                        y_doc_ids.append(f.name); y_page_nums.append(str(p.get("page_number", "1"))); y_texts.append(page_text)
                except: pass
            for f in files_txt:
                try: y_doc_ids.append(f.name); y_page_nums.append("1"); y_texts.append(f.read_text(encoding="utf-8", errors="ignore"))
                except: pass
            DOCUMENT_CACHE[y] = (y_doc_ids, y_page_nums, y_texts)
            
        cached_ids, cached_pages, cached_texts = DOCUMENT_CACHE[y]
        if y not in BM25_CACHE:
            bm25 = SimpleBM25(); bm25.index(cached_ids, cached_pages, cached_texts); BM25_CACHE[y] = bm25
        all_results.extend(BM25_CACHE[y].search(query, top_k))

    if not all_results: return f"No documents found."
        
    all_results.sort(key=lambda x: x[2], reverse=True)
    final_results = all_results[:top_k]
    lines = [f"Top {len(final_results)} matches for '{query}':\n"]
    for i, (fname, page, score) in enumerate(final_results, 1):
        lines.append(f"{i}. Document: {fname} | Page: {page} | Relevance: {score}")
    return "\n".join(lines)

@mcp.tool()
def extract_page_content(doc_id: str, page_number: Union[str, int]) -> str:
    """Extracts content."""
    page_number = str(page_number)
    p = CORPUS_PATH / doc_id
    if not p.exists(): return f"Error: Document {doc_id} not found."
        
    if doc_id.endswith(".json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
            for p_obj in data.get("pages", []):
                if str(p_obj.get("page_number", "")) == page_number:
                    text = p_obj.get("text", "")
                    tables = p_obj.get("tables", [])
                    res = f"--- EXTRACTED PAGE {page_number} FROM {doc_id} ---\n\n{text}"
                    if tables: res += "\n\n[TABLE DATA]:\n" + "\n".join([t.get("markdown", "") for t in tables])
                    return res
            return f"Error: Page {page_number} not found in {doc_id}."
        except Exception as e: return f"Error reading document: {e}"
            
    elif doc_id.endswith(".txt"):
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            if len(content) > 1000000: content = content[:1000000] + "\n\n...[TRUNCATED due to length]"
            return f"--- EXTRACTED FULL DOCUMENT {doc_id} ---\n\n{content}"
        except Exception as e: return f"Error reading document: {e}"

# --- MATH TOOLS ---

@mcp.tool()
def calculate_expression(expression: str) -> str:
    """Evaluate a mathematical expression safely."""
    expr = expression.replace("million", "* 1000000").replace("billion", "* 1000000000").replace("thousand", "* 1000")
    expr = expr.replace("%", " / 100").replace("^", "**")
    expr = re.sub(r'(?<=\d),(?=\d)', '', expr)
    try:
        allowed_names = {"__builtins__": None, "math": math, "ln": math.log, "log": math.log10, "sqrt": math.sqrt, "pow": pow, "exp": math.exp, "pi": math.pi, "abs": abs, "sum": sum, "min": min, "max": max, "round": round, "int": int, "float": float}
        return str(eval(expr, allowed_names, {}))
    except Exception as e: return f"Math Error: {e}"

@mcp.tool()
def calculate_sample_std_dev(values: str) -> str:
    """Calculates the SAMPLE standard deviation (N-1)."""
    try:
        vs = parse_float_list(values)
        if len(vs) < 2: return "Error: Need at least 2 values."
        mean = sum(vs) / len(vs)
        variance = sum((x - mean) ** 2 for x in vs) / (len(vs) - 1)
        return f"Sample Std Dev: {math.sqrt(variance):.6f}"
    except Exception as e: return f"Math Error: {e}"

@mcp.tool()
def calculate_population_std_dev(values: str) -> str:
    """Calculates the POPULATION standard deviation (N)."""
    try:
        vs = parse_float_list(values)
        if not vs: return "Error: No values."
        mean = sum(vs) / len(vs)
        variance = sum((x - mean) ** 2 for x in vs) / len(vs)
        return f"Population Std Dev: {math.sqrt(variance):.6f}"
    except Exception as e: return f"Math Error: {e}"

@mcp.tool()
def calculate_pearson_correlation(x_values: str, y_values: str) -> str:
    """Calculates Pearson correlation coefficient using numerically stable mean-deviation formulation."""
    try:
        xs, ys = parse_float_list(x_values), parse_float_list(y_values)
        if len(xs) != len(ys) or len(xs) < 2: return "Error: Invalid data."
        n = len(xs)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den_x = sum((x - mean_x)**2 for x in xs)
        den_y = sum((y - mean_y)**2 for y in ys)
        
        den = math.sqrt(den_x * den_y)
        if den == 0: return "Error: Denominator is zero."
        return f"Pearson r: {num/den:.6f}"
    except Exception as e: 
        return f"Math Error: {e}"

@mcp.tool()
def calculate_linear_regression(x_values: str, y_values: str) -> str:
    """Calculates OLS linear regression using numerically stable mean-deviation formulation. Returns '[slope, intercept]'."""
    try:
        xs, ys = parse_float_list(x_values), parse_float_list(y_values)
        if len(xs) != len(ys) or len(xs) < 2: return "Error: Invalid data."
        n = len(xs)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den = sum((x - mean_x)**2 for x in xs)
        
        if den == 0: return "Error: Denominator is zero."
        slope = num / den
        intercept = mean_y - slope * mean_x
        return f"[{slope:.3f}, {intercept:.3f}]"
    except Exception as e: 
        return f"Math Error: {e}"

@mcp.tool()
def calculate_geometric_mean(values: str) -> str:
    """Calculates geometric mean using log approach."""
    try:
        vs = parse_float_list(values)
        if not vs or any(v <= 0 for v in vs): return "Error: Requires strictly positive data."
        return f"Geometric Mean: {math.exp(sum(math.log(v) for v in vs) / len(vs)):.6f}"
    except Exception as e: return f"Math Error: {e}"

@mcp.tool()
def calculate_gini_coefficient(values: str) -> str:
    """Calculates the Gini coefficient."""
    try:
        vs = parse_float_list(values)
        if not vs: return "Error: No values."
        n = len(vs)
        if n == 1: return "Gini: 0.000000"
        total_sum = sum(vs)
        if total_sum == 0: return "Error: Sum of values is zero."
        abs_diff_sum = sum(abs(x - y) for x in vs for y in vs)
        gini = abs_diff_sum / (2 * n * total_sum)
        return f"Gini: {gini:.6f}"
    except Exception as e: return f"Math Error: {e}"

@mcp.tool()
def calculate_coefficient_of_variation(values: str) -> str:
    """Calculates Coefficient of Variation (CV) = Sample Std Dev / Mean."""
    try:
        vs = parse_float_list(values)
        if len(vs) < 2: return "Error: Need at least 2 values."
        mean = sum(vs) / len(vs)
        if mean == 0: return "Error: Mean is zero."
        variance = sum((x - mean) ** 2 for x in vs) / (len(vs) - 1)
        std_dev = math.sqrt(variance)
        cv = std_dev / abs(mean)
        return f"CV: {cv:.6f}"
    except Exception as e: return f"Math Error: {e}"

@mcp.tool()
def calculate_hp_filter(values: str, lambda_val: float = 1600.0) -> str:
    """Calculates the Hodrick-Prescott trend component. Default lambda=1600 for monthly data, 100 for annual."""
    try:
        y = parse_float_list(values)
        n = len(y)
        if n < 4: return "Error: Need at least 4 values."
        
        try:
            import numpy as np
            y_np = np.array(y)
            I = np.eye(n)
            D = np.zeros((n-2, n))
            for i in range(n-2):
                D[i, i] = 1; D[i, i+1] = -2; D[i, i+2] = 1
            penalty = lambda_val * (D.T @ D)
            tau = np.linalg.solve(I + penalty, y_np)
            return f"HP Trend: {','.join([f'{x:.4f}' for x in tau.tolist()])}"
        except ImportError:
            # Fallback to pure Python solver if numpy is missing in sandbox
            tau = _hp_filter_pure(y, lambda_val)
            return f"HP Trend: {','.join([f'{x:.4f}' for x in tau])}"
    except Exception as e:
        return f"Math Error: {e}"

@mcp.tool()
def calculate_optimal_box_cox(y_values: str) -> str:
    """Finds optimal Box-Cox lambda."""
    try:
        vs = parse_float_list(y_values)
        if not vs or any(v <= 0 for v in vs): return "Error: Requires strictly positive data."
        n = len(vs); sum_log_y = sum(math.log(v) for v in vs)
        def log_likelihood(lmbda):
            y_trans = [math.log(v) for v in vs] if lmbda == 0 else [(v**lmbda - 1) / lmbda for v in vs]
            mean_y_trans = sum(y_trans) / n; var_y_trans = sum((v - mean_y_trans)**2 for v in y_trans) / n
            return -n/2 * math.log(var_y_trans) + (lmbda - 1) * sum_log_y if var_y_trans > 0 else -float('inf')
        best_lambda, max_ll = 0, -float('inf')
        for l in [i/100 for i in range(-200, 201)]: 
            ll = log_likelihood(l)
            if ll > max_ll: max_ll = ll; best_lambda = l
        return f"Optimal Lambda: {best_lambda:.3f}"
    except Exception as e: return f"Math Error: {e}"

@mcp.tool()
def apply_box_cox_transformation(y_values: str, lambda_val: float) -> str:
    """Applies Box-Cox transformation."""
    try:
        vs = parse_float_list(y_values)
        if not vs or any(v <= 0 for v in vs): return "Error: Requires strictly positive data."
        res = [math.log(v) if lambda_val == 0 else (v**lambda_val - 1) / lambda_val for v in vs]
        output = f"Transformed values: {[round(r, 4) for r in res]}"
        if len(res) == 2: output += f"\nDifference (First - Second): {res[0] - res[1]:.4f}"
        return output
    except Exception as e: return f"Error: {e}"

@mcp.tool()
def submit_answer(answer: str) -> str:
    """Submit your final numerical answer here."""
    with open("/app/answer.txt", "w") as f: f.write(str(answer).strip())
    return "Answer submitted successfully! You MUST now stop execution."

if __name__ == "__main__": mcp.run()