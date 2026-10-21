import React from "react";
import {
  AbsoluteFill, Audio, Easing, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import type { Script } from "./types";

const { fontFamily } = loadFont("normal", { weights: ["500", "700", "800", "900"], subsets: ["latin", "latin-ext"] });

export const FPS = 30;
const NOIR = "#0B0B0D";
const BLANC = "#FFFFFF";
const ORANGE = "#F26A1B";
const GRIS = "#A7A7B0";

const D = { intro: 2.2, titre: 4.0, visuel: 5.5, contexte: 5.0, etape: 4.6, chiffre: 5.5, liste: 5.5, conclusion: 5.0, outro: 3.5 };
const duree = (s: Script, k: keyof typeof D) => Math.round(((s.durees && s.durees[k]) ?? D[k]) * FPS);

function plan(s: Script) {
  const scenes: { id: string; debut: number; longueur: number; i?: number }[] = [];
  let t = 0;
  const ajoute = (id: string, longueur: number, i?: number) => { scenes.push({ id, debut: t, longueur, i }); t += longueur; };
  ajoute("intro", duree(s, "intro"));
  ajoute("titre", duree(s, "titre"));
  ajoute("visuel", duree(s, "visuel"));
  if (s.contexte) ajoute("contexte", duree(s, "contexte"));
  s.etapes.forEach((_, i) => ajoute("etape", duree(s, "etape"), i));
  if (s.chiffre) ajoute("chiffre", duree(s, "chiffre"));
  if (s.liste) ajoute("liste", duree(s, "liste"));
  ajoute("conclusion", duree(s, "conclusion"));
  ajoute("outro", duree(s, "outro"));
  return { scenes, total: t };
}
export const dureeTotale = (s: Script) => plan(s).total;

// ---------------------------------------------------------------- briques d'animation

const useEntree = (delai = 0, raideur = 120) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: f - delai, fps, config: { damping: 18, stiffness: raideur, mass: 0.8 } });
};

const Monte: React.FC<{ delai?: number; children: React.ReactNode; distance?: number }> = ({ delai = 0, children, distance = 60 }) => {
  const p = useEntree(delai);
  return <div style={{ transform: `translateY(${(1 - p) * distance}px)`, opacity: p }}>{children}</div>;
};

const Sortie: React.FC<{ longueur: number; children: React.ReactNode }> = ({ longueur, children }) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [longueur - 8, longueur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const y = interpolate(f, [longueur - 8, longueur], [0, -40], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ opacity: o, transform: `translateY(${y}px)` }}>{children}</AbsoluteFill>;
};

const Fond: React.FC = () => {
  const f = useCurrentFrame();
  const decal = (f * 0.6) % 120;
  return (
    <AbsoluteFill style={{ backgroundColor: NOIR }}>
      <AbsoluteFill style={{
        backgroundImage: "linear-gradient(rgba(255,255,255,0.045) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,0.045) 2px, transparent 2px)",
        backgroundSize: "120px 120px", backgroundPosition: `0 ${decal}px`,
      }} />
      <AbsoluteFill style={{ background: `radial-gradient(circle at 85% 12%, ${ORANGE}33 0%, transparent 45%), radial-gradient(circle at 10% 95%, ${ORANGE}22 0%, transparent 40%)` }} />
      {/* particules : petits points orange qui montent lentement */}
      {Array.from({ length: 22 }).map((_, k) => {
        const x = (k * 397) % 1080;
        const vitesse = 0.6 + ((k * 7) % 5) * 0.25;
        const y = 1920 - ((f * vitesse + k * 211) % 2100);
        const taille = 4 + ((k * 3) % 7);
        return <div key={k} style={{ position: "absolute", left: x, top: y, width: taille, height: taille, borderRadius: "50%",
          background: k % 3 === 0 ? ORANGE : "rgba(255,255,255,0.35)", opacity: 0.55 }} />;
      })}
    </AbsoluteFill>
  );
};

const Puce: React.FC<{ texte: string; delai?: number; plein?: boolean }> = ({ texte, delai = 0, plein = false }) => {
  const p = useEntree(delai, 170);
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 12, padding: "12px 26px", borderRadius: 40, marginRight: 16, marginBottom: 16,
      border: `3px solid ${ORANGE}`, background: plein ? ORANGE : "rgba(242,106,27,0.12)", color: BLANC, fontFamily, fontWeight: 700,
      fontSize: 36, transform: `scale(${0.7 + 0.3 * p})`, opacity: p }}>{texte}</div>
  );
};

