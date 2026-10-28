/** The embedded renderer may be newer than the connected native Studio. */
export function nativeSupportMessage(kind: string, available?: string[]): string | null {
  return available && !available.includes(kind)
    ? '**Requires a newer Dashboard Studio version**\n\nThis visualization is unavailable on the connected instance. Its configuration is preserved.' : null;
}
