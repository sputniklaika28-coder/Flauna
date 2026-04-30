import { describe, it, expect, beforeAll, beforeEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import React from "react";
import i18n from "../../src/i18n/index";
import ja from "../../src/i18n/ja";
import en from "../../src/i18n/en";
import AssessmentScreen from "../../src/components/dialogs/AssessmentScreen";
import { useGameStore } from "../../src/stores/gameStore";
import type { GameState, Grade, SessionScore } from "../../src/types";

beforeAll(async () => {
  await i18n.changeLanguage("ja");
});

function makeState(score: SessionScore | null): GameState {
  return {
    room_id: "r",
    version: 1,
    seed: 1,
    phase: score ? "assessment" : "combat",
    machine_state: "IDLE",
    turn_order: [],
    current_turn_index: 0,
    round_number: score?.rounds_taken ?? 1,
    characters: [],
    map_size: [10, 10],
    obstacles: [],
    assessment_result: score,
    current_turn_summary: null,
    pending_actions: [],
  };
}

describe("Phase 7 web: i18n keys", () => {
  const required = [
    "room.assessment.title",
    "room.assessment.outcomeVictory",
    "room.assessment.outcomeDefeat",
    "room.assessment.grade",
    "room.assessment.rounds",
    "room.assessment.pcsAlive",
    "room.assessment.enemiesDefeated",
    "room.assessment.backToLobby",
    "room.assessment.gradeLabel.S",
    "room.assessment.gradeLabel.A",
    "room.assessment.gradeLabel.B",
    "room.assessment.gradeLabel.C",
    "room.assessment.gradeLabel.D",
  ] as const;

  it("ja and en define every Phase 7 assessment key", () => {
    for (const key of required) {
      expect(ja).toHaveProperty(key);
      expect(en).toHaveProperty(key);
    }
  });
});

describe("Phase 7 web: SessionScore / GrowthProposal types", () => {
  it("Grade covers S/A/B/C/D", () => {
    const grades: Grade[] = ["S", "A", "B", "C", "D"];
    expect(grades).toHaveLength(5);
  });

  it("GameState compiles with assessment_result", () => {
    const score: SessionScore = {
      outcome: "victory",
      rounds_taken: 3,
      pcs_alive: 2,
      pcs_total: 2,
      enemies_defeated: 4,
      enemies_total: 4,
      grade: "S",
    };
    const state = makeState(score);
    expect(state.assessment_result?.grade).toBe("S");
    expect(state.phase).toBe("assessment");
  });
});

describe("Phase 7 web: AssessmentScreen rendering", () => {
  beforeEach(() => {
    cleanup();
    useGameStore.setState({ gameState: null });
  });

  it("renders nothing when phase is not assessment", () => {
    useGameStore.setState({ gameState: makeState(null) });
    const { container } = render(
      React.createElement(AssessmentScreen, { onBackToLobby: () => {} }),
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when assessment_result is missing", () => {
    const s = makeState(null);
    s.phase = "assessment";
    s.assessment_result = null;
    useGameStore.setState({ gameState: s });
    const { container } = render(
      React.createElement(AssessmentScreen, { onBackToLobby: () => {} }),
    );
    expect(container.firstChild).toBeNull();
  });

  it("shows grade letter, outcome, and stats on victory", () => {
    const score: SessionScore = {
      outcome: "victory",
      rounds_taken: 4,
      pcs_alive: 2,
      pcs_total: 2,
      enemies_defeated: 3,
      enemies_total: 3,
      grade: "A",
    };
    useGameStore.setState({ gameState: makeState(score) });
    render(React.createElement(AssessmentScreen, { onBackToLobby: () => {} }));

    expect(screen.getByTestId("assessment-screen")).toBeTruthy();
    expect(screen.getByTestId("assessment-grade").textContent).toBe("A");
    expect(screen.getByText(/任務達成/)).toBeTruthy();
    expect(screen.getByText("2 / 2")).toBeTruthy();
    expect(screen.getByText("3 / 3")).toBeTruthy();
    expect(screen.getByText("4")).toBeTruthy();
  });

  it("shows defeat label when outcome is defeat", () => {
    const score: SessionScore = {
      outcome: "defeat",
      rounds_taken: 7,
      pcs_alive: 0,
      pcs_total: 2,
      enemies_defeated: 1,
      enemies_total: 3,
      grade: "D",
    };
    useGameStore.setState({ gameState: makeState(score) });
    render(React.createElement(AssessmentScreen, { onBackToLobby: () => {} }));
    expect(screen.getByText(/任務失敗/)).toBeTruthy();
    expect(screen.getByTestId("assessment-grade").textContent).toBe("D");
  });

  it("triggers onBackToLobby when the button is clicked", () => {
    const score: SessionScore = {
      outcome: "victory",
      rounds_taken: 2,
      pcs_alive: 1,
      pcs_total: 1,
      enemies_defeated: 1,
      enemies_total: 1,
      grade: "S",
    };
    useGameStore.setState({ gameState: makeState(score) });
    let called = 0;
    render(
      React.createElement(AssessmentScreen, {
        onBackToLobby: () => {
          called += 1;
        },
      }),
    );
    fireEvent.click(screen.getByTestId("assessment-back"));
    expect(called).toBe(1);
  });
});
