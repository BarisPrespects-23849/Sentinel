// Single source of truth for alarm-state colors, shared by the map (RGB
// arrays for deck.gl) and the DOM (CSS classes). ISA-101 philosophy: LOW
// is deliberately colorless steel -- color appears only when risk rises.

// MEDIUM matches --color-warn in index.css: #facc15, chosen over #eab308
// for deuteranopia separation from HIGH's orange (validated deltaE 20.5).
export const RISK_RGB = {
  LOW: [107, 118, 134],
  MEDIUM: [250, 204, 21],
  HIGH: [249, 115, 22],
  CRITICAL: [239, 68, 68],
  UNKNOWN: [92, 101, 117],
};

export const RISK_TEXT_CLASS = {
  LOW: "text-normal",
  MEDIUM: "text-warn",
  HIGH: "text-high",
  CRITICAL: "text-critical",
  UNKNOWN: "text-faint",
};

export const RISK_BAR_CLASS = {
  LOW: "bg-normal/40",
  MEDIUM: "bg-warn",
  HIGH: "bg-high",
  CRITICAL: "bg-critical alarm-pulse",
  UNKNOWN: "bg-faint/40",
};

// Plain operator language for each state -- copy is design material.
export const RISK_LABEL = {
  LOW: "normal",
  MEDIUM: "elevated",
  HIGH: "high risk",
  CRITICAL: "critical",
  UNKNOWN: "no data",
};
