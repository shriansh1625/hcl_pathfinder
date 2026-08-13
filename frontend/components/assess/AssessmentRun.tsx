"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { useIntelligence } from "@/lib/session";

export function AssessmentRun() {
  const { assessment, submitAnswers, updatingModel, error } = useIntelligence();
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<number[]>([]);

  if (!assessment) return <LoadingState label="Loading assessment…" />;
  if (updatingModel) {
    return (
      <div className="mx-auto max-w-lg py-24 text-center">
        <p className="text-[11px] uppercase tracking-[0.2em] text-accent">Evidence loop</p>
        <h1 className="mt-4 text-3xl text-paper">Updating your competency model…</h1>
        <p className="mt-3 text-sm text-mist">
          Scoring, fusion, and adaptation are running on the backend. This screen does not fake progress.
        </p>
      </div>
    );
  }

  const question = assessment.questions[index];
  const selected = answers[index];
  const last = index === assessment.questions.length - 1;

  function choose(choice: number) {
    setAnswers((current) => {
      const next = [...current];
      next[index] = choice;
      return next;
    });
  }

  function next() {
    if (last) {
      void submitAnswers(assessment!.questions.map((_, i) => answers[i]));
      return;
    }
    setIndex((value) => value + 1);
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-[0.2em] text-accent">{assessment.title}</p>
          <h1 className="mt-2 text-2xl text-paper">
            Question {index + 1} of {assessment.question_count}
          </h1>
        </div>
        <p className="font-mono text-xs text-mist">{Math.round(((index + (selected !== undefined ? 1 : 0)) / assessment.question_count) * 100)}%</p>
      </div>
      <div className="h-1 overflow-hidden rounded bg-ink-700">
        <div
          className="h-full bg-accent"
          style={{ width: `${((index) / assessment.question_count) * 100}%` }}
        />
      </div>
      {error ? <ErrorState message={error} /> : null}
      <Panel className="p-6">
        <p className="text-lg leading-relaxed text-paper">{question.prompt}</p>
        <div className="mt-6 space-y-2" role="radiogroup" aria-label="Answers">
          {question.choices.map((choice, choiceIndex) => (
            <button
              key={choice}
              type="button"
              role="radio"
              aria-checked={selected === choiceIndex}
              onClick={() => choose(choiceIndex)}
              className={`block w-full rounded-lg border px-4 py-3 text-left text-sm ${
                selected === choiceIndex
                  ? "border-accent bg-accent/10 text-paper"
                  : "border-line bg-ink-900 text-mist hover:text-paper"
              }`}
            >
              {choice}
            </button>
          ))}
        </div>
        <div className="mt-6 flex justify-between">
          <Button variant="ghost" disabled={index === 0} onClick={() => setIndex((value) => value - 1)}>
            Back
          </Button>
          <Button disabled={selected === undefined} onClick={next}>
            {last ? "Submit" : "Next"}
          </Button>
        </div>
      </Panel>
    </div>
  );
}
