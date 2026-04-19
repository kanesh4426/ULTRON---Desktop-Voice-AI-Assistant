export function createId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function createInitials(name: string, fallback = 'GU'): string {
  if (!name?.trim()) {
    if (typeof window !== 'undefined' && (window as any).process?.env?.NODE_ENV !== 'production') {
      console.warn('createInitials called with empty name, using fallback:', fallback);
    }
    return fallback;
  }
  const initials = name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return initials || fallback;
}

export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}
