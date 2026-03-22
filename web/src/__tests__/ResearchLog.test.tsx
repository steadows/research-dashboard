import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ResearchLog } from "@/app/workbench/ResearchLog";

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  readyState = 1;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    // Simulate open on next tick
    setTimeout(() => this.onopen?.(), 0);
  }

  send = vi.fn();
  close = vi.fn();

  // Helper to simulate an incoming message
  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
}

beforeEach(() => {
  MockWebSocket.instances = [];
  vi.stubGlobal("WebSocket", MockWebSocket);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ResearchLog", () => {
  it("returns null when not active", () => {
    const { container } = render(
      <ResearchLog itemKey="tool::Test" isActive={false} />
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders RESEARCH_LOG header when active", () => {
    render(<ResearchLog itemKey="tool::Test" isActive={true} />);
    expect(screen.getByText("RESEARCH_LOG")).toBeInTheDocument();
  });

  it("renders awaiting signal placeholder when no log lines", () => {
    render(<ResearchLog itemKey="tool::Test" isActive={true} />);
    expect(screen.getByText(/Awaiting signal/)).toBeInTheDocument();
  });

  it("shows WebSocket status indicator", () => {
    render(<ResearchLog itemKey="tool::Test" isActive={true} />);
    // Initial state is connecting, then transitions to open
    // The status label should be present
    const statusEl = screen.getByText(/CONNECTING|LIVE/);
    expect(statusEl).toBeInTheDocument();
  });

  it("connects to correct WebSocket path", () => {
    render(<ResearchLog itemKey="tool::MyTool" isActive={true} />);
    expect(MockWebSocket.instances.length).toBeGreaterThan(0);
    const ws = MockWebSocket.instances[0];
    expect(ws.url).toContain("/ws/research/tool%3A%3AMyTool");
  });
});
