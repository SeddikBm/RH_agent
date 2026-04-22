const fs = await import("node:fs/promises");
const path = await import("node:path");
const { Presentation, PresentationFile } = await import("@oai/artifact-tool");

const W = 1280;
const H = 720;

const DECK_ID = "rh-agent-12min-simple";
const OUT_DIR = "C:\\Users\\abderrafea\\RH_agent\\outputs\\rh-agent-presentation-detaillee-12min";
const SCRATCH_DIR = path.resolve(process.env.PPTX_SCRATCH_DIR || path.join("tmp", "slides", DECK_ID));
const PREVIEW_DIR = path.join(SCRATCH_DIR, "preview");
const VERIFICATION_DIR = path.join(SCRATCH_DIR, "verification");
const INSPECT_PATH = path.join(SCRATCH_DIR, "inspect.ndjson");
const MAX_RENDER_VERIFY_LOOPS = 3;

const INK = "#0B1320";
const GRAPHITE = "#334155";
const MUTED = "#6B7A90";
const PAPER = "#F5F8FC";
const PAPER_96 = "#FFFFFFF0";
const WHITE = "#FFFFFF";
const ACCENT = "#1B63F0";
const ACCENT_DARK = "#1747A6";
const GOLD = "#F0A03B";
const CORAL = "#FF6A57";
const MINT = "#19A87A";
const TRANSPARENT = "#00000000";

const TITLE_FACE = "Aptos Display";
const BODY_FACE = "Aptos";
const MONO_FACE = "Aptos Mono";

const SOURCES = {
  project: "Projet local RH Agent: README.md et RAPPORT_PIPELINE_PROJET.md",
  backend: "backend/main.py, backend/config.py, backend/models/database.py",
  analysis: "backend/api/routes/analysis.py",
  rag: "backend/services/rag.py et backend/services/section_extractor.py",
  graph: "backend/agents/graph.py et backend/agents/nodes/*",
  ui: "frontend/src/pages/Upload.jsx, Analyses.jsx, Report.jsx, Jobs.jsx",
  infra: "docker-compose.yml, backend/Dockerfile, frontend/Dockerfile",
};

