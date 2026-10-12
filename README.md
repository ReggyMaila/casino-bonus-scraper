# Casino Bonus Scraper (screening-task prototype)

A small Python scraper that fetches one public casino comparison page, checks `robots.txt`, uses an LLM to structure three bonus records, validates the response, and writes `bonuses.json`. A responsive static page renders that JSON.

## Important status

This repository is a runnable starter, not a claim that a live scrape or deployment has already succeeded. `bonuses.json` starts empty on purpose: casino values are not typed in by hand. Run the scraper to generate the three records. The default source is a candidate only; the script checks `robots.txt` when run and stops if permission cannot be verified or access is denied. If it stops, select another public source whose terms and robots rules permit the intended access.

## Requirements

- Python 3.10+
- An API key for an OpenAI API or a compatible API that supports Chat Completions JSON Schema output
- Network access to the chosen source and LLM endpoint

## Install

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Set your API key as an environment variable; do not commit it.

```bash
# macOS/Linux
export OPENAI_API_KEY="your-key"
# Windows PowerShell
$env:OPENAI_API_KEY="your-key"
```

Optional configuration:

```bash
export OPENAI_MODEL="gpt-4o-mini"
# For an OpenAI-compatible provider:
export OPENAI_BASE_URL="https://provider.example/v1"
# Override only with a source you have checked and are permitted to fetch:
export SOURCE_URL="https://permitted.example/bonuses"
```

## Run

From the project directory, one command runs the fetch, LLM extraction, validation and JSON write:

```bash
python scraper.py
```

The command should finish with `Saved 3 records to .../bonuses.json`. If robots rules cannot be verified, the source disallows crawling, the site returns 401/403/429, or the LLM configuration fails, it stops and prints an error. Do not work around a block; switch sources.

## View the web page locally

A local server is needed because browsers restrict `fetch()` from a `file://` URL.

```bash
python -m http.server 8000
```

Open <http://localhost:8000>.

## Publish with GitHub Pages

1. Create a public GitHub repository and push this folder.
2. Ensure `index.html`, `app.js`, `styles.css`, and the generated `bonuses.json` are at the repository root.
3. In repository **Settings → Pages**, select **Deploy from a branch**, choose `main` and `/ (root)`, then save.
4. Wait for the Pages deployment to complete and copy the live URL into the submission.
5. Never commit `.env` or API credentials. GitHub Pages hosts the static page only; it does not run the Python scraper. For daily updates, use a scheduled GitHub Actions workflow or a separate scheduled worker to regenerate and publish the JSON.

Do not publish unreviewed data as confirmed. Check the source links and compare the extracted `evidence` and terms with the original page first.

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
