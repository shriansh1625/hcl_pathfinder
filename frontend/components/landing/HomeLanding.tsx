"use client";

import { useRef } from "react";
import { Button } from "@/components/ui/Button";
import { Mark } from "@/components/ui/Mark";
import { HeroHeadline } from "@/components/landing/HeroHeadline";
import { HeroJourneyVisual } from "@/components/landing/HeroJourneyVisual";
import { HeroRouteGeometry } from "@/components/landing/HeroRouteGeometry";
import { HomeAmbience } from "@/components/landing/HomeAmbience";
import { HomeNav } from "@/components/landing/HomeNav";
import { ScrollReveal } from "@/components/landing/ScrollReveal";
import { ValueIcon } from "@/components/landing/ValueIcon";
import { Onboarding } from "@/components/onboarding/Onboarding";

const HOW_STEPS = [
  { title: "Goal", line: "Tell us what career you are working toward — in your own words." },
  { title: "Evidence", line: "Share skills, projects, and assessments so we know what is proven." },
  { title: "Diagnosis", line: "See honest gaps and blockers — not vague percentages." },
  { title: "Path", line: "Get a sequenced learning route with clear next steps." },
  { title: "Adapt", line: "When you prove a skill, your path updates — completed work stays." },
] as const;

const CAREERS = [
  "AI / ML Engineer",
  "Cybersecurity Analyst",
  "Data Engineer",
  "Backend Engineer",
  "Cloud Architect",
  "Product Manager",
  "DevOps Engineer",
  "Full Stack Developer",
] as const;

const VALUES = [
  { icon: "evidence" as const, title: "Evidence-first", line: "Every recommendation is backed by what you have actually shown." },
  { icon: "everyone" as const, title: "Built for everyone", line: "Students, professionals, and career changers." },
  { icon: "private" as const, title: "Private by design", line: "Your learning data stays under your control." },
  { icon: "outcome" as const, title: "Outcome focused", line: "Skills, confidence, and a career destination — not course counts." },
] as const;

const DIFFERENTIATORS = [
  { title: "Missing proof ≠ failure", line: "No evidence yet does not mean zero percent ready." },
  { title: "Dependency-aware", line: "Understand why something is blocked before you can start it." },
  { title: "Adaptive paths", line: "Path V1 becomes V2 when your diagnosis changes — with a clear audit trail." },
] as const;

