name: numeric-precision
description: How to extract numbers precisely from Treasury tables and format answers correctly to pass the 1% tolerance scorer.
---

## How the Scorer Works
Your answer is read from `/app/answer.txt` and compared to the ground truth using:
- **1% numeric tolerance** — your number must be within 1% of the correct value
- **Unit-aware matching** — "2,602" is compared as the number 2602 in context
- **Commas are stripped** before comparison — "2,602" and "2602" both parse to 2602

## Answer Format Rules

### DO:
```
2,602
```
```
1.8
```
```
45,231.7
```

### DON'T:
- Add units: ~~"2,602 million"~~ (unless question asks for units in answer)
- Round aggressively: ~~"2,600"~~ when precise value is 2,602
- Use full expanded form when question says millions: ~~"2,602,000,000"~~
- Leave blank or write explanation text

## Unit Matching Is Critical
If the question says **"in millions of dollars"** → answer in millions: `2,602`
If the question says **"in billions of dollars"** → answer in billions: `2.602`
If the question says **"in thousands of dollars"** → answer in thousands: `2,602,000`

The scorer compares BASE numbers — it does NOT automatically convert units.
Getting the unit wrong = wrong answer even if you found the right row.

## Reading Dense Tables
Treasury tables often look like:

```
                          1938    1939    1940
National defense......   1,131   1,309   2,602
Interest on debt......   1,027   1,041   1,041
```

- Read column headers carefully — they may span multiple rows
- "Calendar year" and "fiscal year" columns are often side by side
- Footnotes (marked with 1/, 2/) may redefine what's included
- Dashes (—) = zero; blank cells = not applicable

## Write Answer Command
```bash
echo "2,602" > /app/answer.txt
cat /app/answer.txt  # verify it was written correctly
```

Always verify with `cat /app/answer.txt` after writing.
