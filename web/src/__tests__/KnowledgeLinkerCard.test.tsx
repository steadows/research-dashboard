import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SWRConfig } from "swr";
import type { LinkerStatus } from "@/app/dashboard/types";

// Mock hooks
const mockMutate = vi.fn();
const mockUseLinkerStatus = vi.fn();

vi.mock("@/app/dashboard/hooks", () => ({
  useLinkerStatus: (...args: unknown[]) => mockUseLinkerStatus(...args),
}));

// Mock apiMutate
const mockApiMutate = vi.fn();
vi.mock("@/lib/api", async (importOriginal) => {
  const orig = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...orig,
    apiMutate: (...args: unknown[]) => mockApiMutate(...args),
  };
});

import { KnowledgeLinkerCard } from "@/app/dashboard/KnowledgeLinkerCard";

function renderCard() {
  return render(
    <SWRConfig value={{ provider: () => new Map() }}>
      <KnowledgeLinkerCard />
    </SWRConfig>
  );
}

function mockStatus(status: LinkerStatus | undefined) {
  mockUseLinkerStatus.mockReturnValue({
    data: status,
    error: undefined,
    mutate: mockMutate,
  });
}

describe("KnowledgeLinkerCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiMutate.mockResolvedValue({ status: "accepted", run_id: "test-123" });
  });

  it("renders heading and Link Vault button when idle", () => {
    mockStatus(undefined);
    renderCard();

    expect(screen.getByText("Knowledge Linker")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /link vault/i })).toBeInTheDocument();
  });

  it("shows running state with directory progress", () => {
    mockStatus({
      run_id: "abc",
      status: "running",
      current_directory: "JournalClub",
      results: null,
      total_modified: null,
      warnings: [],
      started_at: new Date().toISOString(),
      completed_at: null,
      error: null,
    });
    renderCard();

    expect(screen.getByText(/Linking JournalClub/)).toBeInTheDocument();
    expect(screen.getByText(/Processing vault directories/)).toBeInTheDocument();
    // No Link Vault button while running
    expect(screen.queryByRole("button", { name: /link vault/i })).not.toBeInTheDocument();
  });

  it("shows complete state with results breakdown", () => {
    mockStatus({
      run_id: "abc",
      status: "complete",
      current_directory: null,
      results: { Instagram: 3, "Dev Journal": 1, Satellites: 2, Plans: 0 },
      total_modified: 6,
      warnings: [],
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      error: null,
    });
    renderCard();

    expect(screen.getByText("6 files modified")).toBeInTheDocument();
    expect(screen.getByText("Instagram")).toBeInTheDocument();
    expect(screen.getByText("Dev Journal")).toBeInTheDocument();
    // Satellites mapped to Project Links
    expect(screen.getByText("Project Links")).toBeInTheDocument();
    // Plans = 0, should not appear
    expect(screen.queryByText("Plans")).not.toBeInTheDocument();
    // Dismiss button present
    expect(screen.getByRole("button", { name: /dismiss/i })).toBeInTheDocument();
  });

  it("shows error state with retry button", () => {
    mockStatus({
      run_id: "abc",
      status: "error",
      current_directory: null,
      results: null,
      total_modified: null,
      warnings: [],
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      error: "Vault path not found",
    });
    renderCard();

    expect(screen.getByText("Vault path not found")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("handles 409 by starting poll loop instead of erroring", async () => {
    mockStatus({ run_id: null, status: "idle", current_directory: null, results: null, total_modified: null, warnings: [], started_at: null, completed_at: null, error: null });
    mockApiMutate.mockRejectedValueOnce(new Error("API POST /linker/run failed (409): Already running"));

    const user = userEvent.setup();
    renderCard();

    await user.click(screen.getByRole("button", { name: /link vault/i }));

    // Should call mutate to start polling, not throw
    expect(mockMutate).toHaveBeenCalled();
  });

  it("fires POST /linker/run and revalidates on click", async () => {
    mockStatus(undefined);

    const user = userEvent.setup();
    renderCard();

    await user.click(screen.getByRole("button", { name: /link vault/i }));

    expect(mockApiMutate).toHaveBeenCalledWith("/linker/run", { method: "POST" });
    expect(mockMutate).toHaveBeenCalled();
  });

  it("dismiss hides results and shows Link Vault button again", async () => {
    mockStatus({
      run_id: "abc",
      status: "complete",
      current_directory: null,
      results: { Instagram: 1 },
      total_modified: 1,
      warnings: [],
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      error: null,
    });

    const user = userEvent.setup();
    renderCard();

    expect(screen.getByText("1 files modified")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /dismiss/i }));

    // Results hidden, button back
    expect(screen.queryByText("1 files modified")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /link vault/i })).toBeInTheDocument();
  });

  it("shows partial state with warnings in amber", () => {
    mockStatus({
      run_id: "abc",
      status: "partial",
      current_directory: null,
      results: { Instagram: 2 },
      total_modified: 2,
      warnings: ["Failed to link note.md: permission denied"],
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
      error: null,
    });
    renderCard();

    expect(screen.getByText("2 files modified")).toBeInTheDocument();
    expect(screen.getByText(/Failed to link note.md/)).toBeInTheDocument();
  });

  it("rehydrates running state on mount", () => {
    // Simulate page refresh while job is running
    mockStatus({
      run_id: "prior-run",
      status: "running",
      current_directory: "TLDR",
      results: null,
      total_modified: null,
      warnings: [],
      started_at: new Date().toISOString(),
      completed_at: null,
      error: null,
    });
    renderCard();

    // Should show running state immediately, not idle
    expect(screen.getByText(/Linking TLDR/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /link vault/i })).not.toBeInTheDocument();
  });
});
