const {
  Presentation,
  PresentationFile,
  row,
  column,
  grid,
  layers,
  panel,
  text,
  image,
  shape,
  rule,
  fill,
  hug,
  wrap,
  fixed,
  fr,
  auto,
  grow,
  drawSlideToCtx,
} = await import(
  "file:///C:/Users/Matt/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs"
);

const { Canvas } = await import(
  "file:///C:/Users/Matt/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/node_modules/skia-canvas/lib/index.mjs"
);
const fs = await import("node:fs/promises");

const WIDTH = 1920;
const HEIGHT = 1080;
const BASE_UNIT = 8;
const ROOT = "C:/Users/Matt/OneDrive/Documents/BuffaloEvictions";
const PREVIEW_DIR = "scratch/presentation_walkthrough/rendered";

const colors = {
  paper: "#F6F3EE",
  paperAlt: "#EEE7DE",
  ink: "#102030",
  navy: "#13293D",
  slate: "#415A77",
  muted: "#66778A",
  teal: "#2A7F8C",
  tealSoft: "#DCECEF",
  gold: "#C98A2E",
  rust: "#C6544C",
  rustSoft: "#F3DEDB",
  moss: "#5F7A4F",
  mossSoft: "#E4EBDD",
  line: "#D2C7BB",
  white: "#FFFFFF",
};

const assets = {
  hotspots: `${ROOT}/scratch/presentation_assets/hotspots_top8.png`,
  earlyIntervention: `${ROOT}/scratch/presentation_assets/early_intervention_top8.png`,
  transitions: `${ROOT}/scratch/presentation_assets/transition_probs.png`,
  hamlinCase: `${ROOT}/scratch/presentation_assets/hamlin_case_study_v2.png`,
  horizonSummary: `${ROOT}/scratch/presentation_assets/horizon_summary.png`,
};

async function fileToDataUrl(path) {
  const bytes = await fs.readFile(path);
  const ext = path.split(".").pop()?.toLowerCase();
  const contentType =
    ext === "jpg" || ext === "jpeg"
      ? "image/jpeg"
      : ext === "webp"
        ? "image/webp"
        : "image/png";
  return {
    dataUrl: `data:${contentType};base64,${bytes.toString("base64")}`,
    contentType,
  };
}

const assetPayloads = {
  hotspots: await fileToDataUrl(assets.hotspots),
  earlyIntervention: await fileToDataUrl(assets.earlyIntervention),
  transitions: await fileToDataUrl(assets.transitions),
  hamlinCase: await fileToDataUrl(assets.hamlinCase),
  horizonSummary: await fileToDataUrl(assets.horizonSummary),
};

const deckFacts = {
  latestCurrentMonth: "2026-05-01",
  latestForecastMonth: "2026-05-01",
  latestBacktestMonth: "2025-05-01",
  currentStateMix: [
    ["Stable", "59"],
    ["Improving", "10"],
    ["Chronic Distress", "9"],
    ["Emerging Risk", "7"],
    ["Rapid Deterioration", "5"],
  ],
  coverMetrics: [
    ["6", "early-intervention candidates", "6m live forecast, non-severe tracts at 20%+ risk"],
    ["5", "rapid-deterioration tracts", "current snapshot as of 2026-05-01"],
    ["18", "tracts above 20% risk", "latest 6m live-scored snapshot as of 2026-05-01"],
  ],
};

function slideShell(content, background = colors.paper) {
  return layers(
    { name: "slide-shell", width: fill, height: fill },
    [
      shape({
        name: "background",
        width: fill,
        height: fill,
        fill: background,
      }),
      content,
    ]
  );
}

function titleBlock({ kicker, title, subtitle, maxWidth = 1160 }) {
  return column(
    { name: "title-block", width: fill, height: hug, gap: 14 },
    [
      kicker
        ? text(kicker.toUpperCase(), {
            name: "kicker",
            width: wrap(440),
            height: hug,
            style: {
              fontSize: 18,
              bold: true,
              color: colors.teal,
              allCaps: true,
              letterSpacing: 0.8,
            },
          })
        : null,
      text(title, {
        name: "title",
        width: wrap(maxWidth),
        height: hug,
        style: {
          fontSize: 58,
          bold: true,
          color: colors.ink,
          fontFace: "Georgia",
        },
      }),
      subtitle
        ? text(subtitle, {
            name: "subtitle",
            width: wrap(maxWidth),
            height: hug,
            style: {
              fontSize: 25,
              color: colors.slate,
            },
          })
        : null,
    ].filter(Boolean)
  );
}

