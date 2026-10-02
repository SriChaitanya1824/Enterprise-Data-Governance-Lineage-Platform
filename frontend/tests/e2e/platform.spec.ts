import { test, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
const env = fs.readFileSync(path.resolve("../.env"), "utf8");
const password = env
  .split("\n")
  .find((l) => l.startsWith("BOOTSTRAP_PASSWORD="))!
  .split("=")
  .slice(1)
  .join("=");
test("dashboard, CDE traceability, quality and exception navigation", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByLabel("Email address")
    .fill("governance_analyst@example.test");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(
    page.getByRole("heading", { name: "Governance overview" }),
  ).toBeVisible();
  await expect(page.getByText("Registered data assets")).toBeVisible();
  await page
    .getByRole("link", { name: "Critical Data Elements", exact: true })
    .click();
  await page.getByLabel("Business division").selectOption("3");
  await page
    .getByRole("link", { name: /Customer Risk Rating/ })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Customer Risk Rating", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Lineage", exact: true }).click();
  await expect(page.locator(".react-flow")).toBeVisible();
  await page.getByRole("button", { name: "Quality", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Measured quality results" }),
  ).toBeVisible();
  await expect(page.getByText("100%").first()).toBeVisible();
  await page.getByRole("link", { name: "Exceptions", exact: true }).click();
  await page.locator("tbody tr a").first().click();
  await expect(
    page.getByRole("heading", { name: "Control failure & accountability" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Audit Log", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Audit log", exact: true }),
  ).toBeVisible();
  await expect(page.locator("tbody tr").first()).toBeVisible();
});
test("all navigation pages load without API or console errors", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("response", (r) => {
    if (r.url().includes("/api/") && r.status() >= 500)
      errors.push(`${r.status()} ${r.url()}`);
  });
  await page.goto("/");
  await page.getByLabel("Email address").fill("admin@example.test");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  for (const label of [
    "Data Catalog",
    "Business Glossary",
    "Lineage Explorer",
    "Data Quality",
    "Governance Controls",
    "Evidence",
    "Adoption",
    "Administration",
  ]) {
    await page.getByRole("link", { name: label, exact: true }).click();
    await expect(page.locator("main h1")).toBeVisible();
    await expect(page.getByText("Loading governance records…")).toHaveCount(0);
  }
  expect(errors).toEqual([]);
  await page.getByRole("link", { name: "Dashboard", exact: true }).click();
  await expect(page.getByText("Registered data assets")).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/dashboard.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Open navigation" }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/screenshots/mobile.png",
    fullPage: true,
  });
});
