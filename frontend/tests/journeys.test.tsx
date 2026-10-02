import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import { Exceptions } from "../src/pages/Exceptions";
import { Catalog } from "../src/pages/Catalog";
import { setToken } from "../src/services/api";
function wrap(node: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>,
  );
}
afterEach(() => {
  vi.restoreAllMocks();
  setToken(null);
});
describe("governance journeys", () => {
  it("shows a useful authentication error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid credentials" }), {
        status: 401,
      }),
    );
    wrap(<App />);
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "incorrect-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid credentials",
    );
  });
  it("filters CDE profiles and links to governance detail", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      return new Response(
        JSON.stringify(
          url.includes("/cdes")
            ? {
                items: [
                  {
                    id: 22,
                    name: "risk_rating",
                    term: "Customer Risk Rating",
                    classification: "Confidential",
                    asset: {
                      id: 7,
                      name: "customer_risk",
                      owner: null,
                      quality_score: 100,
                    },
                  },
                ],
                total: 1,
                page: 1,
                page_size: 20,
              }
            : { items: [], total: 0 },
        ),
      );
    });
    wrap(<Catalog cdes />);
    expect(
      await screen.findByRole("link", { name: /Customer Risk Rating/ }),
    ).toHaveAttribute("href", "/cdes/22");
    fireEvent.change(screen.getByLabelText("Search catalog"), {
      target: { value: "risk" },
    });
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("q=risk"),
        expect.anything(),
      ),
    );
    expect(await screen.findByText("Unassigned")).toBeInTheDocument();
  });
  it("exposes exception status filtering and detail links", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(
      async (input) =>
        new Response(
          JSON.stringify(
            String(input).includes("/exceptions")
              ? {
                  items: [
                    {
                      id: 4,
                      reference: "DG-2026-DEMO",
                      asset_name: "customer_risk",
                      control_name: "Ownership",
                      severity: "High",
                      status: "Open",
                      due_date: "2026-10-15",
                    },
                  ],
                  total: 1,
                  page: 1,
                  page_size: 20,
                }
              : { items: [] },
          ),
        ),
    );
    wrap(<Exceptions />);
    expect(
      await screen.findByRole("link", { name: "DG-2026-DEMO" }),
    ).toHaveAttribute("href", "/exceptions/4");
    fireEvent.change(screen.getByLabelText("Exception status"), {
      target: { value: "Closed" },
    });
    await waitFor(() =>
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("status=Closed"),
        expect.anything(),
      ),
    );
  });
});
