export type EngineQuery = {
  sessionID: string;
  rgsUrl: string;
  lang: string;
  device: string;
  replay: boolean;
  game: string;
  version: string;
  mode: string;
  event: string;
  social: boolean;
  currency: string;
  amount: string;
};

export function readEngineQuery(search = window.location.search): EngineQuery {
  const params = new URLSearchParams(search);
  return {
    sessionID: params.get("sessionID") || "",
    rgsUrl: (params.get("rgs_url") || "").replace(/\/$/, ""),
    lang: params.get("lang") || "en",
    device: params.get("device") || "desktop",
    replay: params.get("replay") === "true",
    game: params.get("game") || "",
    version: params.get("version") || "",
    mode: params.get("mode") || "base",
    event: params.get("event") || "",
    social: params.get("social") === "true",
    currency: params.get("currency") || "USD",
    amount: params.get("amount") || "",
  };
}

export function isLiveSession(query: EngineQuery) {
  return Boolean(query.sessionID && query.rgsUrl && !query.replay);
}

export function rgsOrigin(rgsUrl: string) {
  const trimmed = rgsUrl.replace(/\/$/, "");
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}
