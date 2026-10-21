import React from "react";
import { Composition } from "remotion";
import { Explainer, dureeTotale, FPS } from "./Explainer";
import type { Script } from "./types";
import exemple from "../public/exemple.json";

export const Root: React.FC = () => (
  <Composition
    id="DecideShort"
    component={Explainer}
    width={1080}
    height={1920}
    fps={FPS}
    durationInFrames={dureeTotale(exemple as Script)}
    defaultProps={exemple as Script}
    calculateMetadata={({ props }) => ({ durationInFrames: dureeTotale(props as Script) })}
  />
);
