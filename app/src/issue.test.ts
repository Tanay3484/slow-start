import { describe, expect, it } from "vitest";
import { issueUrl } from "./issue";

describe("issueUrl", () => {
  it("opens the import form with no fields when there is no report", () => {
    const url = new URL(issueUrl());
    expect(url.pathname).toBe("/Tanay3484/slow-start/issues/new");
    expect(url.searchParams.get("template")).toBe("import-problem.yml");
    expect(url.searchParams.has("app_said")).toBe(false);
  });
  it("fills in the file names and what the app said, and nothing else", () => {
    const url = new URL(
      issueUrl({ kind: "steps", files: ["Daily activity metrics.csv"], said: "Read 1,028 days (Google Fit daily summary)." }),
    );
    expect(url.searchParams.get("title")).toBe("[import] Steps: Daily activity metrics.csv");
    expect(url.searchParams.get("file")).toBe("Daily activity metrics.csv");
    expect(url.searchParams.get("app_said")).toBe("Read 1,028 days (Google Fit daily summary).");
    expect([...url.searchParams.keys()].sort()).toEqual(["app_said", "file", "template", "title"]);
  });
  it("keeps a long message short enough for a URL", () => {
    const url = new URL(issueUrl({ kind: "workouts", files: [], said: "x".repeat(5000) }));
    expect(url.searchParams.get("app_said")!.length).toBe(1500);
  });
});
