# Casino Bonus Scraper (screening-task prototype)

A small Python scraper that fetches one public casino comparison page, checks `robots.txt`, uses an LLM to structure three bonus records, validates the response, and writes `bonuses.json`. A responsive static page renders that JSON.


## Requirements

- Python 3.10+
- An API key for an OpenAI API or a compatible API that supports Chat Completions JSON Schema output
- Network access to the chosen source and LLM endpoint
```
URL

https://reggymaila.github.io/casino-bonus-scraper/



## Output fields

- `casino`
- `welcome_bonus`
- `wagering_requirement` (numeric multiplier or `null`)
- `wagering_text` (original wording where found)
- `minimum_deposit_amount` and `currency`
- `source_url`
- `evidence`
- `needs_review`
- `collected_at`

The numeric multiplier is kept separate from its original wording because a page may contain different conditions for sports, casino games, and free spins. `needs_review` is true when the model indicates uncertainty or a source URL mismatch.

## Known limitations / honest handover

- The default source is a candidate, not a guarantee of access. Its robots rules and current HTML must be checked at runtime.
- A page that requires JavaScript may need a Playwright adapter; the script intentionally does not bypass logins, CAPTCHAs, or blocks.
- The LLM output must be reviewed against the evidence before production use. JSON schema validation cannot guarantee factual correctness.
- The prototype has no database, user interface for corrections, automated monitoring, or daily scheduler.
- The live page URL is not included until the repository is pushed and GitHub Pages deployment succeeds.