const SLIDES = [
  {
    kicker: "PROJET RH AGENT",
    title: "Agent RH IA\nPrésentation détaillée du projet",
    subtitle:
      "Une plateforme qui aide le recruteur à trier des CV, sélectionner les meilleurs profils et générer des rapports explicatifs à partir d'une fiche de poste.",
    moment: "Version 10 min +",
    notes:
      "Bonjour. Dans cette présentation, je vais expliquer le projet de manière plus détaillée. L'objectif est que la présentation soit facile à suivre, même en lisant directement les slides. Je vais d'abord rappeler le problème métier, puis montrer la solution, l'architecture, le fonctionnement interne et enfin la valeur du projet.",
    sources: ["project", "analysis", "graph"],
  },
  {
    kicker: "01. PLAN",
    title: "Plan de la présentation",
    subtitle:
      "Je vais présenter le projet en cinq parties : le besoin, la solution, l'architecture, le fonctionnement et la valeur produite.",
    cards: [
      ["Partie 1", "Pourquoi ce projet existe, quel problème RH il cherche à résoudre et quel objectif il poursuit."],
      ["Partie 2", "Comment la solution fonctionne du point de vue utilisateur et quelles technologies sont utilisées."],
      ["Partie 3", "Comment le système classe les CV, calcule les scores et génère un rapport final explicable."],
    ],
    notes:
      "Cette slide sert simplement à cadrer la présentation. Elle annonce le chemin que je vais suivre. Cela permet au jury ou au public de savoir à quoi s'attendre et de garder un fil logique du début à la fin.",
    sources: ["project"],
  },
  {
    kicker: "02. PROBLÈME",
    title: "Le problème métier",
    subtitle:
      "Dans un recrutement, le volume de CV est élevé, le temps est limité et la justification des choix devient difficile.",
    cards: [
      ["Volume de CV", "Pour un poste attractif, un recruteur peut recevoir beaucoup de candidatures très différentes en format et en qualité."],
      ["Temps d'analyse", "Comparer chaque CV à une fiche de poste demande du temps, surtout quand il faut lire compétences, expérience et formation."],
      ["Besoin d'explication", "Le recruteur ne veut pas seulement trier vite. Il veut aussi pouvoir justifier pourquoi un profil est retenu ou écarté."],
    ],
    notes:
      "Ici, il faut insister sur le besoin métier réel. Le problème n'est pas seulement la quantité de CV. Le vrai sujet, c'est aussi la cohérence du tri, la capacité à monter en charge et la nécessité d'expliquer les décisions prises.",
    sources: ["project", "ui"],
  },
  {
    kicker: "03. OBJECTIF",
    title: "L'objectif du projet",
    subtitle:
      "Le projet n'a pas pour but de remplacer le recruteur, mais de lui fournir un outil d'aide à la décision plus rapide et plus structuré.",
    cards: [
      ["Accélérer", "Réduire le temps passé sur le premier tri des candidatures en automatisant les tâches répétitives."],
      ["Structurer", "Transformer des CV et des fiches de poste en données comparables pour obtenir une analyse plus homogène."],
      ["Assister", "Laisser la décision finale au recruteur humain tout en apportant un classement, un score et une explication lisible."],
    ],
    notes:
      "Cette slide est importante, parce qu'elle positionne correctement le projet. On parle bien d'assistance intelligente. Le système aide, mais il ne décide pas seul. Cette posture est essentielle d'un point de vue métier et éthique.",
    sources: ["project", "graph"],
  },
  {
    kicker: "04. SOLUTION",
    title: "La solution proposée",
    subtitle:
      "Le projet combine un tri rapide de masse et une analyse approfondie sur les profils les plus prometteurs.",
    cards: [
      ["Étape 1", "Le système réalise un classement rapide des CV face à un poste grâce à un moteur RAG basé sur la similarité sémantique."],
      ["Étape 2", "Après ce classement, le recruteur choisit les profils à analyser en profondeur avec un pipeline LangGraph."],
      ["Résultat", "Le système produit ensuite un rapport complet avec score, recommandations, points forts, lacunes et export PDF."],
    ],
    notes:
      "Le mot clé ici, c'est la logique en deux phases. Le système ne lance pas une analyse lourde sur tous les CV. Il commence par un tri large, puis il réserve l'analyse détaillée aux profils qui méritent davantage d'attention.",
    sources: ["analysis", "rag", "graph"],
  },
  {
    kicker: "05. STACK",
    title: "Les technologies utilisées",
    subtitle:
      "Le projet repose sur un frontend web, un backend API, une base relationnelle et un moteur de recherche vectorielle.",
    cards: [
      ["Interface", "React + Vite pour créer des postes, déposer les CV, suivre les analyses et consulter les rapports."],
      ["Backend", "FastAPI pour exposer les routes, lancer les traitements, gérer les tâches de fond et organiser le pipeline."],
      ["IA et données", "PostgreSQL pour les données métier, ChromaDB pour la similarité, LLM pour structurer, scorer et expliquer."],
    ],
    notes:
      "Cette slide présente la stack de manière lisible. On peut préciser que Docker Compose permet de lancer l'ensemble rapidement. On peut aussi rappeler que le backend centralise toute la logique métier, tandis que le frontend sert surtout à piloter l'expérience utilisateur.",
    sources: ["backend", "infra", "ui"],
  },
  {
    kicker: "06. ARCHITECTURE",
    title: "Architecture du système",
    subtitle:
      "Les données circulent entre le frontend, l'API, la base SQL, le moteur vectoriel et les modules d'analyse.",
    cards: [
      ["Entrée utilisateur", "Le frontend envoie au backend les CV importés, les fiches de poste et les demandes d'analyse batch ou individuelle."],
      ["Stockage", "Les fichiers, les postes, les analyses et les états de batch sont conservés en base pour garder un historique clair."],
      ["Traitement", "Le backend appelle les services de parsing, d'indexation RAG et le graphe LangGraph pour fabriquer le résultat final."],
    ],
    notes:
      "Il faut montrer ici que l'architecture est modulaire. Chaque composant a une responsabilité précise. Cela rend le projet plus maintenable et plus facile à faire évoluer.",
    sources: ["backend", "analysis", "rag"],
  },
  {
    kicker: "07. PARCOURS",
    title: "Le parcours utilisateur",
    subtitle:
      "Du point de vue du recruteur, l'utilisation suit un chemin simple, de la fiche de poste jusqu'au rapport final.",
    cards: [
      ["1. Préparer", "Le recruteur crée une fiche de poste manuellement ou la fait extraire depuis un document PDF, DOCX ou TXT."],
      ["2. Charger", "Il dépose ensuite plusieurs CV. Le système extrait le texte et prépare l'indexation en arrière-plan."],
      ["3. Analyser", "Le batch classe les candidats, le recruteur choisit les meilleurs profils et obtient ensuite les rapports détaillés."],
    ],
    notes:
      "Cette slide est utile pour montrer que le produit n'est pas seulement un moteur technique. C'est aussi une interface exploitable. Le parcours est guidé et suit une logique métier très claire.",
    sources: ["ui", "analysis"],
  },
  {
    kicker: "08. RAG",
    title: "Comment fonctionne la présélection RAG",
    subtitle:
      "Le système compare les CV et la fiche de poste par sections normalisées au lieu de comparer seulement des textes bruts.",
    cards: [
      ["Découpage", "Chaque CV et chaque fiche de poste sont transformés en quatre sections : compétences, expérience, formation et profil."],
      ["Vectorisation", "Chaque section est convertie en embedding et stockée dans ChromaDB pour permettre la recherche de similarité."],
      ["Classement", "Le système calcule ensuite un score pondéré pour classer rapidement tous les CV par ordre de pertinence."],
    ],
    notes:
      "Le point important est que le projet ne fait pas un matching naïf mot à mot. Il reformule et structure d'abord les documents, puis calcule la proximité par section. Cela donne un tri plus pertinent qu'une simple recherche textuelle.",
    sources: ["rag", "analysis"],
  },
  {
    kicker: "09. LANGGRAPH",
    title: "Comment fonctionne l'analyse détaillée",
    subtitle:
      "Une fois les meilleurs profils choisis, LangGraph exécute une chaîne d'analyse en plusieurs étapes successives.",
    cards: [
      ["Étape 1", "Le système extrait ou réutilise les compétences, les soft skills, les langues et les informations de profil du CV."],
      ["Étape 2", "Il réalise ensuite un matching plus fin entre le CV et le poste, compétence par compétence, avec justification."],
      ["Étape 3", "Enfin, il calcule les scores, génère un rapport en langage naturel et applique des garde-fous avant validation."],
    ],
    notes:
      "Cette slide décrit le cœur intelligent du projet. LangGraph agit comme un orchestrateur. Il garantit l'ordre des étapes, le partage d'état et la possibilité de relancer certaines phases si la validation détecte un problème.",
    sources: ["graph", "analysis"],
  },
  {
    kicker: "10. SCORING",
    title: "Le score final expliqué",
    subtitle:
      "Le score global suit une pondération métier claire. Ensuite, le système combine un jugement LLM et un signal RAG.",
    metrics: [
      ["40 %", "Compétences techniques", "Critère principal du score global"],
      ["30 %", "Expérience", "Missions réalisées et niveau d'adéquation"],
      ["20 %", "Formation", "Diplôme, cursus, certifications"],
      ["10 %", "Profil", "Soft skills, langues, résumé"],
    ],
    notes:
      "Ici, on peut expliquer que la pondération 40, 30, 20, 10 correspond à une logique métier explicite. On peut aussi rappeler que, dans le code, chaque note finale mélange 70 pour cent de score LLM et 30 pour cent de score RAG avant de calculer le score global.",
    sources: ["rag", "graph", "analysis"],
  },
  {
    kicker: "11. SORTIES",
    title: "Ce que le système produit concrètement",
    subtitle:
      "Le résultat final n'est pas seulement un score. Le système génère un dossier de décision complet, lisible et exploitable.",
    cards: [
      ["Classement batch", "Une liste ordonnée des candidats avec leur rang et leurs scores pour orienter rapidement le recruteur."],
      ["Rapport détaillé", "Un document structuré avec adéquation au poste, points forts, points faibles, matching par compétence et recommandation."],
      ["Export PDF", "Un format pratique pour partager, archiver et relire l'analyse avec une vraie traçabilité des résultats."],
    ],
    notes:
      "Cette slide permet de montrer la valeur perçue par l'utilisateur. Le système produit des sorties directement utiles dans un contexte RH réel, pas seulement des variables techniques.",
    sources: ["analysis", "ui"],
  },
  {
    kicker: "12. VALEUR",
    title: "Valeur, limites et perspectives",
    subtitle:
      "Le projet apporte une vraie valeur opérationnelle, mais il doit rester cadré comme un outil d'assistance responsable.",
    cards: [
      ["Valeur", "Le projet fait gagner du temps, améliore l'homogénéité du tri et rend les décisions plus faciles à expliquer."],
      ["Limites", "La qualité dépend du contenu des CV, des modèles utilisés et de la qualité des prompts. Le contrôle humain reste indispensable."],
      ["Suite", "Les évolutions possibles sont l'intégration ATS, des tableaux de bord RH plus complets et des tests qualité plus poussés."],
    ],
    notes:
      "Pour terminer, il faut insister sur un message équilibré. Le projet est utile et crédible, mais il ne supprime pas la responsabilité humaine. Sa vraie force est d'agir comme un copilote RH explicable et industrialisable.",
    sources: ["project", "graph", "infra"],
  },
];

