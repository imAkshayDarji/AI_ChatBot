import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiGet, apiPost } from "@/lib/api";

describe("apiGet", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ data: true }),
      } as Response),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("requests JSON from the configured API base URL", async () => {
    const value = await apiGet<{ data: boolean }>("/hello");
    expect(value).toEqual({ data: true });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/hello");
  });

  it("throws when the response is not ok", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 502,
    } as Response);

    await expect(apiGet("/down")).rejects.toThrowError("API error: 502");
  });
});

describe("apiPost", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 201,
        json: async () => ({ id: "x" }),
      } as Response),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts JSON body and parses response", async () => {
    const result = await apiPost<{ foo: number }, { id: string }>("/things", {
      foo: 1,
    });

    expect(result).toEqual({ id: "x" });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch).toHaveBeenCalledWith("http://localhost:8000/things", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ foo: 1 }),
    });
  });

  it("throws when the response is not ok", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 400,
    } as Response);

    await expect(apiPost("/", {})).rejects.toThrowError("API error: 400");
  });
});
