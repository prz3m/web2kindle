// ==UserScript==
// @name         Send to Kindle
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Send current page HTML to local kindle server
// @match        *://*/*
// @grant        unsafeWindow
// @grant        GM_xmlhttpRequest
// @connect      localhost
// ==/UserScript==

(function () {
  "use strict";

  function run() {
    var data = document.documentElement.innerHTML;
    var div = document.createElement("div");
    div.style.width = "230px";
    div.style.padding = "20px 0";
    div.style.background = "white";
    div.style.color = "rgb(40, 40, 40)";
    div.style.textAlign = "center";
    div.style.borderRadius = "10px";
    div.style.boxShadow = "3px 3px 10px 1px rgba(40, 40, 40, 0.3)";
    div.style.position = "fixed";
    div.style.top = "20px";
    div.style.left = "20px";
    div.style.zIndex = "9999999999999999";
    div.innerHTML = "Sending to kindle...";
    document.body.appendChild(div);

    GM_xmlhttpRequest({
      method: "POST",
      url: "http://localhost:8666/?page=" + encodeURIComponent(location.href),
      data: JSON.stringify({ document: data }),
      headers: { "Content-Type": "application/json" },
      onload: function () {
        div.innerHTML = "Success!";
        setTimeout(function () {
          if (div.parentNode) document.body.removeChild(div);
        }, 2000);
      },
      onerror: function (e) {
        console.error(e);
        div.innerHTML = "Error! Check console";
        div.style.color = "red";
      },
    });
  }

  unsafeWindow.addEventListener("send-to-kindle", run);
})();
