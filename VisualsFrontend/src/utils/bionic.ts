/**
 * Bionic Reading engine — bolds the first 30-50% of each word
 * to guide the reader's eye and increase reading speed.
 */
export function toBionic(text: string): string {
  return text
    .split(/(\s+)/)
    .map(chunk => {
      if (/^\s+$/.test(chunk)) return chunk;
      const word = chunk;
      if (word.length <= 1) return word;
      const mid = word.length <= 3 ? 1 : Math.ceil(word.length * 0.45);
      const bold = word.slice(0, mid);
      const rest = word.slice(mid);
      return `<b class="bionic-fixation">${bold}</b>${rest}`;
    })
    .join('');
}

/**
 * React-safe wrapper: returns raw HTML string.
 * Use with dangerouslySetInnerHTML={{ __html: bionicHtml(text) }}
 */
export function bionicHtml(text: string, enabled: boolean): string {
  return enabled ? toBionic(text) : text;
}
