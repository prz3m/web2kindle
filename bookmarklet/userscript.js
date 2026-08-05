// ==UserScript==
// @name         Send to Kindle
// @namespace    web2kindle
// @version      2.0
// @description  Queue articles and send collections with web2kindle
// @match        *://*/*
// @grant        unsafeWindow
// @grant        GM.xmlHttpRequest
// @connect      127.0.0.1
// ==/UserScript==

(() => {
  "use strict";

  const API_BASE_URL = "http://127.0.0.1:8666/";
  let dismissTimer;
  let operationInProgress = false;
  let statusElement;

  const getStatusElement = () => {
    if (statusElement?.isConnected) return statusElement;

    statusElement = document.createElement("div");
    statusElement.setAttribute("role", "status");
    statusElement.setAttribute("aria-live", "polite");
    Object.assign(statusElement.style, {
      background: "white",
      borderRadius: "10px",
      boxShadow: "3px 3px 10px 1px rgba(40, 40, 40, 0.3)",
      color: "rgb(40, 40, 40)",
      fontFamily: "sans-serif",
      left: "20px",
      padding: "20px",
      position: "fixed",
      textAlign: "center",
      top: "20px",
      width: "230px",
      zIndex: "9999",
    });
    document.body.appendChild(statusElement);
    return statusElement;
  };

  const showStatus = (message, { error = false, dismissAfter } = {}) => {
    clearTimeout(dismissTimer);
    const element = getStatusElement();
    element.textContent = message;
    element.style.color = error ? "red" : "rgb(40, 40, 40)";

    if (dismissAfter) {
      dismissTimer = setTimeout(() => element.remove(), dismissAfter);
    }
  };

  const showFailure = (error) => {
    console.error(error);
    const status = error instanceof Error ? error.cause?.status : undefined;
    const message = status
      ? `web2kindle returned HTTP ${status}`
      : "Cannot reach web2kindle. Is the server running?";
    showStatus(message, { error: true });
  };

  const buildApiUrl = (path, pageUrl) => {
    const url = new URL(path, API_BASE_URL);
    if (pageUrl) url.searchParams.set("page", pageUrl);
    return url.href;
  };

  const post = async (path, { body, pageUrl } = {}) => {
    const response = await GM.xmlHttpRequest({
      method: "POST",
      url: buildApiUrl(path, pageUrl),
      responseType: "json",
      ...(body === undefined
        ? {}
        : {
            data: JSON.stringify(body),
            headers: { "Content-Type": "application/json" },
          }),
    });

    if (response.status < 200 || response.status >= 300) {
      throw new Error(`HTTP ${response.status}`, { cause: response });
    }
    return response.response;
  };

  const runOperation = async ({ progressMessage, operation, successMessage }) => {
    if (operationInProgress) {
      showStatus("Another web2kindle operation is already in progress");
      return;
    }

    operationInProgress = true;
    showStatus(progressMessage);
    try {
      const result = await operation();
      showStatus(successMessage(result), { dismissAfter: 2000 });
    } catch (error) {
      showFailure(error);
    } finally {
      operationInProgress = false;
    }
  };

  const addArticle = () =>
    runOperation({
      progressMessage: "Adding to Kindle queue...",
      operation: () =>
        post("queue", {
          body: { document: document.documentElement.innerHTML },
          pageUrl: location.href,
        }),
      successMessage: (result) => `Added: ${result.title}`,
    });

  const sendQueue = () =>
    runOperation({
      progressMessage: "Sending Kindle queue...",
      operation: () => post("send"),
      successMessage: (result) =>
        result.status === "empty"
          ? "Kindle queue is empty"
          : `Sent ${result.article_count} article(s)`,
    });

  const sendNow = () =>
    runOperation({
      progressMessage: "Sending article to Kindle...",
      operation: () =>
        post("send-now", {
          body: { document: document.documentElement.innerHTML },
          pageUrl: location.href,
        }),
      successMessage: () => "Sent to Kindle",
    });

  unsafeWindow.addEventListener("send-to-kindle", addArticle);
  unsafeWindow.addEventListener("send-kindle-queue", sendQueue);
  unsafeWindow.addEventListener("send-to-kindle-now", sendNow);
})();
