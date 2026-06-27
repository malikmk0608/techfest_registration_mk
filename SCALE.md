# SCALE.md

Registrations open at 6 PM on Friday and around 2000 students might hit the /register endpoint in the first minute. The server only has 1 GB RAM, so I had to think about what would break first.

I'm using SQLite, and by default SQLite locks the whole database file when something is being written. So if many people register at the same time, requests basically queue up, and some could fail with a "database is locked" error.

To handle this, I turned on WAL mode for the database:

```python
conn.execute("PRAGMA journal_mode=WAL;")
```

This allows reading and writing to happen at the same time instead of blocking each other. So someone checking their ticket doesn't have to wait for someone else who is registering.

I also added a busy timeout:

```python
conn.execute("PRAGMA busy_timeout=5000;")
```

If two writes happen at the exact same moment, this makes the database wait a few seconds and retry instead of throwing an error right away.

I chose this over switching to something like PostgreSQL or adding Redis because it's a small change, doesn't need any new setup, and directly solves the locking problem mentioned in the spike scenario.

If I had more time, I would also add rate limiting on /register so the same person can't spam it, and run the server with a fixed number of workers since RAM is limited.
