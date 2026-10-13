/* embed-worker.js — the embedding worker behind the data dictionary's optional
   semantic search. Shipped into every workspace (site/) and package (assets/)
   by scripts/schemify.py; never edit those copies — they are refreshed from
   the skill.

   The page starts this worker only when it is served over http (browsers
   refuse workers to pages opened from disk; the page then runs the model on
   its own thread). The page passes the runtime URL through the query string:

     embed-worker.js?transformers=<Transformers.js module URL>[&model=<id>][&device=auto]

   With no model given, json-schema-data-dictionary's verified default
   (MongoDB/mdbr-leaf-ir) is used with automatic device and precision.
   A classic worker, so it can importScripts() the vendored IIFE bundle;
   Transformers.js (ESM only) arrives by dynamic import() the first time the
   model is needed. Model weights come from huggingface.co and are cached by
   the browser; the schema text and the queries never leave the machine. */
importScripts("json-schema-data-dictionary.global.js");

var params = new URLSearchParams(self.location.search);
var transformersUrl = params.get("transformers");
if (!transformersUrl) {
  throw new Error("embed-worker.js needs ?transformers=<module url> in its URL");
}

var options = { device: params.get("device") || "auto" };
if (params.get("model")) options.model = params.get("model");

var API = self.JsonSchemaDataDictionary;
API.serveEmbedder(
  API.createTransformersEmbedder(function () {
    return import(transformersUrl).then(function (transformers) {
      transformers.env.allowLocalModels = false; // never probe /models/… on this origin
      return transformers;
    });
  }, options)
);