export function HomeLanding() {
  const startRef = useRef<HTMLDivElement>(null);

  function scrollToStart() {
    startRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="home-landing">
      <HomeAmbience />
      <HomeNav onBuildPath={scrollToStart} />

      <section className="home-hero">
        <HeroRouteGeometry />
        <div className="home-hero-grid">
          <div className="home-hero-copy">
            <p className="home-kicker hero-fade-in">Career learning, made clear</p>
            <HeroHeadline />
            <p className="home-lead hero-fade-in">
              Tell PathFinder where you want to go. We will understand where you are, find what you are missing,
              and build a learning path that adapts as you grow.
            </p>
            <div className="home-hero-actions hero-fade-in">
              <Button className="home-cta-primary home-cta-hero" showMark onClick={scrollToStart}>
                Build My Path
              </Button>
              <Button
                variant="secondary"
                className="home-cta-secondary"
                onClick={() => document.getElementById("careers")?.scrollIntoView({ behavior: "smooth" })}
              >
                Explore Careers
              </Button>
            </div>
          </div>
          <HeroJourneyVisual />
        </div>

        <div className="home-value-bar">
          <div className="home-value-grid">
            {VALUES.map((item) => (
              <div key={item.title} className="home-value-item">
                <span className="home-value-icon-wrap" aria-hidden>
                  <ValueIcon name={item.icon} />
                </span>
                <p className="home-value-title">{item.title}</p>
                <p className="home-value-line">{item.line}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <ScrollReveal>
        <section id="how-it-works" className="home-section">
          <div className="mx-auto max-w-6xl px-6 py-16 lg:py-20">
            <p className="home-section-kicker">How PathFinder works</p>
            <h2 className="home-section-title">From goal to growing career — in five clear steps</h2>
            <ol className="home-steps-grid">
              {HOW_STEPS.map((step, i) => (
                <li key={step.title} className="home-step-card" style={{ ["--step-i" as string]: i }}>
                  <span className="home-step-num">{String(i + 1).padStart(2, "0")}</span>
                  <h3>{step.title}</h3>
                  <p>{step.line}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>
      </ScrollReveal>

      <ScrollReveal delay={60}>
        <section className="home-section home-section-alt">
          <div className="mx-auto max-w-6xl px-6 py-16 lg:py-20">
            <p className="home-section-kicker">Personalization</p>
            <h2 className="home-section-title">Your career — not a generic course list</h2>
            <p className="home-section-lead max-w-2xl">
              PathFinder sequences learning around your destination role, your current skills, and what still needs proof.
              Two learners targeting the same role can receive different paths when their evidence differs.
            </p>
          </div>
        </section>
      </ScrollReveal>

      <ScrollReveal delay={60}>
        <section className="home-section">
          <div className="mx-auto max-w-6xl px-6 py-16 lg:py-20">
            <p className="home-section-kicker">Adaptation</p>
            <h2 className="home-section-title">See what changes when you grow</h2>
            <div className="home-adapt-grid">
              <div className="home-adapt-card">
                <p className="home-adapt-label">Before</p>
                <p className="home-adapt-body">Your path reflects what we knew at the start.</p>
              </div>
              <div className="home-adapt-arrow" aria-hidden>
                →
              </div>
              <div className="home-adapt-card is-highlight">
                <p className="home-adapt-label">New evidence</p>
                <p className="home-adapt-body">You complete an assessment or report real progress.</p>
              </div>
              <div className="home-adapt-arrow" aria-hidden>
                →
              </div>
              <div className="home-adapt-card">
                <p className="home-adapt-label">Updated path</p>
                <p className="home-adapt-body">What is ahead reshapes. Completed work stays preserved.</p>
              </div>
            </div>
          </div>
        </section>
      </ScrollReveal>

      <ScrollReveal delay={60}>
        <section id="careers" className="home-section home-section-alt">
          <div className="mx-auto max-w-6xl px-6 py-16 lg:py-20">
            <p className="home-section-kicker">Careers</p>
            <h2 className="home-section-title">Built for different destinations</h2>
            <p className="home-section-lead max-w-2xl">
              Eight careers from our live role catalog — each with skills, prerequisites, and assessments.
            </p>
            <ul className="home-career-chips">
              {CAREERS.map((name) => (
                <li key={name}>
                  <button type="button" className="home-career-chip" onClick={scrollToStart}>
                    {name}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </ScrollReveal>

      <ScrollReveal delay={60}>
        <section className="home-section">
          <div className="mx-auto max-w-6xl px-6 py-16 lg:py-20">
            <p className="home-section-kicker">Why PathFinder</p>
            <h2 className="home-section-title">Honest, dependency-aware, adaptive</h2>
            <ul className="home-diff-grid">
              {DIFFERENTIATORS.map((item) => (
                <li key={item.title} className="home-diff-card">
                  <h3>{item.title}</h3>
                  <p>{item.line}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </ScrollReveal>

      <ScrollReveal delay={60}>
        <section id="resources" className="home-section home-section-alt">
          <div className="mx-auto max-w-6xl px-6 py-16 lg:py-20">
            <p className="home-section-kicker">Under the hood</p>
            <h2 className="home-section-title">Intelligent — with clear boundaries</h2>
            <p className="home-section-lead max-w-3xl">
              PathFinder uses deterministic engines for diagnosis, sequencing, and adaptation. Optional semantic retrieval
              and grounded explanations help you understand recommendations — they never override your scores or reorder
              your path without evidence.
            </p>
            <ul className="mt-8 grid gap-3 text-sm text-mist sm:grid-cols-2">
              <li>Evidence fusion from self-report, assessments, and progress</li>
              <li>Role-relative gap engine with prerequisite blockers</li>
              <li>Path versioning with frozen completed work</li>
              <li>Grounded learning guide over verified facts only</li>
            </ul>
          </div>
        </section>
      </ScrollReveal>

      <section className="home-final-cta">
        <div className="mx-auto max-w-6xl px-6 py-16 text-center">
          <h2 className="home-section-title">Start building your path</h2>
          <p className="home-section-lead mx-auto mt-3 max-w-lg">
            What are you trying to become? PathFinder will meet you there.
          </p>
          <Button className="home-cta-primary home-cta-hero mt-8" showMark onClick={scrollToStart}>
            Build My Path
          </Button>
        </div>
      </section>

      <section id="get-started" ref={startRef} className="home-onboard-section">
        <div className="mx-auto max-w-6xl px-6 py-16 lg:py-20">
          <div className="home-onboard-intro">
            <Mark className="home-logo-mark mx-auto h-3.5 w-5 text-accent" title="PathFinder" />
            <h2 className="home-section-title mt-4 text-center">What are you trying to become?</h2>
            <p className="home-section-lead mx-auto mt-2 max-w-xl text-center">
              Describe your goal below. We will help you pick a career, understand your starting point, and build your path.
            </p>
          </div>
          <Onboarding />
        </div>
      </section>

      <footer className="home-footer border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-4 px-6 py-8 sm:flex-row sm:items-center">
          <p className="text-sm text-mist">PathFinder · HCLTech AMPlified Round 2</p>
          <a
            href="https://github.com/shriansh1625/hcl_pathfinder"
            className="text-sm text-accent hover:underline"
            target="_blank"
            rel="noreferrer"
          >
            View source on GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}
