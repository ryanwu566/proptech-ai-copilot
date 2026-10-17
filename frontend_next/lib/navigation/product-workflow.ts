/** Pure product URL state; callers own history and view transitions. */
export function isPropertyWorkflow(search: string): boolean {
  return new URLSearchParams(search).get("workflow") === "property";
}

/** Return an independent URL, changing only the workflow query parameter. */
export function setProductWorkflow(href: string, workflow: "property" | null): URL {
  const url = new URL(href);
  if (workflow === null) url.searchParams.delete("workflow");
  else url.searchParams.set("workflow", workflow);
  return url;
}
