/* embed-worker.js — the embedding worker behind the data dictionary's optional
   semantic search. Copied into <package>/assets/ by scripts/render.py
   (init / refresh-assets); never edit the package copy — regenerate it from
   the skill.

   dictionary.html starts this worker when the page is served over http, so the
   text-embedding model runs off the main thread. The page passes the runtime
   and the model through the worker URL's query string — the page stays the
   single source of that configuration:

     assets/embed-worker.js?transformers=<Transformers.js module URL>
                            &model=<Hugging Face model id>&dtype=q8

   A classic worker, so it can importScripts() the vendored IIFE bundle;
   Transformers.js (ESM only) is pulled in with a dynamic import() the first
   time the model is needed. Model weights come from the Hugging Face Hub and
   are cached by the browser; nothing but those downloads leaves the machine. */
importScripts("json-schema-data-dictionary.global.js");

var params = new URLSearchParams(self.location.search);
var transformersUrl = params.get("transformers");
var model = params.get("model");
if (!transformersUrl || !model) {
  throw new Error("embed-worker.js needs ?transformers=<module url>&model=<model id> in its URL");
}

var API = self.JsonSchemaDataDictionary;
API.serveEmbedder(
  API.createTransformersEmbedder(
    function () {
      return import(transformersUrl).then(function (transformers) {
        transformers.env.allowLocalModels = false; // never probe /models/… on this origin
        return transformers;
      });
    },
    {
      model: model,
      dtype: params.get("dtype") || "q8",
      device: params.get("device") || "wasm"
    }
  )
);
