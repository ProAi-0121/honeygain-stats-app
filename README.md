# Honeygain Stats

A small desktop dashboard for tracking your Honeygain earnings. Built with Python and CustomTkinter — it shows your balance, daily earnings, payout progress and a few charts in a dark neon-themed window.

## Features

- Real-time balance in credits, USD and INR
- Today's earnings breakdown (sharing, content delivery, winning, referrals)
- Daily earnings table
- Payout progress bar with an estimated time to payout
- Pie and bar charts of earnings sources
- Auto-refresh every 25 seconds (toggleable)

## Requirements

- Python 3.8+
- Windows (that's what it was developed and tested on; other platforms untested)

## Setup

1. Clone the repo and install dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`
3. Put your Honeygain token in it (see below)

## Getting the token

The app talks to the same API the Honeygain web dashboard uses, so it needs your dashboard JWT:

1. Log in at [dashboard.honeygain.com](https://dashboard.honeygain.com)
2. Open browser DevTools and go to the Network tab
3. Refresh the page and find a request to `/api/v1/users/balances`
4. Copy the token from the `authorization` request header (without the `Bearer ` prefix)
5. Paste it into `.env` as `HONEYGAIN_TOKEN=...`

Tokens expire, so if the app suddenly stops showing data, grab a fresh one.

## Usage

```
python app.py
```

## Configuration

| Variable | Required | Description |
|---|---|---|
| `HONEYGAIN_TOKEN` | yes | JWT token from the Honeygain web dashboard |

## Troubleshooting

- **401 errors / empty data** — your token probably expired. Get a fresh one (see "Getting the token" above).
- **Nothing shows at all** — make sure `.env` sits next to `app.py` and the variable is named `HONEYGAIN_TOKEN`.
- **Chart area is blank** — this happens if `Honeygain` has no stats yet for a new account; give it a day or two.
