# Getting Started with Code for Finance

This guide gets you from zero to writing Python scripts that do useful things
with financial data and documents. About 30 minutes, and by the end you'll have
a working setup where you describe what you need in plain English and get
working code back.

No prior coding experience required. You know finance — that's the hard part.

---

## What you'll be able to do

Once set up, you talk to an AI assistant (Claude) in your terminal. It writes
and runs Python code for you. Examples of things you can ask:

**Market data:**
- "Pull the last year of daily prices for SPY and TLT, calculate rolling correlation, save to Excel"
- "Download the US yield curve for the past year and plot it"
- "Compare YTD performance of XLF, XLK, and XLE in a chart"

**Documents:**
- "Extract all tables from this PDF report and put them in Excel"
- "Read this Word doc and pull out every dollar figure"
- "Compare data in these two Excel files and highlight differences"

**Analysis:**
- "Get the last 12 CPI readings from FRED and calculate month-over-month changes"
- "Pull quarterly revenue for AAPL, MSFT, and GOOGL into one sheet"

Just describe it like you'd describe it to a colleague. Claude handles the code.

---

## What you're setting up

1. **uv** — installs and manages Python for you (no version headaches)
2. **Claude Code** — AI assistant that writes and runs code based on your descriptions
3. **Git + GitHub** — saves your work (like Track Changes for code)
4. **Quality hooks** — automated checks that catch mistakes (wrong numbers, missing data, leaked API keys)

---

## Step 1: Open your terminal

**Mac:** Press `Cmd + Space`, type "Terminal," hit Enter.

**Windows:** Press `Win`, type "PowerShell," hit Enter.
Use PowerShell, not Command Prompt — it handles the install commands better.

---

## Step 2: Install uv

uv is a tool that manages Python for you. You won't interact with it directly —
it works behind the scenes so you don't have to worry about Python versions
or package conflicts.

**Mac/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**After installing, close and reopen your terminal.** This is important —
the terminal needs to reload to see the new command.

Check it worked:
```bash
uv --version
```

