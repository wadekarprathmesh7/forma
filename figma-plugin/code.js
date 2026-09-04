// Main (sandboxed) thread. Has access to the Figma document API but no DOM.
// Talks to ui.html over postMessage. Keep this file dependency-free plain JS
// (no build step) so the plugin can be loaded straight via
// Plugins -> Development -> Import plugin from manifest.

figma.showUI(__html__, { width: 400, height: 640, themeColors: false });

async function currentPaymentStatus() {
  // figma.payments is undefined when payments aren't configured for this
  // plugin yet (e.g. during local dev before the plugin has been created as
  // a draft in the Figma dashboard). Treat that as "paid" locally so you can
  // build/test the full UI before payments are wired up for real.
  if (!figma.payments) return { type: "paid", devFallback: true };
  return figma.payments.status;
}

function placeAndSelect(node) {
  node.x = Math.round(figma.viewport.center.x - node.width / 2);
  node.y = Math.round(figma.viewport.center.y - node.height / 2);
  figma.currentPage.selection = [node];
  figma.viewport.scrollAndZoomIntoView([node]);
}

async function insertIconSvg(svg, sizePx) {
  const node = figma.createNodeFromSvg(svg);
  const size = Number(sizePx) || 24;
  // Icons are authored on a 24x24 grid; scale the whole frame uniformly so
  // strokes/paths stay proportional rather than distorting non-uniformly.
  if (size !== node.width || size !== node.height) {
    node.resize(size, size);
  }
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

    if (msg.type === "get-payment-status") {
      const status = await currentPaymentStatus();
      figma.ui.postMessage({ type: "payment-status", status });
      return;
    }

    if (msg.type === "checkout") {
      if (!figma.payments) {
        // Local-dev fallback: nothing to check out against yet.
        figma.ui.postMessage({ type: "payment-status", status: { type: "paid", devFallback: true } });
        return;
      }
      await figma.payments.initiateCheckoutAsync({ interstitial: "PAID_FEATURE" });
      const status = await currentPaymentStatus();
      figma.ui.postMessage({ type: "payment-status", status });
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

(async () => {
  const status = await currentPaymentStatus();
  figma.ui.postMessage({ type: "payment-status", status });
})();
