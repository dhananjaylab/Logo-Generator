/**
 * Image URL resolution utilities
 */

/**
 * Resolve an image URL, handling both relative and absolute URLs
 */
export function resolveImageUrl(url: string | null | undefined): string | null {
  if (!url) {
    return null;
  }

  // If it's already an absolute URL, return it as-is
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }

  // If it's a data URL, return it as-is
  if (url.startsWith('data:')) {
    return url;
  }

  // If it's a relative path, resolve it relative to the API base URL
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  return `${apiUrl}${url}`;
}
