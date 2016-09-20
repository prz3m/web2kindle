# web2kindle

Send articles to your kindle.

## Why?

There are many apps (e.g. Send to Kindle browser extension by Amazon or Tinderizer bookmarklet) which do the same. The problem begins if the article has many images in it - they are often not included. With this script, all the images are attached and finally you can read articles from waitbutwhy.com on your Kindle.

## Dependencies
* [python-readability](https://github.com/buriy/python-readability) - it handles scraping article from the webpage and is pretty   neat
* [yagmail](https://github.com/kootenpv/yagmail) - sending emails from gmail account

## Preparation
First of all, go to [Amazon's  Manage Your Content and Devices ](amazon.com/mn/dcw/myx.html). In `Settings` tab find `Approved Personal Document E-mail List` and add your gmail address. Also note your kindle address from `Send-to-Kindle E-Mail Settings` section.

Modify web2kindle.conf file:
```[web2kindle]
gmail_login = your_login
kindle_address = your_kindle@kindle.com
```
or delete this file. If you do, you will be prompted for gmail login and kindle address.

## Usage
* Convert article to mobi
  `python web2kindle.py -u http://article-url.com`
* Convert downloaded html to mobi
  `python web2kindle.py -p C:\path\to\file.html`
* Convert and send to Kindle
  `python web2kindle.py -u http://article-url.com -s`
