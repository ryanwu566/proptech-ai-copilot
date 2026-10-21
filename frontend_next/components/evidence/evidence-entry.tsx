"use client";
import dynamic from "next/dynamic";
// Other routes import their own client views directly; download this editor only on entry.
export const ScenarioLabEntry = dynamic(() => import("../workspace/scenarios/scenario-lab").then(module => module.ScenarioLab));
