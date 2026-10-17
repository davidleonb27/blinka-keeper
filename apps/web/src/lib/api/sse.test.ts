import { describe, expect, it } from "vitest";
import { SseParser } from "./sse";

describe("SseParser", () => {
  it("emits one message per blank-line separated block", () => {
    const parser = new SseParser();
    const events = parser.push('event: verdict\ndata: {"round":1}\n\ndata: {"round":2}\n\n');

    expect(events).toEqual([
      { event: "verdict", data: '{"round":1}' },
      { event: "message", data: '{"round":2}' },
    ]);
  });

  it("buffers a message split across chunks", () => {
    const parser = new SseParser();

    expect(parser.push('data: {"ro')).toEqual([]);
    expect(parser.push('und":3}\r\n\r\n')).toEqual([{ event: "message", data: '{"round":3}' }]);
  });

  it("joins multi-line data and ignores comments", () => {
    const parser = new SseParser();
    const events = parser.push(": keep-alive\ndata: line one\ndata: line two\n\n");

    expect(events).toEqual([{ event: "message", data: "line one\nline two" }]);
  });
});
