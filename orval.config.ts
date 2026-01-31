import { defineConfig } from "orval";

export default defineConfig({
  agentLoop: {
    input: {
      target: "http://localhost:8000/v1/openapi.json",
    },
    output: {
      mode: "tags-split",
      target: "./generated/api",
      schemas: "./generated/models",
      client: "fetch",
      override: {
        mutator: {
          path: "./src/api/custom-fetch.ts",
          name: "customFetch",
        },
      },
    },
  },
  // React Query variant
  agentLoopReactQuery: {
    input: {
      target: "http://localhost:8000/v1/openapi.json",
    },
    output: {
      mode: "tags-split",
      target: "./generated/react-query",
      schemas: "./generated/models",
      client: "react-query",
    },
  },
});