const inspectRecords = [];

async function pathExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function ensureDirs() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  const obsoleteFinalArtifacts = [
    "preview",
    "verification",
    "inspect.ndjson",
    ["presentation", "proto.json"].join("_"),
    ["quality", "report.json"].join("_"),
  ];
  for (const obsolete of obsoleteFinalArtifacts) {
    await fs.rm(path.join(OUT_DIR, obsolete), { recursive: true, force: true });
  }
  await fs.mkdir(SCRATCH_DIR, { recursive: true });
  await fs.mkdir(PREVIEW_DIR, { recursive: true });
  await fs.mkdir(VERIFICATION_DIR, { recursive: true });
}

function lineConfig(fill = TRANSPARENT, width = 0) {
  return { style: "solid", fill, width };
}

function recordShape(slideNo, shape, role, shapeType, x, y, w, h) {
  if (!slideNo) return;
  inspectRecords.push({
    kind: "shape",
    slide: slideNo,
    id: shape?.id || `slide-${slideNo}-${role}-${inspectRecords.length + 1}`,
    role,
    shapeType,
    bbox: [x, y, w, h],
  });
}

function addShape(slide, geometry, x, y, w, h, fill = TRANSPARENT, line = TRANSPARENT, lineWidth = 0, meta = {}) {
  const shape = slide.shapes.add({
    geometry,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: lineConfig(line, lineWidth),
  });
  recordShape(meta.slideNo, shape, meta.role || geometry, geometry, x, y, w, h);
  return shape;
}

