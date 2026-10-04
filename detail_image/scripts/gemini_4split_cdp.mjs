import fs from "fs";
import path from "path";

const PAGE = process.argv[2];
const SRC = process.argv[3];
const DEST = process.argv[4];
const PROMPT =
  "상세페이지에 넣을 이미지를 만들어줘. 기존 이미지에 있는 상품은 절대 변경하지말고, 감성 있는 4분할 이미지 만들어줘. 글자, 숫자, 라벨, 로고는 넣지 마.";

function connect(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    let id = 0;
    const pending = new Map();
    ws.addEventListener("open", () => resolve({
      ws,
      send(method, params = {}, timeout = 20000) {
        const msgId = ++id;
        return new Promise((res, rej) => {
          const t = setTimeout(() => {
            pending.delete(msgId);
            rej(new Error("timeout " + method));
          }, timeout);
          pending.set(msgId, { res, rej, t });
          ws.send(JSON.stringify({ id: msgId, method, params }));
        });
      },
    }));
    ws.addEventListener("message", (ev) => {
      const msg = JSON.parse(ev.data);
      if (!msg.id || !pending.has(msg.id)) return;
      const p = pending.get(msg.id);
      clearTimeout(p.t);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(JSON.stringify(msg.error)));
      else p.res(msg.result);
    });
    ws.addEventListener("error", () => reject(new Error("ws error")));
  });
}

async function evalJs(c, expression, timeout = 20000) {
  const r = await c.send("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  }, timeout);
  if (r.exceptionDetails) {
    throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 400));
  }
  return r.result?.value;
}

async function clickAria(c, labels) {
  const list = Array.isArray(labels) ? labels : [labels];
  for (const label of list) {
    const ok = await evalJs(c, `(() => {
      const el = [...document.querySelectorAll('button, [role=button]')]
        .find(b => (b.getAttribute('aria-label')||'') === ${JSON.stringify(label)} && b.offsetParent !== null);
      if (!el) return false;
      el.click();
      return true;
    })()`);
    if (ok) return;
  }
  throw new Error("no button " + list.join("|"));
}

async function clickText(c, texts) {
  const list = Array.isArray(texts) ? texts : [texts];
  for (const text of list) {
    const ok = await evalJs(c, `(() => {
      const el = [...document.querySelectorAll('button, [role=menuitem], div, span')]
        .find(b => (b.innerText||'').trim() === ${JSON.stringify(text)});
      if (!el) return false;
      el.click();
      return true;
    })()`);
    if (ok) return;
  }
  throw new Error("no text " + list.join("|"));
}

async function setFile(c, filePath) {
  const doc = await c.send("DOM.getDocument", { depth: 2 });
  const found = await c.send("DOM.querySelector", {
    nodeId: doc.root.nodeId,
    selector: "input[type=file]",
  });
  if (!found.nodeId) throw new Error("no file input");
  await c.send("DOM.setFileInputFiles", {
    nodeId: found.nodeId,
    files: [filePath],
  });
}

const c = await connect(PAGE);
try {
  await c.send("Page.navigate", { url: "https://gemini.google.com/app" });
  await new Promise((r) => setTimeout(r, 3500));
  let hello = await evalJs(c, "document.body.innerText.slice(0, 600)");
  if (hello.includes("Sign in") || hello.includes("로그인")) {
    console.log("LOGIN_REQUIRED");
    console.log(hello.slice(0, 300));
    process.exit(3);
  }
  if (hello.includes("일일 한도") || hello.includes("사용량 한도")) {
    console.log("QUOTA");
    console.log(hello);
    process.exit(2);
  }
  try {
    await clickAria(c, ["파일 및 도구 추가", "Add files and tools", "Add files"]);
  } catch {
    await clickText(c, ["이미지 만들기", "Create image", "이미지"]);
  }
  await new Promise((r) => setTimeout(r, 600));
  try {
    await clickText(c, ["이미지 만들기", "Create image"]);
  } catch {
    /* already in image mode */
  }
  await new Promise((r) => setTimeout(r, 500));
  await clickAria(c, ["파일 및 도구 추가", "Add files and tools", "Add files"]);
  await new Promise((r) => setTimeout(r, 400));
  await setFile(c, SRC);
  await new Promise((r) => setTimeout(r, 400));
  const added = await evalJs(c, `(() => {
    const el = [...document.querySelectorAll('button, [role=menuitem], div, span')]
      .find(b => (b.innerText||'').trim() === '이미지 추가');
    if (!el) return false;
    el.click();
    return true;
  })()`);
  console.log("image-add-click", added);
  await new Promise((r) => setTimeout(r, 1500));
  const filled = await evalJs(c, `(() => {
    const box = document.querySelector('textarea');
    if (!box) return 'no-textarea';
    box.focus();
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    setter.call(box, ${JSON.stringify(PROMPT)});
    box.dispatchEvent(new Event('input', { bubbles: true }));
    return box.value.length;
  })()`);
  console.log("filled", filled);
  await new Promise((r) => setTimeout(r, 300));
  await clickAria(c, "보내기");
  const start = Date.now();
  let saved = false;
  while (Date.now() - start < 90000) {
    await new Promise((r) => setTimeout(r, 3000));
    const state = await evalJs(c, `(() => {
      const text = document.body.innerText || '';
      if (text.includes('일일 한도') || text.includes('사용량 한도')) return {quota:true, text:text.slice(0,300)};
      const img = [...document.querySelectorAll('img')].find(im => (im.src||'').includes('banana') && im.naturalWidth >= 512);
      return {quota:false, src: img ? img.src : ''};
    })()`);
    if (state.quota) {
      console.log("QUOTA_AFTER");
      console.log(state.text);
      process.exit(2);
    }
    if (state.src) {
      const b64 = await evalJs(c, `fetch(${JSON.stringify(state.src)}).then(r => r.arrayBuffer()).then(buf => {
        const bytes = new Uint8Array(buf);
        let s = '';
        const chunk = 0x8000;
        for (let i = 0; i < bytes.length; i += chunk) s += String.fromCharCode(...bytes.subarray(i, i + chunk));
        return btoa(s);
      })`, 30000);
      fs.writeFileSync(DEST, Buffer.from(b64, "base64"));
      console.log("OK", fs.statSync(DEST).size);
      saved = true;
      break;
    }
  }
  if (!saved) {
    const tail = await evalJs(c, "document.body.innerText.slice(0, 500)");
    console.log("NO_IMAGE");
    console.log(tail);
    process.exit(1);
  }
} finally {
  c.ws.close();
}
