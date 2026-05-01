import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "./App";

describe("CivicClerk staff workspace", () => {
  afterEach(() => {
    window.history.replaceState({}, "", "/");
  });

  it("renders the CivicSuite staff shell and dashboard", () => {
    render(<App />);

    expect(screen.getByText("CivicSuite")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Good morning, City Clerk." })).toBeInTheDocument();
    expect(screen.getByText("Partial install")).toBeInTheDocument();
  });

  it("opens the meeting calendar and a meeting detail workspace", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /Meetings/ }));
    expect(screen.getByRole("heading", { name: "May 2026 clerk calendar" })).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: /City Council/ })[0]);
    expect(screen.getByRole("heading", { name: "Regular Meeting" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Meeting lifecycle stages" })).toBeInTheDocument();
  });

  it("shows actionable error and empty states for frontend QA", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "error" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Confirm the backend is running");
    expect(screen.getByRole("button", { name: "Retry after checking API" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "empty" }));
    expect(screen.getByRole("status")).toHaveTextContent("Create a meeting body");
  });

  it("toggles the audit evidence drawer", async () => {
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Show audit" }));
    expect(screen.getByLabelText("Audit and evidence drawer")).toHaveTextContent("Agenda published");
  });

  it("supports direct URL entry into QA states for browser evidence", () => {
    window.history.replaceState({}, "", "/?page=meeting-detail&state=partial&audit=1");
    render(<App />);

    expect(screen.getByRole("status")).toHaveTextContent("meeting detail is partially available");
    expect(screen.getByLabelText("Audit and evidence drawer")).toBeInTheDocument();
  });
});
