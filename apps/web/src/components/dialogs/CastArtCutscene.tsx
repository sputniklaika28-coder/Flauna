import { useEffect } from "react";
import { useUIStore } from "../../stores";

const CUTSCENE_DURATION_MS = 1800;

export default function CastArtCutscene() {
  const cutscene = useUIStore((s) => s.castArtCutscene);
  const clear = useUIStore((s) => s.clearCastArtCutscene);

  useEffect(() => {
    if (!cutscene) return;
    const id = setTimeout(clear, CUTSCENE_DURATION_MS);
    return () => clearTimeout(id);
  }, [cutscene, clear]);

  if (!cutscene) return null;

  return (
    <div
      key={cutscene.id}
      className="fixed inset-0 z-40 flex items-center justify-center pointer-events-none cast-art-cutscene"
      data-testid="cast-art-cutscene"
    >
      <div className="absolute inset-0 bg-purple-900/30 animate-pulse" />
      <div className="relative">
        <div className="absolute inset-0 -inset-x-32 bg-purple-500/20 blur-3xl rounded-full" />
        <div className="relative px-12 py-6 bg-gradient-to-r from-purple-900/90 via-fuchsia-900/90 to-purple-900/90 border-2 border-purple-300 rounded-lg shadow-[0_0_60px_rgba(168,85,247,0.6)]">
          <div className="text-xs text-purple-200 tracking-[0.3em] uppercase text-center">
            {cutscene.casterName}
          </div>
          <div
            className="text-4xl font-bold text-white text-center mt-1 tracking-widest"
            style={{ textShadow: "0 0 24px rgba(216, 180, 254, 0.9)" }}
          >
            {cutscene.artName}
          </div>
        </div>
      </div>
    </div>
  );
}
