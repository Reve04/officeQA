name: treasury-navigation
description: How to navigate the U.S. Treasury Bulletin corpus efficiently.
---

## Corpus Location
- All files: `/app/corpus/`
- Index: `/app/corpus/index.txt`
- Format: `treasury_bulletin_YYYY_MM.txt`

## Time Lookup Table
| Data period | Best files to check first |
|-------------|--------------------------|
| Jan 1940 | treasury_bulletin_1940_02.txt or _03.txt |
| Full year 1940 | treasury_bulletin_1941_01.txt or _02.txt |
| Full year 1953 | treasury_bulletin_1954_01.txt or _02.txt |
| Full year 1960 | treasury_bulletin_1961_01.txt or _02.txt |
| FY ending Sep 1945 | treasury_bulletin_1945_11.txt or _12.txt |
| Any single month | Check bulletin 1-2 months after that month |

## Best Search Commands
```bash
# Find files for a year
ls /app/corpus/ | grep "1941"

# Search for exact term with context
grep -i -A20 -B5 "national defense" /app/corpus/treasury_bulletin_1941_01.txt

# Search across multiple files
grep -ril "defense" /app/corpus/treasury_bulletin_1941*.txt

# Search for a specific number (useful for verification)
grep -r "2,602" /app/corpus/treasury_bulletin_1941*.txt
```

## Common Table Names
- "Budget Receipts and Expenditures" — main expenditure table
- "Statement of Receipts and Expenditures" — detailed breakdown
- "Cash Income and Outgo" — overall cash flow
- "Public Debt" — debt figures
- "Trust Fund Operations" — Social Security, unemployment

## Table Reading Tips
- Tables often span multiple pages — check for continuation
- Column headers may be on 2 rows — read both
- "Calendar year" and "fiscal year" are often adjacent columns
- Numbers in parentheses () = negative values
- Asterisk (*) or dagger (†) = see footnote
- Three dots (...) = not available
- Dash (—) = zero

## BM25 Search Tool
You have a search_corpus tool — use it before grep!
Examples:
- search_corpus("national defense 1940 expenditures")
- search_corpus("receipts income tax 1955 fiscal year")
- search_corpus("public debt interest 1963")
This returns the top 5 most relevant files instantly.
Always use search_corpus first, then grep the returned files.
