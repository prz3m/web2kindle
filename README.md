# web2kindle

Send articles to your kindle.

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

Run the server with the external secrets directory:

```console
mise run serve -- --secrets-dir ~/.secrets
```

If `--secrets-dir` is omitted, the current working directory is used for
backwards compatibility.

### Userscript (recommended)

The userscript is recommended because it bypasses CSP restrictions that can prevent the direct bookmarklet from working.

1. Install [`bookmarklet/userscript.js`](bookmarklet/userscript.js) with a userscript manager such as Tampermonkey.
2. Create a bookmark whose URL is the contents of [`bookmarklet/bookmarklet_userscript.js`](bookmarklet/bookmarklet_userscript.js).

Open an article and click the bookmark to send it.

### Direct bookmarklet

Alternatively, use [`bookmarklet/bookmarklet.js`](bookmarklet/bookmarklet.js) as a direct bookmarklet.
