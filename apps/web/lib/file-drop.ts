export function fileMatchesAccept(file: File, accept?: string): boolean {
  if (!accept) return true;
  const name = file.name.toLowerCase();
  const type = file.type.toLowerCase();
  return accept.split(",").some((rule) => {
    const normalized = rule.trim().toLowerCase();
    if (!normalized) return false;
    if (normalized.startsWith(".")) return name.endsWith(normalized);
    if (normalized.endsWith("/*")) return type.startsWith(normalized.slice(0, -1));
    return type === normalized;
  });
}

export function firstMatchingFile(files: FileList | null | undefined, accept?: string): File | undefined {
  if (!files?.length) return undefined;
  return Array.from(files).find((file) => fileMatchesAccept(file, accept));
}