function normalizeText(text) {
  if (Array.isArray(text)) {
    return text.map((item) => String(item ?? "")).join("\n");
  }
  return String(text ?? "");
}

function textLineCount(text) {
  const value = normalizeText(text);
  if (!value.trim()) {
    return 0;
  }
  return Math.max(1, value.split(/\n/).length);
}

function requiredTextHeight(text, fontSize, lineHeight = 1.18, minHeight = 8) {
  const lines = textLineCount(text);
  if (lines === 0) {
    return minHeight;
  }
  return Math.max(minHeight, lines * fontSize * lineHeight);
}

function assertTextFits(text, boxHeight, fontSize, role = "text") {
  const required = requiredTextHeight(text, fontSize);
  const tolerance = Math.max(2, fontSize * 0.08);
  if (normalizeText(text).trim() && boxHeight + tolerance < required) {
    throw new Error(
      `${role} text box is too short: height=${boxHeight.toFixed(1)}, required>=${required.toFixed(1)}, ` +
        `lines=${textLineCount(text)}, fontSize=${fontSize}, text=${JSON.stringify(normalizeText(text).slice(0, 90))}`,
    );
  }
}

function wrapText(text, widthChars) {
  const words = normalizeText(text).split(/\s+/).filter(Boolean);
  const lines = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length > widthChars && current) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
  }
  if (current) {
    lines.push(current);
  }
  return lines.join("\n");
}

function recordText(slideNo, shape, role, text, x, y, w, h) {
  const value = normalizeText(text);
  inspectRecords.push({
    kind: "textbox",
    slide: slideNo,
    id: shape?.id || `slide-${slideNo}-${role}-${inspectRecords.length + 1}`,
    role,
    text: value,
    textPreview: value.replace(/\n/g, " | ").slice(0, 180),
    textChars: value.length,
    textLines: textLineCount(value),
    bbox: [x, y, w, h],
  });
}

