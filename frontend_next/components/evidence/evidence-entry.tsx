"use client";
import dynamic from "next/dynamic";
// Other routes own their client boundaries; this contract is only for Scenario Lab.
export const ScenarioLabEntry = dynamic(() => import("../workspace/scenarios/scenario-lab").then(module => module.ScenarioLab));