function footer(textValue) {
  return text(textValue, {
    name: "footer",
    width: fill,
    height: hug,
    style: {
      fontSize: 12,
      color: colors.muted,
    },
  });
}

function metricBlock(value, label, note, color = colors.navy) {
  return column(
    { name: `metric-${label}`, width: fill, height: hug, gap: 8 },
    [
      text(value, {
        name: "metric-value",
        width: fill,
        height: hug,
        style: {
          fontSize: 70,
          bold: true,
          color,
          fontFace: "Georgia",
        },
      }),
      text(label, {
        name: "metric-label",
        width: wrap(320),
        height: hug,
        style: {
          fontSize: 23,
          bold: true,
          color: colors.ink,
        },
      }),
      text(note, {
        name: "metric-note",
        width: wrap(320),
        height: hug,
        style: {
          fontSize: 16,
          color: colors.slate,
        },
      }),
      rule({
        name: "metric-rule",
        width: fixed(180),
        stroke: colors.line,
        weight: 2,
      }),
    ]
  );
}

function bulletList(items, width = 560, fontSize = 24) {
  return column(
    { name: "bullet-list", width: fill, height: hug, gap: 14 },
    items.map((item, index) =>
      text(`• ${item}`, {
        name: `bullet-${index + 1}`,
        width: wrap(width),
        height: hug,
        style: {
          fontSize,
          color: colors.ink,
        },
      })
    )
  );
}

function stepColumn(number, pageName, action, options = {}) {
  const {
    numberSize = 56,
    titleSize = 21,
    bodySize = 17,
    textWidth = 290,
  } = options;
  return column(
    { name: `step-${number}`, width: fill, height: hug, gap: 10 },
    [
      text(String(number), {
        name: `step-number-${number}`,
        width: fill,
        height: hug,
        style: {
          fontSize: numberSize,
          bold: true,
          color: colors.gold,
          fontFace: "Georgia",
        },
      }),
      text(pageName, {
        name: `step-page-${number}`,
        width: wrap(textWidth),
        height: hug,
        style: {
          fontSize: titleSize,
          bold: true,
          color: colors.ink,
        },
      }),
      text(action, {
        name: `step-action-${number}`,
        width: wrap(textWidth),
        height: hug,
        style: {
          fontSize: bodySize,
          color: colors.slate,
        },
      }),
    ]
  );
}

function softNote(title, body, fillColor) {
  return panel(
    {
      name: `${title}-panel`,
      width: fill,
      height: hug,
      padding: { x: 20, y: 18 },
      fill: fillColor,
    },
    column(
      { width: fill, height: hug, gap: 8 },
      [
        text(title, {
          width: fill,
          height: hug,
          style: {
            fontSize: 18,
            bold: true,
            color: colors.ink,
          },
        }),
        text(body, {
          width: fill,
          height: hug,
          style: {
            fontSize: 15,
            color: colors.slate,
          },
        }),
      ]
    )
  );
}

const presentation = Presentation.create({
  slideSize: { width: WIDTH, height: HEIGHT },
});

function addSlide(node) {
  const slide = presentation.slides.add();
  slide.compose(node, {
    frame: { left: 0, top: 0, width: WIDTH, height: HEIGHT },
    baseUnit: BASE_UNIT,
  });
  return slide;
}

