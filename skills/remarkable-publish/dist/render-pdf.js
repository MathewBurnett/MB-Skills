import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { marked } from "marked";
import puppeteer from "puppeteer";
const templatesDir = join(dirname(fileURLToPath(import.meta.url)), "templates");
function escapeHtml(value) {
    return value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
async function fillTemplate(templateFile, body, title) {
    const template = await readFile(join(templatesDir, templateFile), "utf8");
    const values = { title: escapeHtml(title), body };
    // Single pass over the original template, keyed by placeholder name — not sequential .replace()
    // calls, which would let one substitution's content (e.g. a title containing the literal text
    // "{{body}}") be mistaken for the other placeholder. The replacer is a function, not a string,
    // so `$`-patterns in body/title (like markdown's `$$...$$` math delimiters) can't be misread as
    // replacement-pattern syntax either.
    return template.replace(/\{\{(title|body)\}\}/g, (_match, key) => values[key]);
}
/** Builds the full HTML page for markdown/prose content. Pure — no browser needed, easy to unit test. */
export async function buildDocumentHtml(markdown, options = {}) {
    const bodyHtml = await marked.parse(markdown);
    return fillTemplate("document.html", bodyHtml, options.title ?? "Document");
}
/** Builds the full HTML page for an SVG drawing. Pure — no browser needed, easy to unit test. */
export async function buildDrawingHtml(svg, options = {}) {
    return fillTemplate("drawing.html", svg, options.title ?? "Drawing");
}
/**
 * Shared HTML-to-PDF rendering path for both prose documents and SVG drawings.
 *
 * The HTML being rendered embeds untrusted content (markdown/SVG the user asked to publish, which
 * may itself have been pasted or fetched from a third party) — JS execution and all outbound
 * network requests are disabled so an embedded `<script>`/`onerror`/remote-image payload can't run
 * code or exfiltrate anything through the render step. Nothing in the current templates needs
 * either capability.
 */
async function renderHtmlToPdf(html) {
    const browser = await puppeteer.launch({ args: ["--no-sandbox", "--disable-setuid-sandbox"] });
    try {
        const page = await browser.newPage();
        await page.setJavaScriptEnabled(false);
        await page.setRequestInterception(true);
        page.on("request", (req) => req.abort());
        await page.setContent(html, { waitUntil: "load" });
        const pdf = await page.pdf({ printBackground: true, preferCSSPageSize: true });
        return Buffer.from(pdf);
    }
    finally {
        await browser.close();
    }
}
/** Renders markdown/prose content into a paginated PDF. */
export async function renderMarkdownToPdf(markdown, options = {}) {
    return renderHtmlToPdf(await buildDocumentHtml(markdown, options));
}
/** Renders an inline SVG drawing into a PDF. */
export async function renderSvgToPdf(svg, options = {}) {
    return renderHtmlToPdf(await buildDrawingHtml(svg, options));
}
//# sourceMappingURL=render-pdf.js.map