function applyTextStyle(box, text, size, color, bold, face, align, valign, autoFit, listStyle) {
  box.text = text;
  box.text.fontSize = size;
  box.text.color = color;
  box.text.bold = Boolean(bold);
  box.text.alignment = align;
  box.text.verticalAlignment = valign;
  box.text.typeface = face;
  box.text.insets = { left: 0, right: 0, top: 0, bottom: 0 };
  if (autoFit) {
    box.text.autoFit = autoFit;
  }
  if (listStyle) {
    box.text.style = "list";
  }
}

function addText(
  slide,
  slideNo,
  text,
  x,
  y,
  w,
  h,
  {
    size = 22,
    color = INK,
    bold = false,
    face = BODY_FACE,
    align = "left",
    valign = "top",
    fill = TRANSPARENT,
    line = TRANSPARENT,
    lineWidth = 0,
    autoFit = null,
    listStyle = false,
    checkFit = true,
    role = "text",
  } = {},
) {
  if (!checkFit && textLineCount(text) > 1) {
    throw new Error("checkFit=false is only allowed for single-line headers and labels.");
  }
  if (checkFit) {
    assertTextFits(text, h, size, role);
  }
  const box = addShape(slide, "rect", x, y, w, h, fill, line, lineWidth);
  applyTextStyle(box, text, size, color, bold, face, align, valign, autoFit, listStyle);
  recordText(slideNo, box, role, text, x, y, w, h);
  return box;
}

function addAtmosphere(slide, slideNo) {
  slide.background.fill = PAPER;

  const palettes = [
    ["#DCE9FF", "#E6FBF3", "#FFE8D7"],
    ["#D7E7FF", "#EAFBF0", "#FDE4D9"],
    ["#D9EAFF", "#E1F9F1", "#FFECDD"],
    ["#DCE6FF", "#E8FCF5", "#FFF0D8"],
  ];
  const [cool, mint, warm] = palettes[(slideNo - 1) % palettes.length];

  addShape(slide, "ellipse", 900, -130, 470, 470, `${cool}CC`, TRANSPARENT, 0, { slideNo, role: "bg orb" });
  addShape(slide, "ellipse", -140, 460, 420, 420, `${mint}BB`, TRANSPARENT, 0, { slideNo, role: "bg orb" });
  addShape(slide, "ellipse", 1010, 545, 170, 170, `${warm}D5`, TRANSPARENT, 0, { slideNo, role: "bg orb" });
  addShape(slide, "ellipse", 70, 88, 110, 110, "#FFFFFF95", "#D9E4F2", 1, { slideNo, role: "bg orb" });
  addShape(slide, "ellipse", 968, 52, 240, 240, TRANSPARENT, "#C8DAF4", 1.4, { slideNo, role: "bg ring" });
  addShape(slide, "ellipse", 1032, 116, 110, 110, TRANSPARENT, "#D6E3F6", 1.2, { slideNo, role: "bg ring" });
  addShape(slide, "rect", 0, 0, W, 86, "#FFFFFFAA", TRANSPARENT, 0, { slideNo, role: "top haze" });
}

function addHeader(slide, slideNo, kicker, idx, total) {
  addText(slide, slideNo, String(kicker || "").toUpperCase(), 72, 30, 520, 24, {
    size: 13,
    color: ACCENT_DARK,
    bold: true,
    face: MONO_FACE,
    checkFit: false,
    role: "header",
  });
  addText(slide, slideNo, `${String(idx).padStart(2, "0")} / ${String(total).padStart(2, "0")}`, 1100, 30, 112, 24, {
    size: 13,
    color: ACCENT_DARK,
    bold: true,
    face: MONO_FACE,
    align: "right",
    checkFit: false,
    role: "header",
  });
  addShape(slide, "rect", 72, 62, 1136, 2, "#B7CAE6", TRANSPARENT, 0, { slideNo, role: "header rule" });
  addShape(slide, "ellipse", 63, 53, 18, 18, ACCENT, WHITE, 2, { slideNo, role: "header marker" });
}

function addTitleBlock(slide, slideNo, title, subtitle = null, x = 72, y = 92, w = 760) {
  addText(slide, slideNo, title, x, y, w, 138, {
    size: 40,
    color: INK,
    bold: true,
    face: TITLE_FACE,
    role: "title",
  });
  if (subtitle) {
    addText(slide, slideNo, subtitle, x + 2, y + 144, Math.min(w, 760), 76, {
      size: 19,
      color: GRAPHITE,
      face: BODY_FACE,
      role: "subtitle",
    });
  }
}

