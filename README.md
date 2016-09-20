# web2kindle

Send articles to your kindle.

## Why?

There are many apps (e.g. Send to Kindle browser extension by Amazon or Tinderizer bookmarklet) which do the same. The problem begins if the article has many images in it -- they are often not included. With this script, all the images are attached and finally you can read articles from waitbutwhy.com on your Kindle.

## Dependencies
* [kindlegen](https://www.amazon.com/gp/feature.html?ie=UTF8&docId=1000765211) -- converts html to mobi. Download and put `kindlegen.exe` in the same directory as the script (in Linux modify line 95 of `web2kindle.py`: replace `kindlegen.exe` with `kindlegen` -- I will correct this inconvenience soon)
* [python-readability](https://github.com/buriy/python-readability) -- handles scraping article from the webpage and is pretty   neat
* [yagmail](https://github.com/kootenpv/yagmail) -- sending emails from gmail

## Preparation
First of all, go to [Amazon's  Manage Your Content and Devices ](amazon.com/mn/dcw/myx.html). In `Settings` tab find `Approved Personal Document E-mail List` and add your gmail address. Also note your kindle address from `Send-to-Kindle E-Mail Settings` section.

Modify web2kindle.conf file:
```
[web2kindle]
gmail_login = your_login
kindle_address = your_kindle@kindle.com
```
or delete this file. If you do, you will be prompted for gmail login and kindle address when running the script.

## Usage
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
  You will be prompted for your gmail password. If you use 2 factor authentication (and you should), you must generate [App Pasword](#app-password).
  
  (Sometimes Google can block web2kindle from using your account. If it's the case, consider enabling 2 factor authentication and generating App Password)
  
### App Pasword

Visit https://support.google.com/mail/answer/185833 -> "How to generate an App password"

At the bottom, click __Select app__, choose _Other_ and enter whatever name you want. You will get a password.

Go to https://security.google.com/settings/security/apppasswords for more details.
