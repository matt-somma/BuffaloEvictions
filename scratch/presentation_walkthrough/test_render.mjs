const artifactTool = await import(
  "file:///C:/Users/Matt/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs"
);
const skiaCanvas = await import(
  "file:///C:/Users/Matt/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/node_modules/skia-canvas/lib/index.mjs"
);

const { Presentation, text, column, fill, hug, PresentationFile, drawSlideToCtx } =
  artifactTool;
const { Canvas } = skiaCanvas;

const presentation = Presentation.create({
  slideSize: { width: 1280, height: 720 },
});

const slide = presentation.slides.add();
slide.compose(
  column(
    { name: "root", width: fill, height: fill, padding: 48, gap: 16 },
    [
      text("Test Render", {
        name: "title",
        width: fill,
        height: hug,
        style: { fontSize: 40, bold: true, color: "#111111" },
      }),
      text("If this works, we can preview slides before export.", {
        name: "subtitle",
        width: fill,
        height: hug,
        style: { fontSize: 24, color: "#444444" },
      }),
    ]
  ),
  {
    frame: { left: 0, top: 0, width: 1280, height: 720 },
    baseUnit: 8,
  }
);

const canvas = new Canvas(1280, 720);
const ctx = canvas.getContext("2d");
await drawSlideToCtx(slide, presentation, ctx);
await canvas.saveAs("scratch/presentation_walkthrough/test_render.png");

const pptxBlob = await PresentationFile.exportPptx(presentation);
await pptxBlob.save("scratch/presentation_walkthrough/test_render.pptx");
