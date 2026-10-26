import React from "react";
import { Composition } from "remotion";
import { Explainer, dureeTotale, FPS } from "./Explainer";
import type { Script } from "./types";
import exemple from "../public/exemple.json";
import { GabaritV2, dureeTotaleV2, type ScriptV2 } from "./GabaritV2";
import { PersoReel, dureeTotalePerso, type ScriptPerso } from "./PersoReel";

const exempleV2: ScriptV2 = { rubrique: "ANALYSE", titre: "Titre d'exemple", image: "lavage.png", scenes: [{ type: "visuel", duree: 3 }] };
const exemplePerso: ScriptPerso = { rubrique: "Les pièges du cerveau", titre: "Exemple", nom: "Stéphane Nzesseu", compte: "@stephane_nzesseu",
  scenes: [{ type: "accroche", emoji: "😱", ecran: "Pourquoi tu *détestes* perdre ?", duree: 3 }, { type: "signature", duree: 3 }] };

export const Root: React.FC = () => (
  <>
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
    {/* prototype du nouveau gabarit : pas utilisé en production */}
    <Composition
      id="DecideShortV2"
      component={GabaritV2}
      width={1080}
      height={1920}
      fps={FPS}
      durationInFrames={dureeTotaleV2(exempleV2)}
      defaultProps={exempleV2}
      calculateMetadata={({ props }) => ({ durationInFrames: dureeTotaleV2(props as ScriptV2) })}
    />
    {/* Reels du compte Instagram personnel (agent/perso.py) */}
    <Composition
      id="PersoReel"
      component={PersoReel}
      width={1080}
      height={1920}
      fps={FPS}
      durationInFrames={dureeTotalePerso(exemplePerso)}
      defaultProps={exemplePerso}
      calculateMetadata={({ props }) => ({ durationInFrames: dureeTotalePerso(props as ScriptPerso) })}
    />
  </>
);
