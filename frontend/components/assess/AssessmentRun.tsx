"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { ScreenKicker } from "@/components/ui/Mark";
import { useIntelligence } from "@/lib/session";
import { prettySkill } from "@/lib/status";

export function AssessmentRun() {
  const { assessment, submitAnswers, updatingModel, error } = useIntelligence();
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<number[]>([]);
  const [dir, setDir] = useState<"fwd" | "back">("fwd");

  if (!assessment) {
    return <LoadingState label="Loading assessment" detail="Fetching questions from the live assessment API." />;
  }
  if (updatingModel) {
    return (
      <div className="mx-auto max-w-lg py-16">
        <LoadingState
          label="Updating your profile…"
          detail="Scoring, fusion, and adaptation are running on the backend. This screen does not fake progress."
        />
      </div>
    );
  }

  const question = assessment.questions[index];
  const selected = answers[index];
  const last = index === assessment.questions.length - 1;
  const skill = question.skill || assessment.primary_skill;

  function choose(choice: number) {
    setAnswers((current) => {
      const next = [...current];
      next[index] = choice;
      return next;
    });
  }

  function go(nextIndex: number) {
    setDir(nextIndex < index ? "back" : "fwd");
    setIndex(nextIndex);
  }

  function next() {
    if (last) {
      const payload = assessment!.questions.map((_, i) => answers[i]);
      if (payload.some((choice) => choice == null)) {
        return;
      }
      void submitAnswers(payload);
      return;
    }
    go(index + 1);
  }

  return (
    <div className="assess-instrument">
      <header className="assess-instrument-head">
        <ScreenKicker verb="PROVE">{assessment.title}</ScreenKicker>
        <p className="assess-skill">{prettySkill(skill)}</p>
        <p className="assess-qnum type-data">
          Question {index + 1} of {assessment.question_count}
        </p>
      </header>

      {error ? <ErrorState message={error} /> : null}

      <div key={index} className={`q-slide is-${dir}`}>
        <h1 className="assess-prompt">{question.prompt}</h1>
        <div className="assess-choices mt-8 space-y-1" role="radiogroup" aria-label="Answers">
          {question.choices.map((choice, choiceIndex) => (
            <button
              key={choice}
              type="button"
              role="radio"
              aria-checked={selected === choiceIndex}
              onClick={() => choose(choiceIndex)}
              className={`assess-answer ${selected === choiceIndex ? "is-selected" : ""}`}
            >
              <span className="assess-answer-mark" aria-hidden />
              {choice}
            </button>
          ))}
        </div>
        <div className="mt-8 flex justify-between">
          <Button variant="ghost" disabled={index === 0} onClick={() => go(index - 1)}>
            Back
          </Button>
          <Button disabled={selected === undefined} onClick={next} data-testid="assessment-submit">
            {last ? "Submit" : "Next"}
          </Button>
        </div>
      </div>

      <ol className="assess-index assess-route" aria-label="Question progress">
        {assessment.questions.map((_, i) => (
          <li key={i}>
            <span className={i < index ? "is-done" : i === index ? "is-current" : ""} />
          </li>
        ))}
      </ol>
    </div>
  );
}
