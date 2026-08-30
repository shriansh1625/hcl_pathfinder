/** WCAG contrast check for PathFinder dual-theme tokens. */
function hexToRgb(hex) {
  const h = hex.replace("#", "");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
function lum([r, g, b]) {
  const f = (c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
}
function ratio(fg, bg) {
  const l1 = lum(hexToRgb(fg));
  const l2 = lum(hexToRgb(bg));
  const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
  return (hi + 0.05) / (lo + 0.05);
}

const themes = {
  dark: {
    bg: "#12151c", surface: "#181c24", elevated: "#1e242e",
    paper: "#e8e2d4", paperStrong: "#f4efe4", mist: "#8b93a0",
    accent: "#8fba9c", accentHi: "#b3d0be", errorText: "#f4c2c2", btnText: "#0c0e12",
  },
  light: {
    bg: "#f3eee1", surface: "#f8f4e9", elevated: "#efe9da",
    paper: "#2c2822", paperStrong: "#1c1915", mist: "#6e675a",
    accent: "#4a7357", accentHi: "#3c5f49", errorText: "#8f4443", btnText: "#f8f4e9",
  },
};

const pairs = [
  ["paper", "bg", "body text"],
  ["paper", "surface", "body on card"],
  ["paperStrong", "surface", "heading on card"],
  ["mist", "bg", "muted text"],
  ["mist", "surface", "muted on card"],
  ["accent", "bg", "accent text"],
  ["accent", "surface", "accent on card"],
  ["accentHi", "surface", "accent-hi on card"],
  ["errorText", "surface", "error text"],
  ["btnText", "accent", "primary button label"],
];

let fail = 0;
for (const [theme, t] of Object.entries(themes)) {
  console.log(`\n=== ${theme.toUpperCase()} ===`);
  for (const [fg, bg, label] of pairs) {
    const r = ratio(t[fg], t[bg]);
    const aa = r >= 4.5 ? "AA" : r >= 3 ? "AA-large" : "FAIL";
    if (r < 4.5 && !/button label|accent-hi/.test(label)) fail++;
    if (r < 3) fail++;
    console.log(`${label.padEnd(24)} ${t[fg]} on ${t[bg]}  ${r.toFixed(2)}:1  ${aa}`);
  }
}
console.log(`\n${fail === 0 ? "PASS" : "REVIEW"}: ${fail} below-AA body-text pairs`);
