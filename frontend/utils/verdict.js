/**
 * Derives a verdict color class from a verdict object.
 * Verdict keys from the backend are policy_rule_index values (1, 2, 3...) as strings.
 *
 * - "green"   → all rules returned 0 (no violation)
 * - "yellow"  → no rule returned 2, but at least one returned 1
 * - "red"     → at least one rule returned 2
 * - "error"   → the moderation chain failed server-side (verdict.error is set) —
 *               NOT the same as "no violation found", so it must never fall
 *               through to green just because there are no numeric rule keys.
 * - "pending" → verdict is null / not yet available
 */
export function verdictColor(verdict, rules) {
  if (!verdict) return "pending";
  if (verdict.error) return "error";

  const levels = rules.map((r) => verdict[String(r.policy_rule_index)] ?? 0);

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
