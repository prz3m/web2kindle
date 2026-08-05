# web2kindle

Collect articles into an EPUB and send it to your Kindle.

## Why?

There are many apps which do the same. The problem begins if the article has many images in it - they are often not included. With this script, all images are attached.

## What you need

* Gmail account and a Google Cloud project with the Gmail API enabled
* Kindle Send-to-Kindle email address
* Python 3.14 and [uv](https://docs.astral.sh/uv/getting-started/installation/)

You may use [mise](https://mise.jdx.dev/getting-started/) to install Python:

```console
mise install
uv sync
```

Without mise, install uv and run `uv sync`.

## Preparation

### Kindle account

Go to Amazon's **Manage Your Content and Devices** settings. Under **Personal Document Settings**, add your Gmail address to the **Approved Personal Document E-mail List** and note your Kindle address under **Send-to-Kindle E-Mail Settings**.

### Gmail account

Follow Google's [Gmail API Python quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python) to enable the Gmail API, configure the OAuth consent screen, and create a **Desktop app** OAuth client.

Keep the downloaded client JSON and generated token outside the repository so tools
working in this checkout cannot read them. For example, create a private directory
elsewhere and point web2kindle at it:

```console
mkdir -p ~/.secrets
chmod 700 ~/.secrets
mise run get_new_token -- --secrets-dir ~/.secrets
```

The authorization flow creates `token.json` in that directory.

## Usage

Copy and edit the configuration file in the same private directory:

```console
cp web2kindle.conf.template ~/.secrets/web2kindle.conf
```

Create a directory outside the checkout for generated files and run the server
with both external directories:

```console
mkdir -p ~/.local/share/web2kindle
mise run serve -- --secrets-dir ~/.secrets --documents-dir ~/.local/share/web2kindle
```

If `--secrets-dir` is omitted, the current working directory is used for
backwards compatibility. If `--documents-dir` is omitted, the existing
`documents` directory is used. `WEB2KINDLE_DOCUMENTS_DIR` can also provide the
default documents directory.

To verify that the server and VS Code port forwarding are reachable, open
<http://127.0.0.1:8666/health> in the browser or run:

```console
curl http://127.0.0.1:8666/health
```

The response should be `{"status":"ok"}`.

### Userscript

The userscript uses its manager's cross-origin request API to reach the local
web2kindle server without enabling CORS.

1. Install [`bookmarklet/userscript.js`](bookmarklet/userscript.js) with Violentmonkey.
2. Create an **Add to Kindle queue** bookmark whose URL is the contents of [`bookmarklet/bookmarklet_userscript.js`](bookmarklet/bookmarklet_userscript.js).
3. Create a **Send Kindle queue** bookmark whose URL is the contents of [`bookmarklet/bookmarklet_send_userscript.js`](bookmarklet/bookmarklet_send_userscript.js).
4. Create a **Send current article now** bookmark whose URL is the contents of [`bookmarklet/bookmarklet_send_now_userscript.js`](bookmarklet/bookmarklet_send_now_userscript.js).

The bookmarks only dispatch events to the installed userscript. After updating
`userscript.js`, replace or reinstall its installed copy in Violentmonkey as
well; changing the bookmark URLs does not update the userscript logic.

When upgrading from the older `http://tampermonkey.net/` namespace, remove or
disable that installed copy before installing the current `web2kindle`
version. Otherwise both scripts may react to the same bookmark event.

Click **Add to Kindle queue** on every article you want to collect. Click
**Send Kindle queue** to build one EPUB with a table of contents and send all
pending articles. Articles are moved out of the pending queue only after Gmail
accepts the message.

Collection EPUBs open on an inline table of contents and use a UTC timestamped
title such as `web2kindle — 2026-08-05 14:30 UTC`.

Use **Send current article now** when an article should be converted and sent
immediately without being added to or changing the queue.

## Queue files

Prepared articles are stored under `<documents-dir>/queue/pending`. After a
successful send they are moved under `<documents-dir>/queue/sent/<batch-id>`.
Generated EPUBs are kept under `<documents-dir>/queue/epubs`.
