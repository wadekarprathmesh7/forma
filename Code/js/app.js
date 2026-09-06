(() => {
  "use strict";

  const svgCache = new Map(); // path -> raw svg text

  // ---------- Monetisation (matches the Figma plugin's model) ----------
  // Browsing every category, search, weight, and colour is unrestricted
  // for everyone. Downloading icons from the General category is free,
  // forever. Downloading from any other category requires a one-time
  // purchase, verified via a Gumroad license key against /api/verify-license
  // (see Code/api/verify-license.js). The unlocked flag is stored in
  // localStorage -- this is a client-side gate appropriate for a low-stakes
  // icon library, not a server-enforced download restriction.
  const FREE_CATEGORY = "general";
  const LICENSE_STORAGE_KEY = "forma_unlocked";
  // TODO: replace with the real Gumroad product checkout URL once created.
  const GUMROAD_CHECKOUT_URL = "https://REPLACE_ME.gumroad.com/l/forma";

  let unlockedThisSession = false; // fallback when localStorage is blocked

  function isUnlocked() {
    if (unlockedThisSession) return true;
    try {
      return localStorage.getItem(LICENSE_STORAGE_KEY) === "true";
    } catch {
      return false; // private browsing / storage blocked
    }
  }

  function setUnlocked() {
    unlockedThisSession = true;
    try {
      localStorage.setItem(LICENSE_STORAGE_KEY, "true");
    } catch {
      /* ignore -- unlock still applies for the rest of this page load */
    }
  }

  const state = {
    weightIndex: 0,
    colour: "#000000",
    category: CATEGORIES[0].slug,
    search: "",
    selectedIconSlug: null,
  };

  const els = {
    weightTrack: document.getElementById("weightTrack"),
    weightLabels: document.getElementById("weightLabels"),
    colourSwatches: document.getElementById("colourSwatches"),
    multiSwatch: document.getElementById("multiSwatch"),
    hexInput: document.getElementById("hexInput"),
    categoryList: document.getElementById("categoryList"),
    colourFilterBlock: document.getElementById("colourFilterBlock"),
    colourDisabledHint: document.getElementById("colourDisabledHint"),
    contentTitle: document.getElementById("contentTitle"),
    iconGrid: document.getElementById("iconGrid"),
    emptyState: document.getElementById("emptyState"),
    emptyStateText: document.getElementById("emptyStateText"),
    searchInput: document.getElementById("searchInput"),
    searchClear: document.getElementById("searchClear"),

    sidebar: document.getElementById("sidebar"),
    sidebarOverlay: document.getElementById("sidebarOverlay"),
    filterToggleBtn: document.getElementById("filterToggleBtn"),
    sidebarCloseBtn: document.getElementById("sidebarCloseBtn"),

    downloadOverlay: document.getElementById("downloadOverlay"),
    popupIconName: document.getElementById("popupIconName"),
    popupIconPreview: document.getElementById("popupIconPreview"),
    popupWeight: document.getElementById("popupWeight"),
    popupColourRow: document.getElementById("popupColourRow"),
    popupColourDot: document.getElementById("popupColourDot"),
    popupColourHex: document.getElementById("popupColourHex"),
    popupCategory: document.getElementById("popupCategory"),
    popupCloseBtn: document.getElementById("popupCloseBtn"),
    shareBtn: document.getElementById("shareBtn"),
    copyBtn: document.getElementById("copyBtn"),
    downloadSvgBtn: document.getElementById("downloadSvgBtn"),
    downloadPngBtn: document.getElementById("downloadPngBtn"),
    toast: document.getElementById("toast"),

    colourOverlay: document.getElementById("colourOverlay"),
    pickerSv: document.getElementById("pickerSv"),
    pickerSvThumb: document.getElementById("pickerSvThumb"),
    pickerHue: document.getElementById("pickerHue"),
    pickerHueThumb: document.getElementById("pickerHueThumb"),
    pickerSwatchPreview: document.getElementById("pickerSwatchPreview"),
    pickerFields: document.getElementById("pickerFields"),
    dropperBtn: document.getElementById("dropperBtn"),
    colourCancelBtn: document.getElementById("colourCancelBtn"),
    colourApplyBtn: document.getElementById("colourApplyBtn"),

    unlockOverlay: document.getElementById("unlockOverlay"),
    unlockCloseBtn: document.getElementById("unlockCloseBtn"),
    unlockBuyBtn: document.getElementById("unlockBuyBtn"),
    licenseInput: document.getElementById("licenseInput"),
    verifyLicenseBtn: document.getElementById("verifyLicenseBtn"),
    unlockError: document.getElementById("unlockError"),
  };

  // ---------- Mobile filter sidebar ----------

  function openSidebar() {
    els.sidebar.classList.add("open");
    els.sidebarOverlay.hidden = false;
    els.filterToggleBtn.setAttribute("aria-expanded", "true");
  }

  function closeSidebar() {
    els.sidebar.classList.remove("open");
    els.sidebarOverlay.hidden = true;
    els.filterToggleBtn.setAttribute("aria-expanded", "false");
  }

  els.filterToggleBtn.addEventListener("click", openSidebar);
  els.sidebarCloseBtn.addEventListener("click", closeSidebar);
  els.sidebarOverlay.addEventListener("click", closeSidebar);

  // ---------- Unlock modal ----------

  els.unlockBuyBtn.href = GUMROAD_CHECKOUT_URL;

  function openUnlockModal() {
    els.unlockError.hidden = true;
    els.unlockOverlay.hidden = false;
  }

  function closeUnlockModal() {
    els.unlockOverlay.hidden = true;
  }

  els.unlockCloseBtn.addEventListener("click", closeUnlockModal);
  els.unlockOverlay.addEventListener("click", (e) => {
    if (e.target === els.unlockOverlay) closeUnlockModal();
  });

  function showUnlockError(message) {
    els.unlockError.textContent = message;
    els.unlockError.hidden = false;
  }

  els.verifyLicenseBtn.addEventListener("click", async () => {
    const key = els.licenseInput.value.trim();
    if (!key) {
      showUnlockError("Enter your license key first.");
      return;
    }
    els.verifyLicenseBtn.disabled = true;
    els.verifyLicenseBtn.textContent = "Verifying…";
    els.unlockError.hidden = true;
    try {
      const res = await fetch("/api/verify-license", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ licenseKey: key }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.valid) {
        setUnlocked();
        closeUnlockModal();
        showToast("Unlocked! Thanks for your purchase.");
        render();
      } else {
        showUnlockError(data.reason || "That license key doesn't look valid.");
      }
    } catch {
      showUnlockError("Couldn't verify right now. Check your connection and try again.");
    } finally {
      els.verifyLicenseBtn.disabled = false;
      els.verifyLicenseBtn.textContent = "Verify";
    }
  });

  // ---------- Colour helpers ----------

  function hexToRgb(hex) {
    const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex.trim());
    if (!m) return null;
    return { r: parseInt(m[1], 16), g: parseInt(m[2], 16), b: parseInt(m[3], 16) };
  }

  function rgbToHex(r, g, b) {
    const to2 = (n) => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, "0");
    return `#${to2(r)}${to2(g)}${to2(b)}`.toUpperCase();
  }

  function rgbToHsl(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h, s, l = (max + min) / 2;
    if (max === min) { h = s = 0; }
    else {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = (g - b) / d + (g < b ? 6 : 0); break;
        case g: h = (b - r) / d + 2; break;
        default: h = (r - g) / d + 4;
      }
      h /= 6;
    }
    return { h: h * 360, s: s * 100, l: l * 100 };
  }

  function hslToRgb(h, s, l) {
    h = ((h % 360) + 360) % 360 / 360; s /= 100; l /= 100;
    let r, g, b;
    if (s === 0) { r = g = b = l; }
    else {
      const hue2rgb = (p, q, t) => {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1 / 6) return p + (q - p) * 6 * t;
        if (t < 1 / 2) return q;
        if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
        return p;
      };
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const p = 2 * l - q;
      r = hue2rgb(p, q, h + 1 / 3);
      g = hue2rgb(p, q, h);
      b = hue2rgb(p, q, h - 1 / 3);
    }
    return { r: r * 255, g: g * 255, b: b * 255 };
  }

  function setActiveColour(hex) {
    state.colour = hex.toUpperCase();
    document.documentElement.style.setProperty("--fill-0", state.colour);
    document.documentElement.style.setProperty("--stroke-0", state.colour);
    els.hexInput.value = state.colour;

    const matchingSwatch = els.colourSwatches.querySelector(`.swatch[data-colour="${state.colour}"]`);
    document.querySelectorAll(".swatch:not(.swatch-multi)").forEach((sw) => {
      sw.classList.toggle("active", sw === matchingSwatch);
    });
    if (matchingSwatch) {
      els.multiSwatch.classList.remove("active");
      els.multiSwatch.style.removeProperty("--sw");
    } else {
      els.multiSwatch.classList.add("active");
      els.multiSwatch.style.setProperty("--sw", state.colour);
    }

    if (state.selectedIconSlug) renderPopupPreview();
  }

  // ---------- Category list ----------

  function renderCategoryList() {
    els.categoryList.innerHTML = "";
    CATEGORIES.forEach((cat, i) => {
      const label = document.createElement("label");
      label.className = "category-item";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = "category";
      input.value = cat.slug;
      input.checked = cat.slug === state.category;
      input.addEventListener("change", () => {
        state.category = cat.slug;
        state.weightIndex = 0;
        clearSearch();
        renderWeightSlider();
        updateColourAvailability();
        render();
        closeSidebar();
      });
      const iconWrap = document.createElement("span");
      iconWrap.className = "category-icon";
      const iconPath = categoryIconPath(cat.slug);
      if (iconPath) {
        loadSvg(iconPath).then((svg) => { iconWrap.innerHTML = svg; }).catch(() => {});
      }

      const text = document.createElement("span");
      text.className = "label";
      text.textContent = cat.name;
      label.append(input, iconWrap, text);
      els.categoryList.appendChild(label);
    });
  }

  // ---------- Icon grid ----------

  async function loadSvg(path) {
    if (svgCache.has(path)) return svgCache.get(path);
    const res = await fetch(path);
    if (!res.ok) throw new Error(`Failed to load ${path}`);
    const text = await res.text();
    svgCache.set(path, text);
    return text;
  }

  function currentWeight() {
    const scheme = weightSchemeFor(state.category);
    return scheme[state.weightIndex] || scheme[0];
  }

  function iconsForView() {
    const all = getAllIcons();
    const weight = currentWeight();
    if (state.search.trim()) {
      const q = state.search.trim().toLowerCase();
      return all.filter((ic) => ic.weights.includes(weight) && ic.name.includes(q));
    }
    if (state.category === ALL_ICONS_SLUG) {
      return all
        .filter((ic) => ic.weights.includes(weight))
        .sort((a, b) => a.slug.localeCompare(b.slug));
    }
    return all.filter((ic) => ic.category === state.category && ic.weights.includes(weight));
  }

  async function render() {
    const weight = currentWeight();
    const searching = !!state.search.trim();
    const icons = iconsForView();

    els.contentTitle.hidden = searching;
    if (!searching) {
      const cat = CATEGORIES.find((c) => c.slug === state.category);
      els.contentTitle.textContent = cat ? cat.name : "";
    }

    if (icons.length === 0) {
      els.iconGrid.hidden = true;
      els.emptyState.hidden = false;
      els.emptyStateText.textContent = searching
        ? `No results found for "${state.search.trim()}"`
        : `No ${weight} weight icons in this category yet`;
      return;
    }

    els.iconGrid.hidden = false;
    els.emptyState.hidden = true;
    els.iconGrid.innerHTML = "";

    for (const icon of icons) {
      const path = iconSvgPath(icon.category, weight, icon.slug);
      const tile = document.createElement("button");
      tile.type = "button";
      tile.className = "icon-tile";
      tile.dataset.slug = icon.slug;
      tile.dataset.category = icon.category;
      if (icon.slug === state.selectedIconSlug) tile.classList.add("selected");

      const glyph = document.createElement("span");
      glyph.className = "icon-tile-glyph";
      const label = document.createElement("span");
      label.className = "icon-tile-label";
      label.textContent = icon.slug;

      tile.append(glyph, label);

      // Appended to the tile, not the glyph: the glyph's innerHTML gets
      // replaced wholesale once its SVG finishes loading below, which
      // would silently wipe out a badge nested inside it.
      if (icon.category !== FREE_CATEGORY && !isUnlocked()) {
        const badge = document.createElement("span");
        badge.className = "lock-badge";
        const img = document.createElement("img");
        img.src = "icons/security/light/lock.svg";
        img.alt = "";
        badge.appendChild(img);
        tile.appendChild(badge);
      }

      tile.addEventListener("click", () => selectIcon(icon, weight));
      els.iconGrid.appendChild(tile);

      loadSvg(path)
        .then((svg) => { glyph.innerHTML = svg; })
        .catch(() => { glyph.innerHTML = ""; });
    }
  }

  // ---------- Search ----------

  function clearSearch() {
    state.search = "";
    els.searchInput.value = "";
    els.searchClear.hidden = true;
  }

  els.searchInput.addEventListener("input", () => {
    state.search = els.searchInput.value;
    els.searchClear.hidden = state.search.length === 0;
    render();
  });

  els.searchClear.addEventListener("click", () => {
    clearSearch();
    els.searchInput.focus();
    render();
  });

  // ---------- Weight slider ----------

  const WEIGHT_LABELS = {
    light: "Light", medium: "Medium", bold: "Bold", filled: "Filled",
    colour: "Colour", bw: "B&W",
  };

  // The slider is rebuilt whenever the category changes, since Social uses
  // a 2-item Colour/Black & White scheme instead of the usual 4 weights.
  function renderWeightSlider() {
    const scheme = weightSchemeFor(state.category);
    els.weightTrack.innerHTML = "";
    els.weightLabels.innerHTML = "";
    scheme.forEach((w, i) => {
      const dot = document.createElement("button");
      dot.type = "button";
      dot.className = "weight-dot";
      dot.dataset.index = String(i);
      dot.setAttribute("role", "radio");
      dot.setAttribute("aria-label", WEIGHT_LABELS[w] || w);
      dot.addEventListener("click", () => {
        state.weightIndex = i;
        updateWeightSliderVisuals();
        render();
      });
      els.weightTrack.appendChild(dot);

      const span = document.createElement("span");
      span.dataset.weight = w;
      span.textContent = WEIGHT_LABELS[w] || w;
      span.addEventListener("click", () => {
        state.weightIndex = i;
        updateWeightSliderVisuals();
        render();
      });
      els.weightLabels.appendChild(span);
    });
    updateWeightSliderVisuals();
  }

  function updateWeightSliderVisuals() {
    els.weightTrack.querySelectorAll(".weight-dot").forEach((dot, i) => {
      const isActive = i === state.weightIndex;
      dot.classList.toggle("active", isActive);
      dot.setAttribute("aria-checked", String(isActive));
    });
    els.weightLabels.querySelectorAll("span").forEach((span, i) => {
      span.classList.toggle("active", i === state.weightIndex);
    });
  }

  // ---------- Colour swatches ----------

  // Social icons are fixed brand colours, so the whole colour picker is
  // disabled while that category is active.
  function updateColourAvailability() {
    const disabled = state.category === SOCIAL_CATEGORY_SLUG;
    els.colourFilterBlock.classList.toggle("disabled", disabled);
    els.hexInput.disabled = disabled;
    els.colourDisabledHint.hidden = !disabled;
  }

  els.colourSwatches.querySelectorAll(".swatch:not(.swatch-multi)").forEach((sw) => {
    sw.addEventListener("click", () => setActiveColour(sw.dataset.colour));
  });

  els.hexInput.addEventListener("change", () => {
    const val = els.hexInput.value.trim();
    const normalized = val.startsWith("#") ? val : `#${val}`;
    if (hexToRgb(normalized)) {
      setActiveColour(normalized);
    } else {
      els.hexInput.value = state.colour;
    }
  });

  els.multiSwatch.addEventListener("click", () => openColourPicker());

  // ---------- Icon selection + download popup ----------

  function selectIcon(icon, weight) {
    // Browsing (this click just reveals the preview/download popup) is
    // gated the same way inserting is gated in the Figma plugin: General
    // is free forever, everything else needs the one-time unlock.
    if (icon.category !== FREE_CATEGORY && !isUnlocked()) {
      openUnlockModal();
      return;
    }
    state.selectedIconSlug = icon.slug;
    document.querySelectorAll(".icon-tile").forEach((t) => {
      t.classList.toggle("selected", t.dataset.slug === icon.slug);
    });
    openDownloadPopup(icon, weight);
  }

  let currentPopupIcon = null;

  async function openDownloadPopup(icon, weight) {
    currentPopupIcon = { ...icon, weight };
    els.popupIconName.textContent = icon.slug;
    els.popupWeight.textContent = WEIGHT_LABELS[weight] || (weight.charAt(0).toUpperCase() + weight.slice(1));
    els.popupCategory.textContent = icon.categoryName;
    await renderPopupPreview();
    els.downloadOverlay.hidden = false;
  }

  async function renderPopupPreview() {
    if (!currentPopupIcon) return;
    // Social icons carry their own fixed brand colour; the "Colour:" meta
    // row (driven by the global colour picker) doesn't apply to them.
    const isSocial = currentPopupIcon.category === SOCIAL_CATEGORY_SLUG;
    els.popupColourRow.hidden = isSocial;
    if (!isSocial) {
      els.popupColourHex.textContent = state.colour;
      els.popupColourDot.style.background = state.colour;
    }
    const path = iconSvgPath(currentPopupIcon.category, currentPopupIcon.weight, currentPopupIcon.slug);
    try {
      const svg = await loadSvg(path);
      els.popupIconPreview.innerHTML = svg;
    } catch {
      els.popupIconPreview.innerHTML = "";
    }
  }

  function closeDownloadPopup() {
    els.downloadOverlay.hidden = true;
    state.selectedIconSlug = null;
    document.querySelectorAll(".icon-tile.selected").forEach((t) => t.classList.remove("selected"));
    currentPopupIcon = null;
  }

  els.popupCloseBtn.addEventListener("click", closeDownloadPopup);
  els.downloadOverlay.addEventListener("click", (e) => {
    if (e.target === els.downloadOverlay) closeDownloadPopup();
  });

  function resolvedSvgMarkup(rawSvg) {
    return rawSvg.replace(/var\(--(?:fill|stroke)-0,\s*#?[0-9a-fA-F]{3,6}\)/g, state.colour);
  }

  function showToast(msg) {
    els.toast.textContent = msg;
    els.toast.hidden = false;
    clearTimeout(showToast._t);
    showToast._t = setTimeout(() => { els.toast.hidden = true; }, 1600);
  }

  function triggerDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  els.downloadSvgBtn.addEventListener("click", async () => {
    if (!currentPopupIcon) return;
    const path = iconSvgPath(currentPopupIcon.category, currentPopupIcon.weight, currentPopupIcon.slug);
    const raw = await loadSvg(path);
    const resolved = resolvedSvgMarkup(raw);
    const blob = new Blob([resolved], { type: "image/svg+xml" });
    triggerDownload(blob, `${currentPopupIcon.slug}-${currentPopupIcon.weight}.svg`);
  });

  els.downloadPngBtn.addEventListener("click", async () => {
    if (!currentPopupIcon) return;
    const path = iconSvgPath(currentPopupIcon.category, currentPopupIcon.weight, currentPopupIcon.slug);
    const raw = await loadSvg(path);
    const resolved = resolvedSvgMarkup(raw);
    const size = 512;
    const svgBlob = new Blob([resolved], { type: "image/svg+xml" });
    const url = URL.createObjectURL(svgBlob);
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, size, size);
      canvas.toBlob((blob) => {
        triggerDownload(blob, `${currentPopupIcon.slug}-${currentPopupIcon.weight}.png`);
        URL.revokeObjectURL(url);
      }, "image/png");
    };
    img.src = url;
  });

  els.copyBtn.addEventListener("click", async () => {
    if (!currentPopupIcon) return;
    const path = iconSvgPath(currentPopupIcon.category, currentPopupIcon.weight, currentPopupIcon.slug);
    const raw = await loadSvg(path);
    const resolved = resolvedSvgMarkup(raw);
    try {
      await navigator.clipboard.writeText(resolved);
      showToast("SVG copied");
    } catch {
      showToast("Copy failed");
    }
  });

  els.shareBtn.addEventListener("click", async () => {
    if (!currentPopupIcon) return;
    const url = new URL(window.location.href);
    url.search = "";
    url.searchParams.set("icon", currentPopupIcon.slug);
    url.searchParams.set("category", currentPopupIcon.category);
    url.searchParams.set("weight", currentPopupIcon.weight);
    url.searchParams.set("colour", state.colour);
    try {
      await navigator.clipboard.writeText(url.toString());
      showToast("Link copied");
    } catch {
      showToast("Copy failed");
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (!els.downloadOverlay.hidden) closeDownloadPopup();
      if (!els.colourOverlay.hidden) closeColourPicker();
      if (els.sidebar.classList.contains("open")) closeSidebar();
    }
  });

  // ---------- Colour picker popup ----------

  let pickerHsv = { h: 0, s: 0, v: 0 };
  let pickerMode = "rgb";

  function openColourPicker() {
    const rgb = hexToRgb(state.colour) || { r: 0, g: 0, b: 0 };
    const hsl = rgbToHsl(rgb.r, rgb.g, rgb.b);
    const max = Math.max(rgb.r, rgb.g, rgb.b) / 255;
    const min = Math.min(rgb.r, rgb.g, rgb.b) / 255;
    pickerHsv = { h: hsl.h, s: max === 0 ? 0 : (1 - min / max) * 100, v: max * 100 };
    pickerMode = "rgb";
    document.querySelectorAll('input[name="colourMode"]').forEach((r) => { r.checked = r.value === "rgb"; });
    updatePickerUI();
    els.colourOverlay.hidden = false;
  }

  function closeColourPicker() {
    els.colourOverlay.hidden = true;
  }

  els.colourCancelBtn.addEventListener("click", closeColourPicker);
  els.colourOverlay.addEventListener("click", (e) => {
    if (e.target === els.colourOverlay) closeColourPicker();
  });
  els.colourApplyBtn.addEventListener("click", () => {
    const { r, g, b } = pickerRgb();
    setActiveColour(rgbToHex(r, g, b));
    closeColourPicker();
  });

  function pickerRgb() {
    const { h, s, v } = pickerHsv;
    const rgbFromHsv = hsvToRgb(h, s, v);
    return rgbFromHsv;
  }

  function hsvToRgb(h, s, v) {
    s /= 100; v /= 100;
    const c = v * s;
    const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    const m = v - c;
    let r, g, b;
    if (h < 60) [r, g, b] = [c, x, 0];
    else if (h < 120) [r, g, b] = [x, c, 0];
    else if (h < 180) [r, g, b] = [0, c, x];
    else if (h < 240) [r, g, b] = [0, x, c];
    else if (h < 300) [r, g, b] = [x, 0, c];
    else [r, g, b] = [c, 0, x];
    return { r: (r + m) * 255, g: (g + m) * 255, b: (b + m) * 255 };
  }

  function rgbToHsv(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    const d = max - min;
    let h = 0;
    if (d !== 0) {
      if (max === r) h = ((g - b) / d) % 6;
      else if (max === g) h = (b - r) / d + 2;
      else h = (r - g) / d + 4;
      h *= 60;
      if (h < 0) h += 360;
    }
    const s = max === 0 ? 0 : d / max;
    return { h, s: s * 100, v: max * 100 };
  }

  function updatePickerUI() {
    const { r, g, b } = pickerRgb();
    const hex = rgbToHex(r, g, b);
    const hsl = rgbToHsl(r, g, b);

    els.pickerSv.style.background = `linear-gradient(to top, #000, transparent), linear-gradient(to right, #fff, hsl(${pickerHsv.h}, 100%, 50%))`;
    els.pickerSvThumb.style.left = `${pickerHsv.s}%`;
    els.pickerSvThumb.style.top = `${100 - pickerHsv.v}%`;
    els.pickerHueThumb.style.left = `${(pickerHsv.h / 360) * 100}%`;
    els.pickerSwatchPreview.style.background = hex;

    renderPickerFields(r, g, b, hsl, hex);
  }

  function renderPickerFields(r, g, b, hsl, hex) {
    els.pickerFields.innerHTML = "";
    if (pickerMode === "rgb") {
      addField("R", Math.round(r), (val) => applyRgbField("r", val));
      addField("G", Math.round(g), (val) => applyRgbField("g", val));
      addField("B", Math.round(b), (val) => applyRgbField("b", val));
    } else if (pickerMode === "hsl") {
      addField("H", Math.round(hsl.h), (val) => applyHslField("h", val));
      addField("S", Math.round(hsl.s), (val) => applyHslField("s", val));
      addField("L", Math.round(hsl.l), (val) => applyHslField("l", val));
    } else {
      addField("Hex", hex.replace("#", ""), (val) => applyHexField(val), true);
    }
  }

  function addField(labelText, value, onCommit, isText) {
    const wrap = document.createElement("div");
    wrap.className = "picker-field";
    const label = document.createElement("label");
    label.textContent = labelText;
    const input = document.createElement("input");
    input.type = "text";
    input.inputMode = isText ? "text" : "numeric";
    input.value = value;
    input.addEventListener("change", () => onCommit(input.value));
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") input.blur(); });
    wrap.append(label, input);
    els.pickerFields.appendChild(wrap);
  }

  function applyRgbField(channel, val) {
    const n = Math.max(0, Math.min(255, Number(val) || 0));
    const rgb = pickerRgb();
    rgb[channel] = n;
    const hsv = rgbToHsv(rgb.r, rgb.g, rgb.b);
    pickerHsv = hsv;
    updatePickerUI();
  }

  function applyHslField(channel, val) {
    const rgb = pickerRgb();
    const hsl = rgbToHsl(rgb.r, rgb.g, rgb.b);
    const max = channel === "h" ? 360 : 100;
    hsl[channel] = Math.max(0, Math.min(max, Number(val) || 0));
    const newRgb = hslToRgb(hsl.h, hsl.s, hsl.l);
    pickerHsv = rgbToHsv(newRgb.r, newRgb.g, newRgb.b);
    updatePickerUI();
  }

  function applyHexField(val) {
    const normalized = val.startsWith("#") ? val : `#${val}`;
    const rgb = hexToRgb(normalized);
    if (!rgb) { updatePickerUI(); return; }
    pickerHsv = rgbToHsv(rgb.r, rgb.g, rgb.b);
    updatePickerUI();
  }

  document.querySelectorAll('input[name="colourMode"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      pickerMode = radio.value;
      updatePickerUI();
    });
  });

  function dragHandler(el, onMove) {
    function pointerToRatio(e) {
      const rect = el.getBoundingClientRect();
      const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
      return { x, y };
    }
    function move(e) {
      onMove(pointerToRatio(e));
    }
    el.addEventListener("pointerdown", (e) => {
      move(e);
      try { el.setPointerCapture(e.pointerId); } catch { /* ignore unrecognized pointer id */ }
      const onPointerMove = (ev) => move(ev);
      const onPointerUp = (ev) => {
        try { el.releasePointerCapture(ev.pointerId); } catch { /* already released */ }
        el.removeEventListener("pointermove", onPointerMove);
        el.removeEventListener("pointerup", onPointerUp);
      };
      el.addEventListener("pointermove", onPointerMove);
      el.addEventListener("pointerup", onPointerUp);
    });
  }

  dragHandler(els.pickerSv, ({ x, y }) => {
    pickerHsv.s = x * 100;
    pickerHsv.v = (1 - y) * 100;
    updatePickerUI();
  });

  dragHandler(els.pickerHue, ({ x }) => {
    pickerHsv.h = x * 360;
    updatePickerUI();
  });

  els.dropperBtn.addEventListener("click", async () => {
    if (!window.EyeDropper) {
      showToast("Eyedropper not supported in this browser");
      return;
    }
    try {
      const result = await new window.EyeDropper().open();
      const rgb = hexToRgb(result.sRGBHex);
      if (rgb) {
        pickerHsv = rgbToHsv(rgb.r, rgb.g, rgb.b);
        updatePickerUI();
      }
    } catch {
      /* user cancelled */
    }
  });

  // ---------- Deep-link from ?icon=&category=&weight=&colour= ----------

  function applyDeepLink() {
    const params = new URLSearchParams(window.location.search);
    const cat = params.get("category");
    const weight = params.get("weight");
    const colour = params.get("colour");
    const iconSlug = params.get("icon");

    if (cat && CATEGORIES.some((c) => c.slug === cat)) state.category = cat;
    const scheme = weightSchemeFor(state.category);
    if (weight && scheme.includes(weight)) state.weightIndex = scheme.indexOf(weight);
    if (colour && hexToRgb(colour)) setActiveColour(colour.startsWith("#") ? colour : `#${colour}`);

    renderWeightSlider();
    updateColourAvailability();

    return iconSlug;
  }

  // ---------- Init ----------

  async function init() {
    renderCategoryList();
    const deepLinkIcon = applyDeepLink();
    setActiveColour(state.colour);
    await render();

    if (deepLinkIcon) {
      const icon = getAllIcons().find(
        (ic) => ic.slug === deepLinkIcon && (state.category === ALL_ICONS_SLUG || ic.category === state.category)
      );
      if (icon && icon.weights.includes(currentWeight())) {
        selectIcon(icon, currentWeight());
      }
    }
  }

  init();
})();
