import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiFetcher, apiMutate } from "@/lib/api";

// Mock global fetch
const mockFetch = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("apiFetcher", () => {
  it("fetches from /api + path and returns JSON", async () => {
    const data = { items: [1, 2, 3] };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(data),
    });

    const result = await apiFetcher("/dashboard/stats");
    expect(mockFetch).toHaveBeenCalledWith("/api/dashboard/stats");
    expect(result).toEqual(data);
  });

  it("throws with status on non-2xx response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      text: () => Promise.resolve("Not found"),
    });

    await expect(apiFetcher("/missing")).rejects.toThrow("API error 404");
  });

  it("includes status property on error object", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: () => Promise.resolve("Internal error"),
    });

    try {
      await apiFetcher("/fail");
      expect.unreachable("should have thrown");
    } catch (err) {
      expect((err as { status: number }).status).toBe(500);
    }
  });

  it("handles text() failure gracefully", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 502,
      text: () => Promise.reject(new Error("stream error")),
    });

    await expect(apiFetcher("/bad-gateway")).rejects.toThrow("API error 502");
  });
});

describe("apiMutate", () => {
  it("sends POST request by default", async () => {
    const responseData = { id: 1 };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(responseData),
    });

    const result = await apiMutate("/items", { body: { name: "test" } });

    expect(mockFetch).toHaveBeenCalledWith("/api/items", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "test" }),
    });
    expect(result).toEqual(responseData);
  });

  it("sends PUT request when specified", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await apiMutate("/items/1", { method: "PUT", body: { name: "updated" } });

    expect(mockFetch).toHaveBeenCalledWith("/api/items/1", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "updated" }),
    });
  });

  it("sends PATCH request when specified", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await apiMutate("/items/1", { method: "PATCH", body: { status: "done" } });

    expect(mockFetch).toHaveBeenCalledWith("/api/items/1", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "done" }),
    });
  });

  it("sends DELETE request without body", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    });

    await apiMutate("/items/1", { method: "DELETE" });

    expect(mockFetch).toHaveBeenCalledWith("/api/items/1", {
      method: "DELETE",
      headers: undefined,
      body: undefined,
    });
  });

  it("throws on non-2xx with method, path, and status", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 422,
      text: () => Promise.resolve("Validation error"),
    });

    await expect(
      apiMutate("/items", { body: { bad: true } })
    ).rejects.toThrow("API POST /items failed (422)");
  });
});

describe("useWebSocket", () => {
  // WebSocket hook tests are in ResearchLog.test.tsx since the hook
  // requires a React component context. Here we verify the module exports.
  it("exports useWebSocket function", async () => {
    const api = await import("@/lib/api");
    expect(typeof api.useWebSocket).toBe("function");
  });

  it("exports WebSocketStatus type (apiFetcher and apiMutate exist)", async () => {
    const api = await import("@/lib/api");
    expect(typeof api.apiFetcher).toBe("function");
    expect(typeof api.apiMutate).toBe("function");
    expect(typeof api.defaultSWRConfig).toBe("object");
  });
});
