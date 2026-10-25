// A link that opens the repo's "Import problem" issue form with what the app saw already filled in.
// Only file names and the app's own summary go in the link: never the file's contents.
export const REPO = "https://github.com/Tanay3484/slow-start";
const MAX_SAID = 1500;

export interface ImportReport {
  kind: "steps" | "workouts";
  files: string[];
  /** What the app told the person: the summary line, or the error. */
  said: string;
}

export function issueUrl(report?: ImportReport): string {
  const q = new URLSearchParams({ template: "import-problem.yml" });
  if (report) {
    const label = report.kind === "steps" ? "Steps" : "Workouts";
    const first = report.files[0] ?? "a file";
    q.set("title", `[import] ${label}: ${first}`);
    q.set("file", report.files.join(", "));
    q.set("app_said", report.said.slice(0, MAX_SAID));
  }
  return `${REPO}/issues/new?${q.toString()}`;
}
