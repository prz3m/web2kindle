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
* PyQT - if you will use GUI

## Preparation
### Kindle account
First of all, go to [Amazon's  Manage Your Content and Devices ](https://amazon.com/mn/dcw/myx.html). In `Settings` tab find `Approved Personal Document E-mail List` and add your gmail address. Also note your kindle address from `Send-to-Kindle E-Mail Settings` section.

### Gmail account

If you haven't already, enable 2 factor authentication. Then visit https://security.google.com/settings/security/apppasswords. At the bottom, click __Select app__, choose _Other_ and enter whatever name you want. You will get an app password (go to https://support.google.com/mail/answer/185833 for more details).

## Usage
### GUI
* On Windows, download latest release from https://github.com/prz3m/web2kindle/releases, unpack zip and run web2kindle.exe
* Or if you prefer running from source, run
  ```
  python main.py
  ```
* click _Settings_ button and enter you gmail login and kindle e-mail address
* paste article's url or select _file_ and select file from your disk
* check _send_ if you want to send the article to your kindle (otherwise you can send mobi file manually), check _clean_ if you want to delete temporary files
* click _Go!_ button
* A progress bar will appear and after some time black console window prompting for your gmail password. Enter app password which you've generated. You will be asked if you want to store your password in a keyring (operating system's place to store passwords), so that you will not have to enter it the next time. If you don't want, type `n`, otherwise type `y`.
* That's all!

The program minimizes itself to tray.
  
### command line
Firstly, modify web2kindle.conf file:
```
[web2kindle]
gmail_login = your_login
kindle_address = your_kindle@kindle.com
```
or delete this file. If you do, you will be prompted for gmail login and kindle address when running the script.

* Convert article to mobi
  ```
  python web2kindle.py -u http://article-url.com
  ```

* Convert downloaded html to mobi
  ```
  python web2kindle.py -p C:\path\to\file.html
  ```

* Convert and send to Kindle
  ```
  python web2kindle.py -u http://article-url.com -s
  ```
  You will be prompted for your gmail password. Enter app password which you've generated. You will be asked if you want to store your password in a keyring (operating system's place to store passwords), so that you will not have to enter it the next time. If you don't want, type `n`, otherwise type `y`.
