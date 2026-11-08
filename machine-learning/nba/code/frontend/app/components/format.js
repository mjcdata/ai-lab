export const fmt = (n, digits = 1) =>
  typeof n === "number"
    ? n.toLocaleString("en-US", {
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      })
    : "—";

