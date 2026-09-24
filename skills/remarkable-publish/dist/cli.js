#!/usr/bin/env node
import { readFile, writeFile } from "node:fs/promises";
import { renderMarkdownToPdf, renderSvgToPdf } from "./render-pdf.js";
function usageError() {
    throw new Error("Usage: cli <document|drawing> <input-file> <output-file> [title]");
}
async function main() {
    const [mode, inputPath, outputPath, title] = process.argv.slice(2);
    if (mode !== "document" && mode !== "drawing") {
        usageError();
    }
    if (!inputPath || !outputPath) {
        usageError();
    }
    const content = await readFile(inputPath, "utf8");
    const options = title ? { title } : {};
    const pdf = mode === "document" ? await renderMarkdownToPdf(content, options) : await renderSvgToPdf(content, options);
    await writeFile(outputPath, pdf);
}
main().catch((err) => {
    console.error(err instanceof Error ? err.message : String(err));
    process.exit(1);
});
//# sourceMappingURL=cli.js.map