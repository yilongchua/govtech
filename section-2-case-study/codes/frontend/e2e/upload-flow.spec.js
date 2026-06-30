const { test, expect } = require("@playwright/test");

test("frontend upload flow renders comparison report", async ({ page }) => {
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.goto("http://localhost:5173");
  await expect(page.getByRole("heading", { name: "History Exam Paper Alignment" })).toBeVisible();

  await page.setInputFiles(
    "input[type=file]",
    "/Users/YLChua/Desktop/govtech/section-2-case-study/data/raw/exam_pdfs/2174_specimen_paper_1.pdf"
  );
  await expect(page.getByText("2174_specimen_paper_1.pdf")).toBeVisible();

  await page.getByRole("button", { name: /submit/i }).click();
  await expect(page.getByText("Extracted Paper Structure")).toBeVisible({ timeout: 60000 });
  await expect(page.getByText("Topic Weightage")).toBeVisible();
  await page.screenshot({ path: "/tmp/section2-frontend-report.png", fullPage: true });

  expect(pageErrors).toEqual([]);
});