function addIconBadge(slide, slideNo, x, y, accent = ACCENT, kind = "signal") {
  addShape(slide, "ellipse", x, y, 54, 54, WHITE, "#D7E3F3", 1.2, { slideNo, role: "icon badge" });
  if (kind === "flow") {
    addShape(slide, "ellipse", x + 13, y + 18, 10, 10, accent, TRANSPARENT, 0, { slideNo, role: "icon glyph" });
    addShape(slide, "ellipse", x + 31, y + 27, 10, 10, accent, TRANSPARENT, 0, { slideNo, role: "icon glyph" });
    addShape(slide, "rect", x + 22, y + 25, 19, 3, INK, TRANSPARENT, 0, { slideNo, role: "icon glyph" });
  } else if (kind === "layers") {
    addShape(slide, "roundRect", x + 13, y + 15, 26, 13, accent, TRANSPARENT, 0, { slideNo, role: "icon glyph" });
    addShape(slide, "roundRect", x + 18, y + 24, 26, 13, GOLD, TRANSPARENT, 0, { slideNo, role: "icon glyph" });
    addShape(slide, "roundRect", x + 23, y + 33, 20, 10, CORAL, TRANSPARENT, 0, { slideNo, role: "icon glyph" });
  } else {
    addShape(slide, "rect", x + 16, y + 29, 6, 12, accent, TRANSPARENT, 0, { slideNo, role: "icon glyph" });
    addShape(slide, "rect", x + 25, y + 21, 6, 20, accent, TRANSPARENT, 0, { slideNo, role: "icon glyph" });
    addShape(slide, "rect", x + 34, y + 14, 6, 27, accent, TRANSPARENT, 0, { slideNo, role: "icon glyph" });
  }
}

function addCard(slide, slideNo, x, y, w, h, label, body, { accent = ACCENT, fill = PAPER_96, line = "#D7E3F3", iconKind = "signal" } = {}) {
  if (h < 180) {
    throw new Error(`Card is too short for editable copy: height=${h.toFixed(1)}, minimum=180.`);
  }
  addShape(slide, "roundRect", x, y, w, h, fill, line, 1.2, { slideNo, role: `card panel: ${label}` });
  addShape(slide, "rect", x, y, 8, h, accent, TRANSPARENT, 0, { slideNo, role: `card accent: ${label}` });
  addIconBadge(slide, slideNo, x + 22, y + 24, accent, iconKind);
  addText(slide, slideNo, label, x + 88, y + 22, w - 108, 28, {
    size: 15,
    color: ACCENT_DARK,
    bold: true,
    face: MONO_FACE,
    role: "card label",
  });
  const wrapped = wrapText(body, Math.max(28, Math.floor(w / 13)));
  const bodyY = y + 86;
  const bodyH = h - (bodyY - y) - 24;
  addText(slide, slideNo, wrapped, x + 24, bodyY, w - 48, bodyH, {
    size: 17,
    color: INK,
    face: BODY_FACE,
    role: `card body: ${label}`,
  });
}

function addMetricCard(slide, slideNo, x, y, w, h, metric, label, note = null, accent = ACCENT) {
  if (h < 138) {
    throw new Error(`Metric card is too short: height=${h.toFixed(1)}, minimum=138.`);
  }
  addShape(slide, "roundRect", x, y, w, h, WHITE, "#D7E3F3", 1.2, { slideNo, role: `metric panel: ${label}` });
  addShape(slide, "rect", x, y, w, 7, accent, TRANSPARENT, 0, { slideNo, role: `metric accent: ${label}` });
  addText(slide, slideNo, metric, x + 22, y + 24, w - 44, 46, {
    size: 32,
    color: INK,
    bold: true,
    face: TITLE_FACE,
    role: "metric value",
  });
  addText(slide, slideNo, label, x + 24, y + 76, w - 48, 26, {
    size: 16,
    color: GRAPHITE,
    face: BODY_FACE,
    role: "metric label",
  });
  if (note) {
    addText(slide, slideNo, note, x + 24, y + h - 36, w - 48, 18, {
      size: 10,
      color: MUTED,
      face: BODY_FACE,
      role: "metric note",
    });
  }
}

function addNotes(slide, body, sourceKeys) {
  const sourceLines = (sourceKeys || []).map((key) => `- ${SOURCES[key] || key}`).join("\n");
  slide.speakerNotes.setText(`${body || ""}\n\n[Sources]\n${sourceLines}`);
}

