type GroupKeys<T extends Record<string, Record<string, string>>> = {
  [P in keyof T & string]: `${P}.${keyof T[P] & string}`
}[keyof T & string];

// Expand shared prefixes once; preserve literal key types for exhaustive resources.
export function expandCopyGroups<T extends Record<string, Record<string, string>>>(groups: T): Record<GroupKeys<T>, string> {
  return Object.fromEntries(Object.entries(groups).flatMap(([prefix, values]) => Object.entries(values).map(([key, value]) => [`${prefix}.${key}`, value]))) as Record<GroupKeys<T>, string>;
}