If you see a version number, you're good. If you see "command not found," see
[Troubleshooting](#troubleshooting) below.

---

## Step 3: Install Git

Git saves your work and lets you undo mistakes.

**Mac:** Git is usually pre-installed. Check:
```bash
git --version
```
If not found, run: `xcode-select --install` and follow the prompts.

**Windows:** Download from [git-scm.com/downloads](https://git-scm.com/downloads).
During install, keep all defaults.

Tell Git who you are (use your real name and email):
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

---

## Step 4: Get the project

**Option A — If someone shared this repo with you:**
```bash
cd ~/Desktop
git clone <THE_URL_THEY_GAVE_YOU>
cd finance-coding-setup
```

**Option B — Starting fresh on GitHub:**
1. Go to [github.com](https://github.com/) and create an account
2. Create a new repository called `finance-coding-setup`
3. Clone it:
```bash
cd ~/Desktop
git clone https://github.com/YOUR_USERNAME/finance-coding-setup.git
cd finance-coding-setup
```

Then copy all files from this template into your repo.

---

## Step 5: Run setup

One command installs everything:

```bash
bash setup.sh
```

This takes 1-2 minutes. It installs Python, all the financial and document
analysis libraries, and sets up the quality hooks. You'll see a summary when
it's done.

If it fails, see [Troubleshooting](#troubleshooting).

---

## Step 6: Install Claude Code

Claude Code is the AI assistant that writes and runs code for you.

### Install Node.js first

Claude Code needs Node.js (a runtime — you won't use it directly).

**Mac:**
```bash
brew install node
```
If `brew` isn't installed:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install node
```

**Windows:**
Go to [nodejs.org](https://nodejs.org/) → download the **LTS** version → run the installer.
Keep all defaults. **Close and reopen PowerShell after installing.**

### Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
```

If you get a permissions error on Mac/Linux:
```bash
sudo npm install -g @anthropic-ai/claude-code
```

### Get your API key

1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Create an account (or sign in)
3. Click **API Keys** in the sidebar
4. Click **Create Key**
5. Copy the key — it looks like `sk-ant-...`
6. Keep this page open, you'll paste it in the next step

---

## Step 7: Start working

```bash
cd ~/Desktop/finance-coding-setup
claude
```

First time, it asks for your API key — paste the one you copied.

Then just type what you need:

```
Pull the last 6 months of daily closing prices for SPY and TLT,
calculate the rolling 20-day correlation, and save to Excel.
```

Claude writes the script, runs it, and your Excel file appears in `~/finance-outputs/`.

---

## Your daily workflow

1. Open terminal
2. `cd ~/Desktop/finance-coding-setup`
3. `claude`
4. Describe what you need
5. Claude writes code, runs it, saves output to `~/finance-outputs/`
6. Open the output file

That's it. You never need to write or read Python code yourself.

---

## Working with files

### Drop a file for analysis

If you have a PDF report, Excel file, or Word doc you want to analyze,
put it somewhere accessible (like your Desktop) and tell Claude:

```
Extract all tables from ~/Desktop/quarterly-report.pdf and save as Excel
```

Or:

```
Read the Word doc at ~/Desktop/investment-memo.docx and pull out every company name and dollar figure
```

Claude knows how to handle PDFs, Word docs, and Excel files.

### Where your outputs go

All generated files are saved to `~/finance-outputs/`. This is a folder on
your computer — open it in Finder (Mac) or Explorer (Windows) like any folder.

Every Excel file includes a "Metadata" tab showing when it was generated and
what data source was used, so you always know where numbers came from.

---

## API keys

Some data sources need a free API key. Claude will tell you when one is needed
and walk you through getting it.

Your keys are stored in a file called `.env` in the project folder. You'll
never need to edit this file manually — Claude handles it for you.

If you already have keys, you can add them yourself: open `.env` in any text
editor and paste them in:

```
FRED_API_KEY=your_key_here
ALPHA_VANTAGE_API_KEY=your_key_here
```

**FRED** (Federal Reserve economic data — interest rates, CPI, GDP):
Get a free key at [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)

---

## What the quality hooks do

You don't need to manage these — they run automatically in the background.
Here's what they catch:

- **Before code is saved:** Prevents API keys from being written into scripts,
  catches common financial calculation mistakes (floating-point errors on dollar
  amounts), ensures your data gets validated before being saved to a file
- **After code runs:** Checks that output files aren't empty, flags suspicious
  data (negative stock prices, too many missing values, stale dates)
- **Before code is committed to GitHub:** Final check that no API keys or
  passwords are being pushed to the internet

When a hook catches something, Claude fixes it automatically and rewrites the
code. You'll rarely notice — the hooks are a safety net, not a speed bump.

---

## Saving your work to GitHub

After a session, save your scripts:

```bash
git add .
git commit -m "Add yield curve analysis"
git push
```

Or just tell Claude: *"save and push my changes"* — it handles it.

---

## Running scripts with uv

When Claude runs a script, it uses `uv run python script.py`. This
automatically uses the right Python version and the packages installed in
this project.

If you ever need to run a script yourself:
```bash
uv run python my_script.py
```

To install an extra package:
```bash
uv add some-package
```

You never need to type `pip install`, `python3`, `source activate`, or
any of the old Python incantations. uv handles it.

---

## Troubleshooting

### "command not found: uv"

You installed uv but the terminal doesn't see it yet.

**Fix:** Close the terminal window completely, open a new one, and try again.

If it still doesn't work:
```bash
export PATH="$HOME/.local/bin:$PATH"
uv --version
```
If that works, add `export PATH="$HOME/.local/bin:$PATH"` to the end of your
`~/.bashrc` (Linux) or `~/.zshrc` (Mac) file.

### "command not found: node" or "command not found: npm"

Node.js isn't installed or isn't in your PATH.

**Mac:** `brew install node` — if brew isn't found, install it first (see Step 6).

**Windows:** Download from [nodejs.org](https://nodejs.org/), install the LTS version,
then **close and reopen PowerShell**.

### "permission denied" when installing Claude Code

**Mac/Linux:** Add `sudo` in front:
```bash
sudo npm install -g @anthropic-ai/claude-code
```

**Windows:** Open PowerShell as Administrator (right-click → Run as Administrator).

### "EACCES" errors on Mac

```bash
sudo chown -R $(whoami) /usr/local/lib/node_modules
npm install -g @anthropic-ai/claude-code
```

### setup.sh says "uv was installed but isn't in your PATH"

Close the terminal, open a new one, and run `bash setup.sh` again.
The first terminal session doesn't know about uv yet.

### "Java is required" when processing PDFs with tabula

Some complex PDF tables use tabula-py, which needs Java:

**Mac:** `brew install java`
**Windows:** Download from [java.com](https://www.java.com/)

If you don't want to install Java, that's fine — pdfplumber handles most PDFs
without it. Tell Claude "use pdfplumber, not tabula."

### Script errors or crashes

Copy the error message and paste it to Claude. It will fix the code.
You don't need to understand the error — that's Claude's job.

### "BLOCKED: Code quality issues"

This means the quality hooks caught something. Claude will see the same
message and rewrite the code to fix it. If it keeps happening, tell Claude
what you're trying to do in different words.

---

## What's next

You don't need to plan ahead. Bring your real work problems — the repetitive
spreadsheet tasks, the PDFs you have to manually copy data from, the reports
you build every Monday morning.

Start with one thing. Get it working. Then the next thing.
