// Main (sandboxed) thread. Has access to the Figma document API but no DOM.
// Talks to ui.html over postMessage. Keep this file dependency-free plain JS
// (no build step) so the plugin can be loaded straight via
// Plugins -> Development -> Import plugin from manifest.

figma.showUI(__html__, { width: 400, height: 640, themeColors: false });

// No figma.payments here: Figma Payments (Stripe Connect) doesn't support
// payouts to India, so unlocking is handled entirely in ui.html via a
// Gumroad license key checked against /api/verify-license, with the
// unlocked flag stored in the UI iframe's own localStorage. This thread
// never needs to know the payment/unlock state -- ui.html only sends an
// insert-icon message once it has already decided the icon is allowed.

function placeAndSelect(node) {
  node.x = Math.round(figma.viewport.center.x - node.width / 2);
  node.y = Math.round(figma.viewport.center.y - node.height / 2);
  figma.currentPage.selection = [node];
  figma.viewport.scrollAndZoomIntoView([node]);
}

async function insertIconSvg(svg, sizePx) {
  const node = figma.createNodeFromSvg(svg);
  // ui.html always sends 24 here regardless of how big the icon grid tiles
  // render on screen, that's just a UI display size, unrelated to paste
  // size. Resize unconditionally (not just when it looks off) so every
  // pasted icon is exactly 24x24 no matter what size Figma happened to
  // parse the SVG at.
  const size = Number(sizePx) || 24;
  node.resize(size, size);
  placeAndSelect(node);
}

async function insertIconPng(bytes, sizePx) {
  const size = Number(sizePx) || 24;
  const image = figma.createImage(bytes);
  const rect = figma.createRectangle();
  rect.resize(size, size);
  rect.fills = [{ type: "IMAGE", imageHash: image.hash, scaleMode: "FILL" }];
  placeAndSelect(rect);
}

figma.ui.onmessage = async (msg) => {
  try {
    if (msg.type === "insert-icon") {
      await insertIconSvg(msg.svg, msg.size);
      figma.ui.postMessage({ type: "insert-icon-done" });
      return;
    }

    if (msg.type === "insert-icon-png") {
      await insertIconPng(new Uint8Array(msg.bytes), msg.size);
      figma.ui.postMessage({ type: "insert-icon-done" });
      return;
    }

    if (msg.type === "close") {
      figma.closePlugin();
      return;
    }
  } catch (err) {
    figma.ui.postMessage({ type: "error", message: String((err && err.message) || err) });
  }
};