// bandeau bas permanent : rubrique · pays · date + hashtags qui défilent
const Bandeau: React.FC<{ s: Script }> = ({ s }) => {
  const f = useCurrentFrame();
  const texte = [s.rubrique, s.pays, s.date].filter(Boolean).join("  •  ");
  const tags = (s.hashtags || []).join("     ") + "     ";
  const largeur = Math.max(1, tags.length * 22);
  const decal = -((f * 3) % largeur);
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 150, height: 120 }}>
      <div style={{ display: "flex", height: 64, alignItems: "stretch" }}>
        <div style={{ background: ORANGE, color: BLANC, fontFamily, fontWeight: 900, fontSize: 30, letterSpacing: 3,
          padding: "0 30px", display: "flex", alignItems: "center" }}>INFO</div>
        <div style={{ flex: 1, background: "rgba(255,255,255,0.95)", color: NOIR, fontFamily, fontWeight: 800, fontSize: 30,
          letterSpacing: 1, display: "flex", alignItems: "center", padding: "0 26px", whiteSpace: "nowrap", overflow: "hidden" }}>{texte}</div>
      </div>
      {tags.trim() && (
        <div style={{ height: 52, background: "rgba(0,0,0,0.75)", overflow: "hidden", whiteSpace: "nowrap", display: "flex", alignItems: "center" }}>
          <div style={{ transform: `translateX(${decal}px)`, fontFamily, fontWeight: 700, fontSize: 28, color: ORANGE }}>{tags + tags + tags}</div>
        </div>
      )}
    </div>
  );
};

const Logo: React.FC<{ taille?: number }> = ({ taille = 46 }) => (
  <div style={{ fontFamily, fontWeight: 900, fontSize: taille, color: BLANC, letterSpacing: 1, display: "flex", alignItems: "baseline" }}>
    DEC<span style={{ color: ORANGE }}>I</span>DE<span style={{ fontWeight: 600, fontSize: taille * 0.42, marginLeft: 6 }}>media</span>
  </div>
);

const Pastille: React.FC<{ texte: string; delai?: number }> = ({ texte, delai = 0 }) => {
  const p = useEntree(delai, 160);
  return (
    <div style={{ display: "inline-block", background: ORANGE, color: BLANC, fontFamily, fontWeight: 800, fontSize: 40, letterSpacing: 3,
      padding: "14px 30px", borderRadius: 6, transform: `scale(${0.6 + 0.4 * p})`, opacity: p, transformOrigin: "left center" }}>
      {texte}
    </div>
  );
};

const Souligne: React.FC<{ delai?: number; largeur?: number }> = ({ delai = 0, largeur = 520 }) => {
  const f = useCurrentFrame();
  const w = interpolate(f - delai, [0, 18], [0, largeur], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  return <div style={{ height: 10, width: w, background: ORANGE, borderRadius: 5, marginTop: 26 }} />;
};

// ---------------------------------------------------------------- scènes

const Intro: React.FC<{ s: Script }> = ({ s }) => {
  const f = useCurrentFrame();
  const balayage = interpolate(f, [0, 16], [-1080, 0], { extrapolateRight: "clamp", easing: Easing.out(Easing.exp) });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div style={{ position: "absolute", top: 860, left: 0, height: 200, width: 1080, background: ORANGE, transform: `translateX(${balayage}px) skewY(-4deg)` }} />
      <Monte delai={8}><div style={{ fontFamily, fontWeight: 900, fontSize: 92, color: BLANC, letterSpacing: 4 }}>{s.rubrique}</div></Monte>
      {s.pays && <Monte delai={14}><div style={{ fontFamily, fontWeight: 700, fontSize: 40, color: NOIR, letterSpacing: 10, marginTop: 10 }}>{s.pays}</div></Monte>}
    </AbsoluteFill>
  );
};

