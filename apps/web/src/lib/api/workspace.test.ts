import { describe, expect, it, vi } from "vitest";
import type { WorkspaceCreated } from "./client";
import { ensureWorkspace, readWorkspaceCookie, WORKSPACE_COOKIE } from "./workspace";

function memoryStore(initial: string | null) {
  let value = initial;
  return {
    read: () => value,
    write: vi.fn((next: WorkspaceCreated) => {
      value = next.workspace_id;
    }),
    readApiKey: () => null,
  };
}

describe("readWorkspaceCookie", () => {
  it("finds the workspace id among other cookies", () => {
    expect(readWorkspaceCookie(`theme=dark; ${WORKSPACE_COOKIE}=ws_9; other=1`)).toBe("ws_9");
  });

  it("returns null when the cookie is absent or empty", () => {
    expect(readWorkspaceCookie("theme=dark")).toBeNull();
    expect(readWorkspaceCookie(`${WORKSPACE_COOKIE}=`)).toBeNull();
  });
});

describe("ensureWorkspace", () => {
  it("creates a demo workspace when there is no cookie and remembers it", async () => {
    const store = memoryStore(null);
    const createWorkspace = vi.fn(async () => ({ workspace_id: "ws_new", api_key: "ck_1" }));

    const id = await ensureWorkspace({ createWorkspace }, store);

    expect(id).toBe("ws_new");
    expect(createWorkspace).toHaveBeenCalledWith("demo");
    expect(store.write).toHaveBeenCalledWith({ workspace_id: "ws_new", api_key: "ck_1" });
  });

  it("reuses the existing workspace", async () => {
    const store = memoryStore("ws_old");
    const createWorkspace = vi.fn();

    expect(await ensureWorkspace({ createWorkspace }, store)).toBe("ws_old");
    expect(createWorkspace).not.toHaveBeenCalled();
  });
});
