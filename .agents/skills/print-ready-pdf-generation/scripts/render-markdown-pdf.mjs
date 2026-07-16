#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function usage() {
  console.error(`Usage:
  node render-markdown-pdf.mjs <input.md|input.html> <output.pdf> [options]

Options:
  --config <path>          CommonJS config with pdf_options and stylesheet entries
  --css <path>             CSS file to inline; may be repeated
  --chrome <path>          Chrome/Chromium executable path
  --keep-html <path>       Write the intermediate HTML for inspection
  --fail-on-overflow       Exit non-zero if obvious screen overflow is detected

The script resolves marked/playwright from local node_modules, NODE_PATH, or
the Codex bundled dependency path when present.`);
}

function parseArgs(argv) {
  const parsed = {
    css: [],
    config: null,
    chrome: null,
    keepHtml: null,
    failOnOverflow: false,
    positional: [],
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--css") parsed.css.push(argv[++i]);
    else if (arg === "--config") parsed.config = argv[++i];
    else if (arg === "--chrome") parsed.chrome = argv[++i];
    else if (arg === "--keep-html") parsed.keepHtml = argv[++i];
    else if (arg === "--fail-on-overflow") parsed.failOnOverflow = true;
    else if (arg === "--help" || arg === "-h") {
      usage();
      process.exit(0);
    } else if (arg.startsWith("--")) {
      throw new Error(`Unknown option: ${arg}`);
    } else {
      parsed.positional.push(arg);
    }
  }

  if (parsed.positional.length !== 2) {
    usage();
    process.exit(2);
  }
  return parsed;
}

function existingPaths(paths) {
  return paths.filter(Boolean).filter((candidate) => fs.existsSync(candidate));
}

function moduleDirs() {
  const dirs = [];
  if (process.env.NODE_PATH) dirs.push(...process.env.NODE_PATH.split(path.delimiter));
  dirs.push(
    path.resolve(process.cwd(), "node_modules"),
    path.resolve(__dirname, "..", "node_modules"),
    path.resolve(__dirname, "..", "..", "node_modules"),
    path.join(process.env.HOME || "", ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"),
  );
  return existingPaths([...new Set(dirs)]);
}

async function importPackage(packageName) {
  const errors = [];
  for (const dir of moduleDirs()) {
    try {
      const req = createRequire(path.join(dir, "_resolver.cjs"));
      const resolved = req.resolve(packageName);
      return await import(pathToFileURL(resolved).href);
    } catch (error) {
      errors.push(`${dir}: ${error.message}`);
    }
  }

  try {
    return await import(packageName);
  } catch (error) {
    errors.push(`default resolver: ${error.message}`);
  }

  throw new Error(`Could not resolve ${packageName}.\n${errors.join("\n")}`);
}

function stripFrontmatter(input) {
  return input.replace(/^---\s*\r?\n[\s\S]*?\r?\n---\s*\r?\n/, "");
}

function readConfig(configPath) {
  if (!configPath) return {};
  const absolute = path.resolve(configPath);
  const req = createRequire(pathToFileURL(absolute).href);
  return {
    config: req(absolute),
    baseDir: path.dirname(absolute),
  };
}

function resolveRelative(filePath, baseDirs) {
  if (!filePath) return null;
  if (path.isAbsolute(filePath)) return filePath;
  for (const baseDir of baseDirs) {
    const candidate = path.resolve(baseDir, filePath);
    if (fs.existsSync(candidate)) return candidate;
  }
  return path.resolve(baseDirs[0] || process.cwd(), filePath);
}

function readCss(paths) {
  return paths
    .filter(Boolean)
    .map((cssPath) => fs.readFileSync(cssPath, "utf8"))
    .join("\n\n");
}

function findChrome(explicitPath) {
  const candidates = existingPaths([
    explicitPath,
    process.env.CHROME_PATH,
    process.env.PUPPETEER_EXECUTABLE_PATH,
    process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ]);
  return candidates[0] || null;
}

function htmlShell({ title, css, body }) {
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>${title.replaceAll("&", "&amp;").replaceAll("<", "&lt;")}</title>
  <style>${css}</style>
</head>
<body>
${body}
</body>
</html>`;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const inputPath = path.resolve(args.positional[0]);
  const outputPath = path.resolve(args.positional[1]);
  const inputDir = path.dirname(inputPath);

  const configData = readConfig(args.config);
  const config = configData.config || {};
  const configBaseDir = configData.baseDir || inputDir;
  const baseDirs = [configBaseDir, inputDir, process.cwd()];

  const stylesheetEntries = [
    ...(Array.isArray(config.stylesheet) ? config.stylesheet : []),
    ...(Array.isArray(config.stylesheets) ? config.stylesheets : []),
    ...args.css,
  ];
  const cssPaths = stylesheetEntries.map((entry) => resolveRelative(entry, baseDirs));
  const css = readCss(cssPaths);

  const raw = fs.readFileSync(inputPath, "utf8");
  const extension = path.extname(inputPath).toLowerCase();
  let body;
  if (extension === ".html" || extension === ".htm") {
    body = raw;
  } else {
    const markedModule = await importPackage("marked");
    const marked = markedModule.marked || markedModule.default || markedModule;
    body = await marked.parse(stripFrontmatter(raw));
  }

  const html = htmlShell({
    title: path.basename(inputPath),
    css,
    body,
  });

  if (args.keepHtml) {
    fs.mkdirSync(path.dirname(path.resolve(args.keepHtml)), { recursive: true });
    fs.writeFileSync(path.resolve(args.keepHtml), html);
  }

  const playwrightModule = await importPackage("playwright");
  const { chromium } = playwrightModule.default || playwrightModule;
  if (!chromium) {
    throw new Error("Resolved playwright, but could not find chromium export.");
  }
  const executablePath = findChrome(args.chrome);
  const launchOptions = executablePath
    ? { headless: true, executablePath, args: ["--no-sandbox"] }
    : { headless: true, args: ["--no-sandbox"] };

  const browser = await chromium.launch(launchOptions);
  try {
    const page = await browser.newPage({ viewport: { width: 816, height: 1056 } });
    await page.emulateMedia({ media: "print" });
    await page.setContent(html, { waitUntil: "networkidle" });
    await page.evaluate(() => document.fonts && document.fonts.ready);

    const overflowing = await page.evaluate(() =>
      Array.from(document.querySelectorAll("body *"))
        .filter((element) => element.scrollWidth > element.clientWidth + 2)
        .slice(0, 10)
        .map((element) => ({
          tag: element.tagName.toLowerCase(),
          text: (element.textContent || "").trim().slice(0, 90),
          clientWidth: element.clientWidth,
          scrollWidth: element.scrollWidth,
        })),
    );

    if (overflowing.length) {
      console.warn("Potential overflowing elements before print:");
      console.warn(JSON.stringify(overflowing, null, 2));
      if (args.failOnOverflow) process.exitCode = 1;
    }

    const pdfOptions = {
      format: "Letter",
      printBackground: true,
      ...(config.pdf_options || {}),
      path: outputPath,
    };
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    await page.pdf(pdfOptions);
  } finally {
    await browser.close();
  }

  if (process.exitCode) return;
  console.log(`Wrote ${outputPath}`);
}

main().catch((error) => {
  console.error(error.stack || error.message || error);
  process.exit(1);
});