addSlide(
  slideShell(
    row(
      {
        name: "cover-root",
        width: fill,
        height: fill,
        padding: { x: 84, y: 76 },
        gap: 56,
        align: "stretch",
      },
      [
        column(
          { name: "cover-left", width: grow(1.2), height: fill, gap: 26, justify: "center" },
          [
            text("BUFFALO HOUSING INSTABILITY INTELLIGENCE PLATFORM", {
              name: "cover-kicker",
              width: wrap(820),
              height: hug,
              style: {
                fontSize: 18,
                bold: true,
                color: colors.teal,
                letterSpacing: 1.1,
              },
            }),
            text("How to use the dashboard like an intervention workflow, not just a map gallery.", {
              name: "cover-title",
              width: wrap(920),
              height: hug,
              style: {
                fontSize: 66,
                bold: true,
                color: colors.ink,
                fontFace: "Georgia",
              },
            }),
            text(
              "This walk-through uses live app insights to show how current hotspots, forecast risk, tract history, and state transitions work together to prioritize action.",
              {
                name: "cover-subtitle",
                width: wrap(820),
                height: hug,
                style: {
                  fontSize: 28,
                  color: colors.slate,
                },
              }
            ),
            rule({
              name: "cover-rule",
              width: fixed(240),
              stroke: colors.gold,
              weight: 5,
            }),
            text(
              "Current-condition pages and live forecast pages now both reflect data through 2026-05-01. Historical backtest forecast rows remain available through 2025-05-01 for evaluation and case-study use.",
              {
                name: "cover-date-note",
                width: wrap(760),
                height: hug,
                style: {
                  fontSize: 18,
                  color: colors.muted,
                },
              }
            ),
          ]
        ),
        column(
          { name: "cover-right", width: fixed(420), height: fill, gap: 22, justify: "center" },
          deckFacts.coverMetrics.map((metric, index) =>
            metricBlock(metric[0], metric[1], metric[2], index === 0 ? colors.teal : index === 1 ? colors.rust : colors.gold)
          )
        ),
      ]
    )
  )
);

addSlide(
  slideShell(
    column(
      {
        name: "workflow-root",
        width: fill,
        height: fill,
        padding: { x: 84, y: 72 },
        gap: 34,
      },
      [
        titleBlock({
          kicker: "Operator Workflow",
          title: "Use the app in a sequence that moves from visible distress to future risk.",
          subtitle:
            "The dashboard is strongest when each page answers a different question in the same decision flow.",
        }),
        row(
          { name: "workflow-main", width: fill, height: fill, gap: 44, align: "start" },
          [
            row(
              { name: "workflow-steps", width: grow(1.25), height: fill, gap: 28, align: "start" },
              [
                column(
                  { width: grow(1), height: hug, gap: 14 },
                  [
                    stepColumn(
                      1,
                      "Hotspot Analysis",
                      "Find the tracts already showing concentrated current distress.",
                      { numberSize: 44, titleSize: 18, bodySize: 15, textWidth: 250 }
                    ),
                    stepColumn(
                      2,
                      "Tract-Level Forecast Risk",
                      "Compare severe-risk probabilities across 1m, 3m, 6m, and 12m horizons.",
                      { numberSize: 44, titleSize: 18, bodySize: 15, textWidth: 250 }
                    ),
                    stepColumn(
                      3,
                      "Early Intervention",
                      "Focus on non-severe tracts where earlier action still matters.",
                      { numberSize: 44, titleSize: 18, bodySize: 15, textWidth: 250 }
                    ),
                  ]
                ),
                column(
                  { width: grow(1), height: hug, gap: 14 },
                  [
                    stepColumn(
                      4,
                      "Forecast Risk Map",
                      "Check whether the flagged tracts are isolated or part of a cluster or corridor.",
                      { numberSize: 44, titleSize: 18, bodySize: 15, textWidth: 250 }
                    ),
                    stepColumn(
                      5,
                      "Tract Explorer + State Transitions",
                      "Validate tract history and judge how sticky the surrounding state pattern tends to be.",
                      { numberSize: 44, titleSize: 18, bodySize: 15, textWidth: 250 }
                    ),
                  ]
                ),
              ]
            ),
            column(
              { name: "workflow-right", width: fixed(520), height: fill, gap: 20 },
              [
                softNote(
                  "Current state snapshot",
                  "As of 2026-05-01 the latest tract-state mix is 59 Stable, 10 Improving, 9 Chronic Distress, 7 Emerging Risk, and 5 Rapid Deterioration. That is the current-condition context the hotspot pages start from.",
                  colors.tealSoft
                ),
                panel(
                  {
                    name: "state-mix-panel",
                    width: fill,
                    height: hug,
                    padding: { x: 20, y: 18 },
                    fill: colors.paperAlt,
                  },
                  column(
                    { width: fill, height: hug, gap: 10 },
                    [
                      text("Latest tract-state counts", {
                        width: fill,
                        height: hug,
                        style: { fontSize: 18, bold: true, color: colors.ink },
                      }),
                      ...deckFacts.currentStateMix.map(([name, value]) =>
                        row(
                          { width: fill, height: hug, justify: "between" },
                          [
                            text(name, {
                              width: grow(1),
                              height: hug,
                              style: { fontSize: 17, color: colors.slate },
                            }),
                            text(value, {
                              width: hug,
                              height: hug,
                              style: { fontSize: 17, bold: true, color: colors.ink },
                            }),
                          ]
                        )
                      ),
                    ]
                  )
                ),
                softNote(
                  "Mind the two score sets",
                  "The app now carries both live_scoring rows and holdout_backtest rows. Live forecast pages are current through 2026-05-01, while historical backtest rows through 2025-05-01 remain useful for explaining how the model behaved before outcomes were known.",
                  colors.rustSoft
                ),
              ]
            ),
          ]
        ),
        footer("Source: analytics.tract_state_history and analytics.tract_forecast_scores in the app database.")
      ]
    )
  )
);

