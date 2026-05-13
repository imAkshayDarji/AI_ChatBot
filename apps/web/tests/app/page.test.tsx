import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "@/app/page";

describe("Home page", () => {
  it("shows the studio name and tagline", () => {
    render(<Home />);
    expect(
      screen.getByRole("heading", { name: /krystal tattoo studio/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/tattoo, piercing & dreadlock studio/i),
    ).toBeInTheDocument();
  });
});
