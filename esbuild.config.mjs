import * as esbuild from "esbuild";

const isWatch = process.argv.includes("--watch");
const isProd = process.argv.includes("--production");

/** @type {esbuild.BuildOptions} */
const extensionConfig = {
  entryPoints: ["src/extension/extension.ts"],
  bundle: true,
  platform: "node",
  target: "node18",
  outfile: "dist/extension/index.js",
  external: ["vscode"],
  format: "cjs",
  sourcemap: true,
  logLevel: "info",
};

/** @type {esbuild.BuildOptions} */
const webviewConfig = {
  entryPoints: ["src/webview/index.tsx"],
  bundle: true,
  platform: "browser",
  target: "es2020",
  outfile: "dist/webview/index.js",
  format: "iife",
  sourcemap: true,
  minify: isProd,
  logLevel: "info",
};

async function main() {
  if (isWatch) {
    const extCtx = await esbuild.context(extensionConfig);
    const webCtx = await esbuild.context(webviewConfig);
    await Promise.all([extCtx.watch(), webCtx.watch()]);
    console.log("Watching for changes...");
  } else {
    await Promise.all([
      esbuild.build(extensionConfig),
      esbuild.build(webviewConfig),
    ]);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
