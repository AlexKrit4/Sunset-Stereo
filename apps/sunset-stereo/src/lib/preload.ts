import { assetUrl, preloadAudio } from "./audioBank";
import { loadSymbolArt, symbolPreloadUrls } from "../pixi/symbols";

function decodeImage(url: string) {
  return new Promise<void>((resolve) => {
    const image = new Image();
    image.onload = () => resolve();
    image.onerror = () => resolve();
    image.src = url;
  });
}

export async function preloadGame(onProgress: (ratio: number) => void) {
  let audioRatio = 0;
  let extrasRatio = 0;
  const report = () => onProgress(Math.min(1, audioRatio * 0.88 + extrasRatio * 0.12));

  const audio = preloadAudio((ratio) => {
    audioRatio = ratio;
    report();
  });

  const extras = (async () => {
    const urls = [assetUrl("sunset-scene.jpg"), ...symbolPreloadUrls()];
    let done = 0;
    await Promise.all(
      urls.map(async (url) => {
        await decodeImage(url);
        done += 1;
        extrasRatio = (done / urls.length) * 0.45;
        report();
      }),
    );
    await loadSymbolArt();
    extrasRatio = 1;
    report();
  })();

  await Promise.all([audio, extras]);
  onProgress(1);
}