addSlide(
  slideShell(
    column(
      {
        name: "hotspots-root",
        width: fill,
        height: fill,
        padding: { x: 84, y: 70 },
        gap: 28,
      },
      [
        titleBlock({
          kicker: "Hotspot Analysis",
          title: "Start with what is already visible in the current neighborhood condition data.",
          subtitle:
            "This page is the best first pass for asking where distress is already concentrated, persistent, or escalating.",
        }),
        row(
          { name: "hotspots-main", width: fill, height: grow(1), gap: 40, align: "start" },
          [
            image({
              name: "hotspots-chart",
              dataUrl: assetPayloads.hotspots.dataUrl,
              contentType: assetPayloads.hotspots.contentType,
              width: fixed(980),
              height: fixed(610),
              fit: "contain",
              alt: "Top current hotspots chart",
            }),
            column(
              { name: "hotspots-right", width: grow(1), height: fill, gap: 14 },
              [
                text("What the current snapshot says", {
                  width: wrap(520),
                  height: hug,
                  style: { fontSize: 30, bold: true, color: colors.ink },
                }),
                bulletList([
                  "Hamlin Park tract 36029005202 is the strongest current hotspot at a combined trajectory score of 98.3 and is already classified as Rapid Deterioration.",
                  "Delavan Grider, Genesee-Moselle, and Masten Park also sit above 91, which means the current-risk list is not a single-tract story.",
                  "Kensington-Bailey, the second Hamlin Park tract, and North Park are not yet in Rapid Deterioration, but they already appear high on the current-risk leaderboard as Emerging Risk tracts.",
                  ], 520, 21),
                text("How to use it", {
                  width: wrap(520),
                  height: hug,
                  style: { fontSize: 23, bold: true, color: colors.teal },
                }),
                bulletList([
                  "Sort by trajectory score to find the most concentrated current risk.",
                  "Use persistence and months in state to separate one-month spikes from repeated pressure.",
                  "Save the top tracts for cross-checking against forecast risk and tract history.",
                  ], 520, 18),
              ]
            ),
          ]
        ),
        footer(
          "Current hotspot snapshot as of 2026-05-01. Highest tracts shown: Hamlin Park 36029005202, Delavan Grider 36029003400, Genesee-Moselle 36029003600, and Masten Park 36029003302."
        ),
      ]
    )
  )
);

