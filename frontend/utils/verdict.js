/**
 * Derives a verdict color class from a verdict object.
 * - "green"  → all rules returned 0 (no violation)
 * - "yellow" → no rule returned 2, but at least one returned 1
 * - "red"    → at least one rule returned 2
 * - "pending"→ verdict is null / not yet available
 */
export function verdictColor(verdict, rules) {
  if (!verdict) return "pending";

  // Collect numeric violation levels for each rule (ignore 'details')
  const levels = rules.map((r) => verdict[String(r.id)] ?? 0);

  if (levels.some((v) => v === 2)) return "red";
  if (levels.some((v) => v === 1)) return "yellow";
  return "green";
}

/**
 * Returns a human-readable label for a violation level.
 */
export function violationLabel(level) {
  return ["No violation", "Possible violation", "Clear violation"][level] ?? "Unknown";
}
