// Habillage des comptes « Histoires vraies d'argent » (06/11/2026) : photo de profil (TikTok et YouTube, ronde à
// l'affichage) et bannière YouTube 2560×1440 (zone visible partout : 1546×423 au centre). Mêmes couleurs et polices
// que les vidéos (RecitReel.tsx).
import React from "react";
import { AbsoluteFill } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import { loadFont as loadPlayfair } from "@remotion/google-fonts/PlayfairDisplay";
import { loadFont as loadElite } from "@remotion/google-fonts/SpecialElite";
import { loadFont as loadAnton } from "@remotion/google-fonts/Anton";

const { fontFamily } = loadFont("normal", { weights: ["700", "800"], subsets: ["latin", "latin-ext"] });
const { fontFamily: playfair } = loadPlayfair("normal", { weights: ["900"], subsets: ["latin", "latin-ext"] });
const { fontFamily: elite } = loadElite("normal", { weights: ["400"], subsets: ["latin", "latin-ext"] });
const { fontFamily: anton } = loadAnton("normal", { weights: ["400"], subsets: ["latin", "latin-ext"] });

const NOIR = "#120E0B";
const PAPIER = "#F3E9D2";
const OR = "#E2B04A";
const ROUGE = "#C2412D";

const Fond: React.FC = () => (
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, #2E2318 0%, ${NOIR} 72%)` }}>
    <AbsoluteFill style={{ opacity: 0.06, backgroundImage: "repeating-linear-gradient(0deg, #fff 0px, transparent 1px, transparent 4px)" }} />
  </AbsoluteFill>
);

const Tampon: React.FC<{ texte: string; taille: number; couleur?: string; rot?: number }> = ({ texte, taille, couleur = ROUGE, rot = -8 }) => (
  <div style={{ display: "inline-block", transform: `rotate(${rot}deg)`, fontFamily: elite, fontSize: taille, lineHeight: 1, color: couleur,
    padding: `${taille * 0.08}px ${taille * 0.25}px`, border: `${Math.max(4, taille * 0.07)}px solid ${couleur}`, borderRadius: taille * 0.1,
    background: "rgba(18,14,11,0.55)" }}>{texte}</div>
);

// Photo de profil 800×800 : un sceau doré, texte circulaire, « € » au centre, tampon « VRAI ».
export const Profil: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: NOIR }}>
    <Fond />
    <svg width={800} height={800} viewBox="0 0 800 800" style={{ position: "absolute" }}>
      <defs>
        <path id="cercle" d="M 400,400 m -268,0 a 268,268 0 1,1 536,0 a 268,268 0 1,1 -536,0" />
      </defs>
      <circle cx={400} cy={400} r={330} fill="none" stroke={OR} strokeWidth={14} />
      <circle cx={400} cy={400} r={300} fill="none" stroke={OR} strokeWidth={4} />
      <circle cx={400} cy={400} r={222} fill="none" stroke={OR} strokeWidth={4} />
      {/* une seule fois le nom, étiré sur tout le tour (2π×268 ≈ 1684) : il ne se chevauche plus */}
      <text fill={OR} style={{ fontFamily: elite, fontSize: 54 }} textLength={1650} lengthAdjust="spacing">
        <textPath href="#cercle" startOffset="0%">HISTOIRES VRAIES · D'ARGENT · </textPath>
      </text>
    </svg>
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div style={{ fontFamily: anton, fontSize: 250, color: OR, lineHeight: 1, marginTop: -70,
        textShadow: "0 0 50px rgba(226,176,74,0.45), 0 10px 24px rgba(0,0,0,0.7)" }}>€</div>
    </AbsoluteFill>
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", top: 140 }}>
      <Tampon texte="VRAI" taille={64} />
    </AbsoluteFill>
  </AbsoluteFill>
);

// Bannière YouTube 2560×1440. Zone sûre (tous écrans) : x 507–2053, y 508–931. Le reste n'apparaît que sur télévision.
export const Bandeau: React.FC = () => {
  const dates = ["1637", "1720", "1889", "1902", "1925", "1934", "1976"];
  return (
    <AbsoluteFill style={{ backgroundColor: NOIR }}>
      <Fond />
      {/* frise de dates en filigrane, visible surtout sur grand écran */}
      <div style={{ position: "absolute", top: 160, left: 0, right: 0, display: "flex", justifyContent: "space-around", opacity: 0.12 }}>
        {dates.map((d) => <span key={d} style={{ fontFamily: elite, fontSize: 150, color: PAPIER }}>{d}</span>)}
      </div>
      <div style={{ position: "absolute", bottom: 160, left: 0, right: 0, display: "flex", justifyContent: "space-around", opacity: 0.12 }}>
        {dates.slice().reverse().map((d) => <span key={d} style={{ fontFamily: elite, fontSize: 150, color: PAPIER }}>{d}</span>)}
      </div>
      {/* filets dorés qui encadrent la zone sûre */}
      <div style={{ position: "absolute", top: 528, left: 527, width: 1506, height: 2, background: OR, opacity: 0.6 }} />
      <div style={{ position: "absolute", top: 911, left: 527, width: 1506, height: 2, background: OR, opacity: 0.6 }} />
      {/* zone sûre */}
      <div style={{ position: "absolute", left: 507, top: 508, width: 1546, height: 423, display: "flex", alignItems: "center",
        justifyContent: "space-between", padding: "0 60px" }}>
        <div>
          <div style={{ fontFamily: playfair, fontWeight: 900, fontSize: 118, color: PAPIER, lineHeight: 1 }}>
            Histoires vraies <span style={{ color: OR }}>d'argent</span>
          </div>
          <div style={{ fontFamily, fontWeight: 700, fontSize: 44, color: PAPIER, opacity: 0.9, marginTop: 26 }}>
            Arnaques, fortunes, faillites : des histoires vraies qui paraissent inventées.
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 26, marginLeft: 40 }}>
          <Tampon texte="VRAI" taille={110} rot={-10} />
          <div style={{ fontFamily, fontWeight: 800, fontSize: 32, color: NOIR, background: OR, padding: "12px 26px", borderRadius: 40, whiteSpace: "nowrap" }}>
            Une histoire par jour
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// Filigrane des vidéos YouTube (150×150 conseillé) : le même sceau, en petit.
export const Filigrane: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: "transparent", alignItems: "center", justifyContent: "center" }}>
    <div style={{ width: 300, height: 300, borderRadius: 150, background: NOIR, border: `12px solid ${OR}`, display: "flex",
      alignItems: "center", justifyContent: "center", fontFamily: anton, fontSize: 190, color: OR }}>€</div>
  </AbsoluteFill>
);