addSlide(
  slideShell(
    column(
      {
        name: "forecast-root",
        width: fill,
        height: fill,
        padding: { x: 84, y: 70 },
        gap: 26,
      },
      [
        titleBlock({
          kicker: "Forecast Risk + Early Intervention",
          title: "Move next to the forecast pages to separate imminent risk from actionable early warning.",
          subtitle:
            "The forecast views answer a different question than hotspots: not what is already bad, but what is most likely to deteriorate next.",
        }),
        row(
          { name: "forecast-main", width: fill, height: grow(1), gap: 36, align: "start" },
          [
            column(
              { name: "forecast-left", width: fixed(540), height: fill, gap: 16 },
              [
                image({
                  name: "horizon-summary",
                  dataUrl: assetPayloads.horizonSummary.dataUrl,
                  contentType: assetPayloads.horizonSummary.contentType,
                  width: fixed(540),
                  height: fixed(280),
                  fit: "contain",
                  alt: "Forecast horizon summary chart",
                }),
                bulletList([
                  "At the latest live-scored month, 18 tracts sit above 20% risk on the 6m horizon and 6 of those qualify as early-intervention candidates because they are not already severe.",
                  "Longer horizons still widen the watchlist: the average risk rises from 8.6% on the 1m horizon to 22.2% on the 12m horizon, so the horizon choice changes how aggressive the scan feels.",
                  "Kensington-Bailey now leads the live early-intervention list. Use Forecast Risk for cross-horizon comparison and Early Intervention Candidates when the goal is to act before severity is obvious.",
                  ], 520, 17),
              ]
            ),
            image({
              name: "early-intervention-chart",
              dataUrl: assetPayloads.earlyIntervention.dataUrl,
              contentType: assetPayloads.earlyIntervention.contentType,
              width: fixed(1130),
              height: fixed(620),
              fit: "contain",
              alt: "Top early intervention candidates chart",
            }),
          ]
        ),
        footer(
          "Forecast snapshot uses the latest live-scored month in analytics.tract_forecast_scores: 2026-05-01. Example 6m forecast metrics: average probability 0.141, max probability 0.797, 18 tracts above 20% risk."
        ),
      ]
    )
  )
);

addSlide(
  slideShell(
    column(
      {
        name: "case-root",
        width: fill,
        height: fill,
        padding: { x: 84, y: 70 },
        gap: 26,
      },
      [
        titleBlock({
          kicker: "Tract Explorer Case Study",
          title: "Hamlin Park shows why the forecast pages matter before the hotspot list peaks.",
          subtitle:
            "This is a historical backtest example from the app that shows how the forecast pages can surface a tract before it becomes the top current hotspot.",
        }),
        row(
          { name: "case-main", width: fill, height: grow(1), gap: 34, align: "start" },
          [
            column(
              { name: "case-left", width: fixed(540), height: fill, gap: 16 },
              [
                text("What changed", {
                  width: wrap(520),
                  height: hug,
                  style: { fontSize: 26, bold: true, color: colors.ink },
                }),
                bulletList([
                  "On 2025-05-01, Hamlin Park tract 36029005202 was still Emerging Risk, but the 6m forecast probability was already 0.349 and the tract sat in the 89th risk percentile.",
                  "The main forecast drivers were combined trajectory score, neighbor_avg_rolling_3m, and cases_last_6m_per_1000_housing_units, which points users toward both internal trajectory and spillover context.",
                  "By 2026-05-01, the same tract had become the highest-scoring current hotspot in the city at 98.3 and was classified as Rapid Deterioration.",
                ], 540, 20),
                text("Use it", {
                  width: wrap(560),
                  height: hug,
                  style: { fontSize: 20, bold: true, color: colors.teal },
                }),
                bulletList([
                  "Use a live forecast page for current triage, then keep a historical backtest example like this in the deck to explain why the workflow matters.",
                  "Use Hotspot Analysis later to confirm whether the tract has fully transitioned into a current-priority condition.",
                ], 540, 17),
              ]
            ),
            image({
              name: "hamlin-case-image",
              dataUrl: assetPayloads.hamlinCase.dataUrl,
              contentType: assetPayloads.hamlinCase.contentType,
              width: fixed(1110),
              height: fixed(620),
              fit: "contain",
              alt: "Hamlin Park case study chart",
            }),
          ]
        ),
        footer(
          "Case study tract: Hamlin Park 36029005202. Forecast snapshot date: 2025-05-01. Current-condition snapshot date: 2026-05-01."
        ),
      ]
    )
  )
);

