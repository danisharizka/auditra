/// <reference types="vite/client" />

declare namespace GeoJSON {
  interface FeatureCollection {
    type: "FeatureCollection";
    features: Feature[];
  }
  interface Feature {
    type: "Feature";
    properties?: Record<string, unknown>;
    geometry: unknown;
  }
}
