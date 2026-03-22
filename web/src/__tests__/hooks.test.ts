import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock SWR to control data flow without real fetches
const mockUseSWR = vi.fn();
vi.mock("swr", () => ({
  default: (...args: unknown[]) => mockUseSWR(...args),
  __esModule: true,
}));

vi.mock("@/lib/api", () => ({
  defaultSWRConfig: { fetcher: vi.fn(), revalidateOnFocus: false },
  apiMutate: vi.fn(),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useWorkbench", () => {
  it("returns grouped columns when data is present", async () => {
    mockUseSWR.mockReturnValue({
      data: {
        "tool::Vitest": {
          name: "Vitest",
          source_type: "tool",
          status: "queued",
          notes: "",
          previous_status: null,
          added_at: null,
          verdict: null,
          pid: null,
          log_file: null,
        },
        "method::TDD": {
          name: "TDD",
          source_type: "method",
          status: "researching",
          notes: "",
          previous_status: null,
          added_at: null,
          verdict: null,
          pid: 123,
          log_file: null,
        },
        "tool::Jest": {
          name: "Jest",
          source_type: "tool",
          status: "completed",
          notes: "",
          previous_status: "researching",
          added_at: null,
          verdict: "programmatic",
          pid: null,
          log_file: null,
        },
      },
      error: undefined,
      isLoading: false,
      mutate: vi.fn(),
    });

    const { useWorkbench } = await import("@/app/workbench/hooks");
    const { result } = renderHook(() => useWorkbench());

    expect(result.current.columns.queued).toHaveLength(1);
    expect(result.current.columns.queued[0].key).toBe("tool::Vitest");
    expect(result.current.columns.researching).toHaveLength(1);
    expect(result.current.columns.researching[0].key).toBe("method::TDD");
    expect(result.current.columns.completed).toHaveLength(1);
    expect(result.current.columns.completed[0].key).toBe("tool::Jest");
  });

  it("returns empty columns when data is undefined (loading)", async () => {
    mockUseSWR.mockReturnValue({
      data: undefined,
      error: undefined,
      isLoading: true,
      mutate: vi.fn(),
    });

    const { useWorkbench } = await import("@/app/workbench/hooks");
    const { result } = renderHook(() => useWorkbench());

    expect(result.current.columns.queued).toHaveLength(0);
    expect(result.current.columns.researching).toHaveLength(0);
    expect(result.current.columns.completed).toHaveLength(0);
    expect(result.current.isLoading).toBe(true);
  });

  it("passes error through from SWR", async () => {
    const err = new Error("fetch failed");
    mockUseSWR.mockReturnValue({
      data: undefined,
      error: err,
      isLoading: false,
      mutate: vi.fn(),
    });

    const { useWorkbench } = await import("@/app/workbench/hooks");
    const { result } = renderHook(() => useWorkbench());

    expect(result.current.error).toBe(err);
  });

  it("fetches from /workbench endpoint", async () => {
    mockUseSWR.mockReturnValue({
      data: {},
      error: undefined,
      isLoading: false,
      mutate: vi.fn(),
    });

    const { useWorkbench } = await import("@/app/workbench/hooks");
    renderHook(() => useWorkbench());

    expect(mockUseSWR).toHaveBeenCalledWith(
      "/workbench",
      expect.objectContaining({ refreshInterval: 10_000 })
    );
  });
});

describe("updateWorkbenchStatus", () => {
  it("calls apiMutate with PATCH and correct path", async () => {
    const { apiMutate } = await import("@/lib/api");
    const { updateWorkbenchStatus } = await import("@/app/workbench/hooks");

    await updateWorkbenchStatus("tool::MyTool", "researching");

    expect(apiMutate).toHaveBeenCalledWith(
      "/workbench/tool%3A%3AMyTool",
      {
        method: "PATCH",
        body: { updates: { status: "researching" } },
      }
    );
  });
});

describe("useDashboardStats", () => {
  it("fetches from /dashboard/stats with refresh interval", async () => {
    mockUseSWR.mockReturnValue({
      data: { papers: 10, tools: 5, blog_queue: 3, active_projects: 4 },
      error: undefined,
      isLoading: false,
    });

    const { useDashboardStats } = await import("@/app/dashboard/hooks");
    const { result } = renderHook(() => useDashboardStats());

    expect(mockUseSWR).toHaveBeenCalledWith(
      "/dashboard/stats",
      expect.objectContaining({ refreshInterval: 30_000 })
    );
    expect(result.current.data).toEqual({
      papers: 10,
      tools: 5,
      blog_queue: 3,
      active_projects: 4,
    });
  });

  it("returns loading state", async () => {
    mockUseSWR.mockReturnValue({
      data: undefined,
      error: undefined,
      isLoading: true,
    });

    const { useDashboardStats } = await import("@/app/dashboard/hooks");
    const { result } = renderHook(() => useDashboardStats());

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });
});

describe("useInstagramFeed", () => {
  it("fetches from /instagram/feed", async () => {
    const posts = [
      {
        id: "1",
        account: "test",
        title: "Post 1",
        key_points: [],
        tags: [],
        timestamp: "2026-03-22T00:00:00Z",
      },
    ];
    mockUseSWR.mockReturnValue({
      data: posts,
      error: undefined,
      isLoading: false,
    });

    const { useInstagramFeed } = await import("@/app/dashboard/hooks");
    const { result } = renderHook(() => useInstagramFeed());

    expect(mockUseSWR).toHaveBeenCalledWith(
      "/instagram/feed",
      expect.any(Object)
    );
    expect(result.current.data).toEqual(posts);
  });

  it("returns error state", async () => {
    const err = new Error("network error");
    mockUseSWR.mockReturnValue({
      data: undefined,
      error: err,
      isLoading: false,
    });

    const { useInstagramFeed } = await import("@/app/dashboard/hooks");
    const { result } = renderHook(() => useInstagramFeed());

    expect(result.current.error).toBe(err);
  });
});