async function slideCover(presentation) {
  const slideNo = 1;
  const data = SLIDES[0];
  const slide = presentation.slides.add();

  addAtmosphere(slide, slideNo);
  addShape(slide, "rect", 0, 0, W, H, "#FFFFFF99", TRANSPARENT, 0, { slideNo, role: "cover wash" });
  addShape(slide, "rect", 72, 104, 7, 430, ACCENT, TRANSPARENT, 0, { slideNo, role: "cover accent rule" });
  addText(slide, slideNo, data.kicker, 96, 102, 520, 26, {
    size: 13,
    color: ACCENT_DARK,
    bold: true,
    face: MONO_FACE,
    role: "kicker",
  });
  addText(slide, slideNo, data.title, 92, 144, 780, 182, {
    size: 50,
    color: INK,
    bold: true,
    face: TITLE_FACE,
    role: "cover title",
  });
  addText(slide, slideNo, data.subtitle, 96, 332, 700, 94, {
    size: 21,
    color: GRAPHITE,
    face: BODY_FACE,
    role: "cover subtitle",
  });
  addShape(slide, "roundRect", 96, 470, 420, 88, WHITE, "#D7E3F3", 1.2, { slideNo, role: "cover moment panel" });
  addText(slide, slideNo, data.moment, 122, 493, 372, 36, {
    size: 24,
    color: INK,
    bold: true,
    face: TITLE_FACE,
    role: "cover moment",
  });
  addShape(slide, "roundRect", 920, 122, 220, 220, "#FFFFFFA8", "#DCE6F6", 1.2, { slideNo, role: "cover badge panel" });
  addText(slide, slideNo, "2 phases", 972, 154, 120, 42, {
    size: 26,
    color: ACCENT_DARK,
    bold: true,
    face: TITLE_FACE,
    align: "center",
    role: "cover stat",
  });
  addText(slide, slideNo, "RAG pour classer\nLangGraph pour expliquer", 960, 212, 146, 84, {
    size: 16,
    color: GRAPHITE,
    face: BODY_FACE,
    align: "center",
    role: "cover stat body",
  });
  addNotes(slide, data.notes, data.sources);
}

async function slideCards(presentation, idx) {
  const data = SLIDES[idx - 1];
  const slide = presentation.slides.add();

  addAtmosphere(slide, idx);
  addShape(slide, "rect", 0, 0, W, H, "#FFFFFFA8", TRANSPARENT, 0, { slideNo: idx, role: "content wash" });
  addHeader(slide, idx, data.kicker, idx, SLIDES.length);
  addTitleBlock(slide, idx, data.title, data.subtitle, 72, 92, 770);

  const cards = data.cards || [];
  const cols = Math.min(3, cards.length);
  const cardW = (1112 - (cols - 1) * 24) / cols;
  const iconKinds = ["signal", "flow", "layers"];
  const accents = [ACCENT, MINT, GOLD];

  for (let cardIdx = 0; cardIdx < cols; cardIdx += 1) {
    const [label, body] = cards[cardIdx];
    const x = 84 + cardIdx * (cardW + 24);
    addCard(slide, idx, x, 386, cardW, 214, label, body, {
      iconKind: iconKinds[cardIdx % iconKinds.length],
      accent: accents[cardIdx % accents.length],
    });
  }

  addNotes(slide, data.notes, data.sources);
}

async function slideMetrics(presentation, idx) {
  const data = SLIDES[idx - 1];
  const slide = presentation.slides.add();

  addAtmosphere(slide, idx);
  addShape(slide, "rect", 0, 0, W, H, "#FFFFFFAC", TRANSPARENT, 0, { slideNo: idx, role: "metrics wash" });
  addHeader(slide, idx, data.kicker, idx, SLIDES.length);
  addTitleBlock(slide, idx, data.title, data.subtitle, 72, 92, 820);

  const metrics = data.metrics || [];
  const accents = [ACCENT, MINT, GOLD, CORAL];

  if (metrics.length === 4) {
    const positions = [
      { x: 92, y: 344 },
      { x: 648, y: 344 },
      { x: 92, y: 512 },
      { x: 648, y: 512 },
    ];
    for (let metricIdx = 0; metricIdx < 4; metricIdx += 1) {
      const [metric, label, note] = metrics[metricIdx];
      const pos = positions[metricIdx];
      addMetricCard(slide, idx, pos.x, pos.y, 540, 146, metric, label, note, accents[metricIdx]);
    }
  } else {
    const count = Math.min(3, metrics.length);
    const cardW = 330;
    for (let metricIdx = 0; metricIdx < count; metricIdx += 1) {
      const [metric, label, note] = metrics[metricIdx];
      addMetricCard(slide, idx, 92 + metricIdx * 370, 412, cardW, 174, metric, label, note, accents[metricIdx]);
    }
  }

  addNotes(slide, data.notes, data.sources);
}