const Titre: React.FC<{ s: Script }> = ({ s }) => (
  <AbsoluteFill style={{ justifyContent: "center", padding: "0 80px" }}>
    <Pastille texte={s.rubrique} />
    <div style={{ height: 40 }} />
    {s.titre.map((ligne, i) => (
      <Monte key={i} delai={6 + i * 7} distance={90}>
        <div style={{ fontFamily, fontWeight: 900, fontSize: s.titre.length > 4 ? 78 : s.titre.length > 3 ? 92 : 108, lineHeight: 1.05, color: BLANC }}>{ligne}</div>
      </Monte>
    ))}
    <Souligne delai={6 + s.titre.length * 7} />
    <div style={{ height: 50 }} />
    <div>
      {s.pays && <Puce texte={`📍 ${s.pays}`} delai={14 + s.titre.length * 7} />}
      {s.date && <Puce texte={`🗓 ${s.date}`} delai={20 + s.titre.length * 7} />}
    </div>
  </AbsoluteFill>
);

const Contexte: React.FC<{ s: Script }> = ({ s }) => {
  const p = useEntree(2, 150);
  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: "0 80px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 30 }}>
        <div style={{ width: 150, height: 150, borderRadius: "50%", background: ORANGE, display: "flex", alignItems: "center",
          justifyContent: "center", fontSize: 84, transform: `scale(${p}) rotate(${(1 - p) * -90}deg)` }}>🎯</div>
        <Monte delai={6}><div style={{ fontFamily, fontWeight: 900, fontSize: 70, color: BLANC, letterSpacing: 2 }}>POUR VOUS</div></Monte>
      </div>
      <Souligne delai={10} largeur={340} />
      <div style={{ height: 50 }} />
      <Monte delai={14} distance={70}>
        <div style={{ fontFamily, fontWeight: 700, fontSize: 64, color: BLANC, lineHeight: 1.25, background: "rgba(255,255,255,0.06)",
          borderLeft: `12px solid ${ORANGE}`, borderRadius: 18, padding: "40px 44px" }}>{s.contexte}</div>
      </Monte>
    </AbsoluteFill>
  );
};

