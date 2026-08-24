"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { ScreenKicker } from "@/components/ui/Mark";
import { useIntelligence } from "@/lib/session";

export function AssessmentRun() {
  const { assessment, submitAnswers, updatingModel, error } = useIntelligence();
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<number[]>([]);

  if (!assessment) return <LoadingState label="Loading assessment…" />;
  if (updatingModel) {
    return (
      <div className="mx-auto max-w-lg py-24">
        <ScreenKicker verb="ADAPT">Recompute</ScreenKicker>
        <h1 className="mt-4 font-display text-4xl text-paper">Updating your competency model…</h1>
        <p className="mt-4 text-sm leading-relaxed text-mist">
          Scoring, fusion, and adaptation are running on the backend. This screen does not fake progress.
        </p>
      </div>
    );
  }

  const question = assessment.questions[index];
  const selected = answers[index];
  const last = index === assessment.questions.length - 1;
  const progress = (index / assessment.question_count) * 100;

  function choose(choice: number) {
    setAnswers((current) => {
      const next = [...current];
      next[index] = choice;
      return next;
    });
  }

  function go(nextIndex: number) {
    setIndex(nextIndex);
  }

  function next() {
    if (last) {
      void submitAnswers(assessment!.questions.map((_, i) => answers[i]));
      return;
    }
    go(index + 1);
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <ScreenKicker verb="PROVE">{assessment.title}</ScreenKicker>
          <h1 className="mt-2 font-display text-3xl text-paper">
            Question {index + 1} of {assessment.question_count}
          </h1>
        </div>
        <p className="font-mono text-xs tabular-nums text-mist">{Math.round(progress)}%</p>
      </div>
      <div className="progress-bar h-px overflow-hidden bg-white/10">
        <span style={{ width: `${progress}%` }} />
      </div>
      {error ? <ErrorState message={error} /> : null}
      <div key={index} className="q-slide">
        <p className="text-lg leading-relaxed text-paper">{question.prompt}</p>
        <div className="mt-6 space-y-2" role="radiogroup" aria-label="Answers">
          {question.choices.map((choice, choiceIndex) => (
            <button
              key={choice}
              type="button"
              role="radio"
              aria-checked={selected === choiceIndex}
              onClick={() => choose(choiceIndex)}
              className={`path-row block w-full border px-4 py-3 text-left text-sm ${
                selected === choiceIndex
                  ? "border-accent/70 text-paper"
                  : "border-line text-mist hover:text-paper"
              }`}
            >
              {choice}
            </button>
          ))}
        </div>
        <div className="mt-6 flex justify-between">
          <Button variant="ghost" disabled={index === 0} onClick={() => go(index - 1)}>
            Back
          </Button>
          <Button disabled={selected === undefined} onClick={next}>
            {last ? "Submit" : "Next"}
          </Button>
        </div>
      </div>
    </div>
  );
}
