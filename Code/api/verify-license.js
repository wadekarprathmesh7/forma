// Vercel serverless function: POST /api/verify-license
//
// Verifies a Gumroad license key server-side. This has to happen on a
// server rather than straight from app.js: Gumroad's verify endpoint isn't
// reliably callable cross-origin from browser JS, and checking refund /
// dispute status here means a refunded purchase actually re-locks the app
// instead of trusting whatever the client says forever.
//
// Configure in the Vercel project's Settings -> Environment Variables:
//   GUMROAD_PRODUCT_ID         Preferred. Required by Gumroad for any
//                              product created on/after Jan 9, 2023.
//   GUMROAD_PRODUCT_PERMALINK  Fallback, only for older products (the
//                              short slug from the product's URL, e.g.
//                              "forma" from gumroad.com/l/forma).
// Set at least one of the two -- GUMROAD_PRODUCT_ID takes priority if both
// are present.

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ valid: false, reason: "Method not allowed." });
    return;
  }

  const licenseKey = ((req.body && req.body.licenseKey) || "").trim();
  if (!licenseKey) {
    res.status(400).json({ valid: false, reason: "Missing license key." });
    return;
  }

  const productId = process.env.GUMROAD_PRODUCT_ID;
  const productPermalink = process.env.GUMROAD_PRODUCT_PERMALINK;
  if (!productId && !productPermalink) {
    res.status(500).json({ valid: false, reason: "Server isn't configured yet." });
    return;
  }

  const params = new URLSearchParams({ license_key: licenseKey });
  if (productId) params.set("product_id", productId);
  else params.set("product_permalink", productPermalink);

  let data;
  try {
    const gumroadRes = await fetch("https://api.gumroad.com/v2/licenses/verify", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: params.toString(),
    });
    data = await gumroadRes.json();
  } catch (err) {
    res.status(502).json({ valid: false, reason: "Couldn't reach the license server. Try again in a moment." });
    return;
  }

  if (!data || !data.success) {
    res.status(200).json({ valid: false, reason: "License key not found." });
    return;
  }

  const purchase = data.purchase || {};
  if (purchase.refunded || purchase.disputed || purchase.chargebacked) {
    res.status(200).json({ valid: false, reason: "This purchase was refunded or disputed." });
    return;
  }

  res.status(200).json({ valid: true });
};