const Visuel: React.FC<{ s: Script; longueur: number }> = ({ s, longueur }) => {
  const f = useCurrentFrame();
  const rayon = interpolate(f, [0, 22], [0, 120], { extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const zoom = interpolate(f, [0, longueur], [1.08, 1.0]);
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: 260 }}>
      <div style={{ width: 920, height: 920, borderRadius: 36, overflow: "hidden", clipPath: `circle(${rayon}% at 50% 50%)`,
        boxShadow: `0 0 0 8px ${ORANGE}, 0 40px 120px rgba(0,0,0,0.6)` }}>
        <Img src={staticFile(s.image)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` }} />
      </div>
      <div style={{ padding: "70px 90px 0" }}>
        <Monte delai={26}>
          <div style={{ fontFamily, fontWeight: 700, fontSize: 56, lineHeight: 1.25, color: BLANC, textAlign: "center" }}>
            « {s.accroche} »
          </div>
        </Monte>
      </div>
    </AbsoluteFill>
  );
};

const EtapeScene: React.FC<{ s: Script; i: number }> = ({ s, i }) => {
  const e = s.etapes[i];
  const f = useCurrentFrame();
  const pIcone = useEntree(4, 200);
  const rotation = interpolate(pIcone, [0, 1], [-30, 0]);
  const tour = interpolate(f, [0, 140], [0, 120]);
  return (
    <AbsoluteFill style={{ padding: "330px 80px 0" }}>
      {/* filigrane : grand numéro + anneau pointillé qui tourne */}
      <div style={{ position: "absolute", right: -40, top: 640, fontFamily, fontWeight: 900, fontSize: 620, color: "rgba(255,255,255,0.04)", lineHeight: 1 }}>
        {i + 1}
      </div>
      <div style={{ position: "absolute", right: 60, top: 300, width: 300, height: 300, borderRadius: "50%",
        border: `4px dashed ${ORANGE}55`, transform: `rotate(${tour}deg)` }} />
      {/* compteur d'étapes */}
      <div style={{ display: "flex", gap: 18, marginBottom: 70 }}>
        {s.etapes.map((_, k) => (
          <div key={k} style={{ height: 14, flex: 1, borderRadius: 7, background: k < i ? ORANGE : k === i ? BLANC : "rgba(255,255,255,0.18)",
            transform: k === i ? `scaleX(${interpolate(f, [0, 15], [0.3, 1], { extrapolateRight: "clamp" })})` : undefined, transformOrigin: "left" }} />
        ))}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 40 }}>
        <Monte><div style={{ fontFamily, fontWeight: 900, fontSize: 220, color: ORANGE, lineHeight: 1 }}>{String(i + 1).padStart(2, "0")}</div></Monte>
        <div style={{ width: 230, height: 230, borderRadius: "50%", background: "rgba(255,255,255,0.08)", border: `6px solid ${ORANGE}`,
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 130,
          transform: `scale(${pIcone}) rotate(${rotation}deg)` }}>{e.icone}</div>
      </div>
      <div style={{ height: 60 }} />
      <Monte delai={8} distance={80}><div style={{ fontFamily, fontWeight: 900, fontSize: 104, color: BLANC, lineHeight: 1.05 }}>{e.titre}</div></Monte>
      <Souligne delai={14} largeur={300} />
      <div style={{ height: 30 }} />
      <Monte delai={16}><div style={{ fontFamily, fontWeight: 600, fontSize: e.detail.length > 120 ? 48 : 56, color: "#D9D9DE", lineHeight: 1.32 }}>{e.detail}</div></Monte>
    </AbsoluteFill>
  );
};

const Chiffre: React.FC<{ s: Script; longueur: number }> = ({ s, longueur }) => {
  const c = s.chiffre!;
  const f = useCurrentFrame();
  const progression = interpolate(f, [10, longueur - 15], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const brut = c.compte_a_rebours ? c.valeur * (1 - progression) : c.valeur * progression;
  const affiche = (c.compte_a_rebours ? Math.ceil(brut) : brut).toLocaleString("fr-FR", { maximumFractionDigits: c.decimales ?? 0, minimumFractionDigits: c.compte_a_rebours ? 0 : (c.decimales ?? 0) });
  const R = 300, C = 2 * Math.PI * R;
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div style={{ position: "relative", width: 720, height: 720 }}>
        <svg width={720} height={720} style={{ position: "absolute", transform: "rotate(-90deg)" }}>
          <circle cx={360} cy={360} r={R} stroke="rgba(255,255,255,0.12)" strokeWidth={34} fill="none" />
          <circle cx={360} cy={360} r={R} stroke={ORANGE} strokeWidth={34} fill="none" strokeLinecap="round"
            strokeDasharray={C} strokeDashoffset={C * (1 - progression)} />
        </svg>
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <div style={{ fontFamily, fontWeight: 900, fontSize: affiche.length > 5 ? 150 : affiche.length > 3 ? 200 : 260, color: BLANC, lineHeight: 1 }}>{affiche}</div>
          <div style={{ fontFamily, fontWeight: 800, fontSize: 60, color: ORANGE, letterSpacing: 4 }}>{c.unite.toUpperCase()}</div>
        </AbsoluteFill>
      </div>
      <div style={{ height: 70 }} />
      <Monte delai={12}><div style={{ fontFamily, fontWeight: 700, fontSize: 60, color: BLANC, textAlign: "center", padding: "0 90px" }}>{c.legende}</div></Monte>
    </AbsoluteFill>
  );
};

const Liste: React.FC<{ s: Script }> = ({ s }) => {
  const l = s.liste!;
  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: "0 80px" }}>
      <Monte><div style={{ fontFamily, fontWeight: 900, fontSize: 84, color: BLANC, lineHeight: 1.1 }}>{l.titre}</div></Monte>
      <Souligne delai={6} largeur={260} />
      <div style={{ height: 60 }} />
      {l.items.map((it, k) => (
        <Monte key={k} delai={14 + k * 12} distance={50}>
          <div style={{ display: "flex", alignItems: "center", gap: 30, marginBottom: 34, background: "rgba(255,255,255,0.07)",
            borderLeft: `14px solid ${ORANGE}`, borderRadius: 18, padding: "34px 40px" }}>
            <div style={{ width: 64, height: 64, borderRadius: "50%", background: ORANGE, color: BLANC, fontFamily, fontWeight: 900,
              fontSize: 40, display: "flex", alignItems: "center", justifyContent: "center" }}>✓</div>
            <div style={{ fontFamily, fontWeight: 700, fontSize: 58, color: BLANC }}>{it}</div>
          </div>
        </Monte>
      ))}
    </AbsoluteFill>
  );
};

const Conclusion: React.FC<{ s: Script }> = ({ s }) => (
  <AbsoluteFill style={{ justifyContent: "center", padding: "0 80px" }}>
    <Monte><div style={{ fontFamily, fontWeight: 800, fontSize: 44, color: ORANGE, letterSpacing: 6 }}>À RETENIR</div></Monte>
    <div style={{ height: 40 }} />
    <Monte delai={8} distance={80}><div style={{ fontFamily, fontWeight: 900, fontSize: 90, color: BLANC, lineHeight: 1.12 }}>{s.conclusion}</div></Monte>
    <Souligne delai={16} />
    {s.source && <Monte delai={22}><div style={{ fontFamily, fontWeight: 500, fontSize: 40, color: GRIS, marginTop: 50 }}>{s.source}</div></Monte>}
  </AbsoluteFill>
);

const Outro: React.FC<{ s: Script }> = ({ s }) => {
  const p = useEntree(0, 140);
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", background: ORANGE }}>
      <div style={{ transform: `scale(${0.7 + 0.3 * p})`, opacity: p, textAlign: "center" }}>
        <div style={{ background: NOIR, padding: "40px 60px", borderRadius: 20, display: "inline-block" }}><Logo taille={110} /></div>
        <div style={{ fontFamily, fontWeight: 900, fontSize: 66, color: NOIR, marginTop: 50, letterSpacing: 2 }}>COMPRENDRE POUR DÉCIDER</div>
        <Monte delai={14}><div style={{ fontFamily, fontWeight: 700, fontSize: 46, color: BLANC, marginTop: 40 }}>Abonnez-vous pour l'info utile</div></Monte>
        <div style={{ marginTop: 60, padding: "0 60px", display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 14 }}>
          {(s.hashtags || []).slice(0, 6).map((h, k) => (
            <Monte key={k} delai={20 + k * 4} distance={30}>
              <div style={{ background: NOIR, color: BLANC, fontFamily, fontWeight: 700, fontSize: 34, padding: "10px 22px", borderRadius: 30 }}>{h}</div>
            </Monte>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- composition

export const Explainer: React.FC<Script> = (s) => {
  const { scenes, total } = plan(s);
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ fontFamily }}>
      <Fond />
      {scenes.map((sc, k) => (
        <Sequence key={k} from={sc.debut} durationInFrames={sc.longueur}>
          <Sortie longueur={sc.longueur}>
            {sc.id === "intro" && <Intro s={s} />}
            {sc.id === "titre" && <Titre s={s} />}
            {sc.id === "visuel" && <Visuel s={s} longueur={sc.longueur} />}
            {sc.id === "contexte" && <Contexte s={s} />}
            {sc.id === "etape" && <EtapeScene s={s} i={sc.i!} />}
            {sc.id === "chiffre" && <Chiffre s={s} longueur={sc.longueur} />}
            {sc.id === "liste" && <Liste s={s} />}
            {sc.id === "conclusion" && <Conclusion s={s} />}
            {sc.id === "outro" && <Outro s={s} />}
          </Sortie>
        </Sequence>
      ))}
      {/* bandeau permanent : logo + barre de progression (rétention sur Shorts) */}
      {f < total - duree(s, "outro") && (
        <AbsoluteFill style={{ pointerEvents: "none" }}>
          <div style={{ position: "absolute", top: 0, left: 0, height: 12, width: `${(f / total) * 100}%`, background: ORANGE }} />
          <div style={{ position: "absolute", top: 70, right: 70, background: "rgba(0,0,0,0.55)", padding: "14px 24px", borderRadius: 10 }}><Logo /></div>
          {f > duree(s, "intro") && <Bandeau s={s} />}
          <div style={{ position: "absolute", bottom: 90, left: 80, fontFamily, fontWeight: 600, fontSize: 30, color: GRIS, letterSpacing: 2 }}>
            {s.audio ? "Illustrations générées · voix de synthèse" : "Illustrations générées"}
          </div>
        </AbsoluteFill>
      )}
      {s.audio && <Audio src={staticFile(s.audio)} />}
      {s.musique && (
        <Audio src={staticFile(s.musique)} loop
          volume={(fr) => (s.volume_musique ?? 0.10) * interpolate(fr, [0, 20, total - 45, total], [0, 1, 1, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" })} />
      )}
    </AbsoluteFill>
  );
};
