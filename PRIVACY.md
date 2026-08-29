# Privacy Policy for healthex

_Last updated: 2026-08-29_

healthex is an open-source command-line tool that exports a user's own Google Health
data into a PostgreSQL database that the user runs and controls.

## Who operates healthex

healthex is not a hosted service. There is no healthex server, no healthex account,
and no healthex backend. The software runs entirely on hardware controlled by the
person using it. The author of healthex publishes the source code and does not
operate any infrastructure that processes user data.

## What data healthex accesses

When you authorize healthex, it requests read-only access to your own Google Health
data using these scopes:

- `googlehealth.sleep.readonly` — sleep sessions and sleep stages
- `googlehealth.activity_and_fitness.readonly` — daily step counts
- `googlehealth.health_metrics_and_measurements.readonly` — resting heart rate and
  heart rate variability

healthex requests read-only scopes only. It never writes to, modifies, or deletes
data in your Google Health account.

## How the data is used and where it goes

Data flows in exactly one direction: from the Google Health API to a PostgreSQL
database whose connection string you supply via `DATABASE_URL`.

- The data is written only to your database.
- It is not transmitted to the author of healthex.
- It is not transmitted to any third party.
- It is not used for analytics, advertising, profiling, model training, or any
  purpose other than storing it where you asked it to be stored.

There is no telemetry of any kind in healthex. The only network destination the
software contacts is Google's own API endpoint.

## Credentials

OAuth credentials are stored as files on your machine:

- `client_secret.json` — the OAuth client you created in your own Google Cloud project
- `token.json` — your access and refresh tokens, written with `0600` permissions
  (owner read/write only)

These files never leave your machine. Deleting `token.json` revokes healthex's local
copy of your authorization; you can additionally revoke access at any time at
https://myaccount.google.com/permissions.

## Data retention and deletion

Retention is entirely under your control, because the database is yours. healthex
never deletes health data. To remove data collected by healthex, drop the tables or
the database, and delete `token.json`.

## Changes to this policy

Changes will be committed to this file in the public repository, and its revision
history is visible at https://github.com/yetmike/healthex/commits/main/PRIVACY.md.

## Contact

Questions about this policy can be raised as an issue at
https://github.com/yetmike/healthex/issues.