addSlide(
  slideShell(
    column(
      {
        name: "transitions-root",
        width: fill,
        height: fill,
        padding: { x: 84, y: 70 },
        gap: 28,
      },
      [
        titleBlock({
          kicker: "Neighborhood State Transitions",
          title: "Use the transition view to calibrate how sticky or reversible each state tends to be.",
          subtitle:
            "This page turns the neighborhood-state model into a decision aid: when a tract is flagged elsewhere, transition behavior helps you decide how aggressively to respond.",
        }),
        row(
          { name: "transitions-main", width: fill, height: grow(1), gap: 36, align: "start" },
          [
            image({
              name: "transition-chart",
              dataUrl: assetPayloads.transitions.dataUrl,
              contentType: assetPayloads.transitions.contentType,
              width: fixed(980),
              height: fixed(600),
              fit: "contain",
              alt: "Transition probabilities chart",
            }),
            column(
              { name: "transitions-right", width: grow(1), height: fill, gap: 18 },
              [
                text("What the transition matrix is telling us", {
                  width: wrap(520),
                  height: hug,
                  style: { fontSize: 30, bold: true, color: colors.ink },
                }),
                bulletList([
                  "Stable is very sticky: 90.0% of Stable tract-months stay Stable in the next step.",
                  "Rapid Deterioration is also sticky at 59.8%, and another 28.9% of those cases move into Chronic Distress rather than resolving quickly.",
                  "Emerging Risk is mixed: 54.2% stay Emerging Risk, 26.3% move back to Stable, but 10.5% escalate to Rapid Deterioration.",
                ], 520, 22),
                text("How to use it", {
                  width: wrap(520),
                  height: hug,
                  style: { fontSize: 23, bold: true, color: colors.teal },
                }),
                bulletList([
                  "Elevate action when a tract is forecast-high and the relevant transition path is historically sticky.",
                  "Treat improving signals more cautiously when the broader state system still shows high persistence in distress states.",
                ], 520, 19),
              ]
            ),
          ]
        ),
        footer(
          "Selected transition probabilities from analytics.neighborhood_transition_matrix: Stable→Stable 0.900, Rapid Deterioration→Rapid Deterioration 0.598, Rapid Deterioration→Chronic Distress 0.289, Emerging Risk→Rapid Deterioration 0.105."
        ),
      ]
    )
  )
);

addSlide(
  slideShell(
    column(
      {
        name: "playbook-root",
        width: fill,
        height: fill,
        padding: { x: 84, y: 74 },
        gap: 34,
      },
      [
        titleBlock({
          kicker: "Recommended Operating Playbook",
          title: "The practical takeaway: use the dashboard as a layered triage workflow.",
          subtitle:
            "No single page is the answer by itself. The tool gets stronger when you move from visible distress, to future risk, to tract-level explanation, and then back to intervention decisions.",
        }),
        row(
          { name: "playbook-steps", width: fill, height: hug, gap: 28, align: "start" },
          [
            stepColumn(1, "Hotspot Analysis", "Find what is already concentrated and hard to ignore."),
            stepColumn(2, "Forecast Risk", "Identify which tracts are most likely to tip next."),
            stepColumn(3, "Early Intervention Candidates", "Narrow to non-severe tracts where action can still be earlier than crisis response."),
            stepColumn(4, "Forecast Risk Map", "See whether the risk is isolated or part of a spatial pattern."),
            stepColumn(5, "Tract Explorer + State Transitions", "Validate local history and judge persistence before escalating resources."),
          ]
        ),
        panel(
          {
            name: "closing-panel",
            width: fill,
            height: hug,
            padding: { x: 28, y: 24 },
            fill: colors.tealSoft,
          },
          column(
            { width: fill, height: hug, gap: 12 },
            [
              text("What this tool is best at", {
                width: fill,
                height: hug,
                style: { fontSize: 26, bold: true, color: colors.ink },
              }),
              text(
                "It helps an operator move from “where is the problem now?” to “where is it forming next?” to “is this tract drifting, persisting, or tipping?” The Hamlin Park example is the clearest proof that the forecast views are not just parallel visuals. They can surface actionable risk before the current hotspot list fully catches up.",
                {
                  width: wrap(1560),
                  height: hug,
                  style: { fontSize: 22, color: colors.slate },
                }
              ),
            ]
          )
        ),
        footer(
          "Walk-through built from live app outputs and analytics tables in the Buffalo Housing Instability Intelligence Platform."
        ),
      ]
    )
  )
);

await PresentationFile.exportPptx(presentation).then((blob) => blob.save("output/output.pptx"));

for (let index = 0; index < presentation.slides.items.length; index += 1) {
  const slide = presentation.slides.items[index];
  const canvas = new Canvas(WIDTH, HEIGHT);
  const ctx = canvas.getContext("2d");
  await drawSlideToCtx(slide, presentation, ctx);
  await canvas.toFile(`${PREVIEW_DIR}/slide-${String(index + 1).padStart(2, "0")}.png`);
}

console.log(`Exported deck to output/output.pptx`);
console.log(`Rendered previews to ${PREVIEW_DIR}`);
