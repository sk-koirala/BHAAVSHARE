// Client-side validation mirroring backend schemas/entities.py policy.
// Keep both sides in sync — if backend policy changes, update this file.

export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function validateEmail(email) {
  if (!email) return 'Email is required.';
  if (email.length > 200) return 'Email is too long.';
  if (!EMAIL_RE.test(email)) return 'Please enter a valid email address.';
  return null;
}

export function validateFullName(name) {
  if (!name) return 'Full name is required.';
  const trimmed = name.trim();
  if (trimmed.length < 2) return 'Name must be at least 2 characters.';
  if (trimmed.length > 100) return 'Name is too long.';
  // Allow Latin + Devanagari letters, spaces, hyphen, apostrophe, period
  if (!/^[A-Za-z\u0900-\u097F\s\.'-]+$/.test(trimmed)) {
    return 'Name contains invalid characters.';
  }
  return null;
}

/**
 * Returns an object describing password strength:
 * { score: 0..5, label, color, issues: string[] }
 * score = number of satisfied rules from the policy:
 *   length>=8, uppercase, lowercase, digit, special-char (bonus).
 */
export function scorePassword(pw) {
  const issues = [];
  const rules = {
    length: (pw || '').length >= 8,
    upper: /[A-Z]/.test(pw || ''),
    lower: /[a-z]/.test(pw || ''),
    digit: /\d/.test(pw || ''),
    special: /[^A-Za-z0-9]/.test(pw || ''),
  };
  if (!rules.length) issues.push('At least 8 characters');
  if (!rules.upper) issues.push('One uppercase letter (A–Z)');
  if (!rules.lower) issues.push('One lowercase letter (a–z)');
  if (!rules.digit) issues.push('One digit (0–9)');

  const score = Object.values(rules).filter(Boolean).length; // 0..5
  const label =
    score <= 1 ? 'Very weak' :
    score === 2 ? 'Weak' :
    score === 3 ? 'Fair' :
    score === 4 ? 'Strong' : 'Very strong';
  const color =
    score <= 1 ? 'bg-red-500' :
    score === 2 ? 'bg-orange-500' :
    score === 3 ? 'bg-amber-500' :
    score === 4 ? 'bg-emerald-500' : 'bg-cyan-400';

  return { score, label, color, issues, rules, valid: issues.length === 0 };
}

export function validateSignup({ email, password, confirm, fullName }) {
  const nameErr = validateFullName(fullName);
  if (nameErr) return nameErr;
  const emailErr = validateEmail(email);
  if (emailErr) return emailErr;
  const pw = scorePassword(password);
  if (!pw.valid) return `Password requirements not met: ${pw.issues.join(', ')}.`;
  if (password !== confirm) return 'Passwords do not match.';
  return null;
}

export function validateLogin({ email, password }) {
  const emailErr = validateEmail(email);
  if (emailErr) return emailErr;
  if (!password) return 'Password is required.';
  return null;
}
