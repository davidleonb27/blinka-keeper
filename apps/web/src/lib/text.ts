/** Lowercase without diacritics, for accent-insensitive matching ("Café" matches "cafe"). */
export function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}