async function createDeck() {
  await ensureDirs();
  if (!SLIDES.length) {
    throw new Error("SLIDES must contain at least one slide.");
  }

  const presentation = Presentation.create({ slideSize: { width: W, height: H } });
  await slideCover(presentation);
  for (let idx = 2; idx <= SLIDES.length; idx += 1) {
    const data = SLIDES[idx - 1];
    if (data.metrics) {
      await slideMetrics(presentation, idx);
    } else {
      await slideCards(presentation, idx);
    }
  }
  return presentation;
}

async function saveBlobToFile(blob, filePath) {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  await fs.writeFile(filePath, bytes);
}

async function writeInspectArtifact(presentation) {
  inspectRecords.unshift({
    kind: "deck",
    id: DECK_ID,
    slideCount: presentation.slides.count,
    slideSize: { width: W, height: H },
  });
  presentation.slides.items.forEach((slide, index) => {
    inspectRecords.splice(index + 1, 0, {
      kind: "slide",
      slide: index + 1,
      id: slide?.id || `slide-${index + 1}`,
    });
  });
  const lines = inspectRecords.map((record) => JSON.stringify(record)).join("\n") + "\n";
  await fs.writeFile(INSPECT_PATH, lines, "utf8");
}

async function currentRenderLoopCount() {
  const logPath = path.join(VERIFICATION_DIR, "render_verify_loops.ndjson");
  if (!(await pathExists(logPath))) return 0;
  const previous = await fs.readFile(logPath, "utf8");
  return previous.split(/\r?\n/).filter((line) => line.trim()).length;
}

async function nextRenderLoopNumber() {
  return (await currentRenderLoopCount()) + 1;
}

async function appendRenderVerifyLoop(presentation, previewPaths, pptxPath) {
  const logPath = path.join(VERIFICATION_DIR, "render_verify_loops.ndjson");
  const priorCount = await currentRenderLoopCount();
  const record = {
    kind: "render_verify_loop",
    deckId: DECK_ID,
    loop: priorCount + 1,
    maxLoops: MAX_RENDER_VERIFY_LOOPS,
    capReached: priorCount + 1 >= MAX_RENDER_VERIFY_LOOPS,
    timestamp: new Date().toISOString(),
    slideCount: presentation.slides.count,
    previewCount: previewPaths.length,
    previewDir: PREVIEW_DIR,
    inspectPath: INSPECT_PATH,
    pptxPath,
  };
  await fs.appendFile(logPath, JSON.stringify(record) + "\n", "utf8");
  return record;
}

async function verifyAndExport(presentation) {
  await ensureDirs();
  const nextLoop = await nextRenderLoopNumber();
  if (nextLoop > MAX_RENDER_VERIFY_LOOPS) {
    throw new Error(`Render loop cap reached: ${MAX_RENDER_VERIFY_LOOPS}.`);
  }

  await writeInspectArtifact(presentation);
  const previewPaths = [];
  for (let idx = 0; idx < presentation.slides.items.length; idx += 1) {
    const slide = presentation.slides.items[idx];
    const preview = await presentation.export({ slide, format: "png", scale: 1 });
    const previewPath = path.join(PREVIEW_DIR, `slide-${String(idx + 1).padStart(2, "0")}.png`);
    await saveBlobToFile(preview, previewPath);
    previewPaths.push(previewPath);
  }

  const pptxBlob = await PresentationFile.exportPptx(presentation);
  const pptxPath = path.join(OUT_DIR, "output.pptx");
  await pptxBlob.save(pptxPath);
  await appendRenderVerifyLoop(presentation, previewPaths, pptxPath);
  return { pptxPath, previewPaths };
}

const presentation = await createDeck();
const result = await verifyAndExport(presentation);
console.log(result.pptxPath);
