import adapter from "@sveltejs/adapter-static";
import { mdsvex } from "mdsvex";
import mdsvexConfig from "./mdsvex.config.js";

const isDev = process.argv.includes("dev");

export default {
  compilerOptions: {
    runes: ({ filename }) => {
      if (filename.endsWith(".svx") || filename.endsWith(".md")) {
        return false;
      }
      return filename.split(/[/\\]/).includes("node_modules") ? undefined : true;
    },
  },
  extensions: [".svelte", ...mdsvexConfig.extensions],
  preprocess: [mdsvex(mdsvexConfig)],
  kit: {
    adapter: adapter({ pages: "build", assets: "build", fallback: "404.html" }),
    paths: {
      base: isDev ? "" : (process.env.BASE_PATH ?? ""),
    },
  },
};
