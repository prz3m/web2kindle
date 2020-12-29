# web2kindle

Send articles to your kindle.

## Why?

There are many apps (e.g. Send to Kindle browser extension by Amazon or Tinderizer bookmarklet) which do the same. The problem begins if the article has many images in it - they are often not included. With this script, all images are attached.

## What you need
* [kindlegen](https://www.amazon.com/gp/feature.html?ie=UTF8&docId=1000765211) - converts html to mobi. Download and put `kindlegen.exe` (or `kindlegen` on Linux) in the same directory as the program.
* Gmail account with 2 factor authentication

On Windows, you can download executable version from https://github.com/prz3m/web2kindle/releases.
On other OSes (or if you want to run from source), install dependecies from the list below.

## Dependencies
* [python-readability](https://github.com/buriy/python-readability) - handles scraping article from the webpage and is pretty   neat
* [yagmail](https://github.com/kootenpv/yagmail) - sending emails from gmail

## Preparation
### Kindle account
First of all, go to [Amazon's  Manage Your Content and Devices ](https://amazon.com/mn/dcw/myx.html). In `Settings` tab find `Approved Personal Document E-mail List` and add your gmail address. Also note your kindle address from `Send-to-Kindle E-Mail Settings` section.

### Gmail account

If you haven't already, enable 2 factor authentication. Then visit https://security.google.com/settings/security/apppasswords. At the bottom, click __Select app__, choose _Other_ and enter whatever name you want. You will get an app password (go to https://support.google.com/mail/answer/185833 for more details).

## Usage
Firstly, modify web2kindle.conf file:
```
[web2kindle]
gmail_login = your_login
kindle_address = your_kindle@kindle.com
```
or delete this file. If you do, you will be prompted for gmail login and kindle address when running the script.

Run server:
```
uvicorn --port 8666 run:app
```


## Development

Run server in development mode (with reloading):
```
uvicorn --port 8666 run:app --reload --reload-dir web2kindle --reload-dir server
```
